from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from creator_ops.public_media import PublicMediaBundle, create_media_server


class FixtureDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            CREATE TABLE content_items (
                id INTEGER PRIMARY KEY, creator_id INTEGER, approved INTEGER,
                status TEXT, safety_class TEXT, visibility_scope TEXT, adult INTEGER);
            INSERT INTO content_items VALUES (1,1,1,'OWNER_APPROVED','SFW','PUBLIC_SFW',0);
            CREATE TABLE assets (
                id INTEGER PRIMARY KEY, asset_id TEXT, creator_id INTEGER,
                content_id INTEGER, asset_type TEXT, safety_class TEXT,
                visibility_scope TEXT, published_status TEXT, rights_status TEXT,
                platform_allowed TEXT, status TEXT, file_path TEXT, is_top_pick INTEGER);
            CREATE TABLE asset_usage_plan(asset_id INTEGER, content_id INTEGER, priority INTEGER);
        """)

    def one(self, sql, parameters=()):
        return self.connection.execute(sql, parameters).fetchone()

    def all(self, sql, parameters=()):
        return self.connection.execute(sql, parameters).fetchall()


class PublicMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        (self.root / "assets").mkdir(parents=True)
        self.db = FixtureDatabase()
        self.addCleanup(self.db.connection.close)
        for number in range(1, 4):
            path = self.root / "assets" / f"{number}.jpg"
            path.write_bytes(b"\xff\xd8\xff\xe0" + bytes([number]) * 16 + b"\xff\xd9")
            self.db.connection.execute(
                "INSERT INTO assets VALUES (?,?,1,1,'image','SFW','PUBLIC_SFW','UNPUBLISHED','AI_GENERATED','instagram,threads','GENERATED',?,1)",
                (number, f"asset-{number}", f"assets/{number}.jpg"),
            )
            self.db.connection.execute("INSERT INTO asset_usage_plan VALUES (?,1,?)", (number, 4-number))

    def bundle(self, **kwargs):
        return PublicMediaBundle.from_database(self.db, self.root, 1, **kwargs)

    def test_manifest_preserves_top_three_order_and_disclosure_is_opt_in(self):
        bundle = self.bundle()
        manifest = bundle.manifest("https://media.example.com")
        self.assertEqual(manifest["schema"], "creator-ops-meta-publish-v1")
        content = manifest["content"]["1"]
        self.assertEqual(list(content["asset_urls"]), ["asset-3", "asset-2", "asset-1"])
        self.assertIs(content["native_ai_disclosure_confirmed"], False)
        self.assertIs(bundle.manifest("https://media.example.com", native_ai_disclosure_confirmed=True)["content"]["1"]["native_ai_disclosure_confirmed"], True)
        with self.assertRaisesRegex(ValueError, "disclosure_boolean"):
            bundle.manifest("https://media.example.com", native_ai_disclosure_confirmed="false")
        self.assertNotIn(str(self.root), json.dumps(manifest))

    def test_manifest_requires_public_https_origin(self):
        basic_auth_url = "https://" + "user" + ":" + "password" + "@example.com"
        for url in ("http://example.com", "https://localhost", "https://192.168.1.2", "https://127.0.0.1", "https://foo.local", basic_auth_url, "https://example.com/path", "https://example.com?token=x", "https://example.com:4180"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.bundle().manifest(url)

    def test_approval_safety_and_character_guards(self):
        for column, value in (("approved",0), ("status","PUBLISHED"), ("safety_class","ADULT"), ("visibility_scope","LOCAL_ONLY"), ("adult",1)):
            original = self.db.one(f"SELECT {column} FROM content_items")[0]
            self.db.connection.execute(f"UPDATE content_items SET {column}=?", (value,))
            with self.subTest(column=column), self.assertRaises(ValueError):
                self.bundle()
            self.db.connection.execute(f"UPDATE content_items SET {column}=?", (original,))
        self.db.connection.execute("UPDATE assets SET creator_id=2 WHERE id=1")
        with self.assertRaisesRegex(ValueError, "asset_not_eligible"):
            self.bundle()

    def test_published_restricted_unknown_rights_and_non_image_rejected(self):
        for column, value in (("published_status","PUBLISHED"), ("visibility_scope","LOCAL_ONLY"), ("rights_status","UNKNOWN"), ("platform_allowed","tiktok"), ("asset_type","video"), ("status","REJECTED")):
            original = self.db.one(f"SELECT {column} FROM assets WHERE id=1")[0]
            self.db.connection.execute(f"UPDATE assets SET {column}=? WHERE id=1", (value,))
            with self.subTest(column=column), self.assertRaisesRegex(ValueError, "asset_not_eligible"):
                self.bundle()
            self.db.connection.execute(f"UPDATE assets SET {column}=? WHERE id=1", (original,))

    def test_exactly_three_required(self):
        self.db.connection.execute("UPDATE assets SET is_top_pick=0 WHERE id=1")
        with self.assertRaisesRegex(ValueError, "three_unpublished"):
            self.bundle()

    def test_missing_and_outside_assets_rejected(self):
        for path in ("assets/missing.jpg", "../outside.jpg", str(self.root.parent / "outside.jpg"), "data/review_dashboard.db"):
            self.db.connection.execute("UPDATE assets SET file_path=? WHERE id=1", (path,))
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.bundle()

    def test_source_symlink_rejected(self):
        source = self.root / "assets" / "1.jpg"
        link = self.root / "assets" / "linked.jpg"
        try:
            link.symlink_to(source)
        except OSError:
            # Exercise the same guard even on Windows without symlink privilege.
            with patch.object(Path, "is_symlink", lambda p: p == source):
                with self.assertRaisesRegex(ValueError, "symlink_forbidden"):
                    self.bundle()
        else:
            self.db.connection.execute("UPDATE assets SET file_path='assets/linked.jpg' WHERE id=1")
            with self.assertRaisesRegex(ValueError, "symlink_forbidden"):
                self.bundle()

    def test_derivative_must_be_explicit_selected_and_inside_content_directory(self):
        source = self.root / "assets" / "1.png"
        source.write_bytes(b"png-original")
        self.db.connection.execute("UPDATE assets SET file_path='assets/1.png' WHERE id=1")
        with self.assertRaisesRegex(ValueError, "jpeg_derivative_required"):
            self.bundle()
        directory = self.root / "output" / "meta-public-media" / "1"
        directory.mkdir(parents=True)
        derivative = directory / "asset-1.jpg"
        derivative.write_bytes((self.root / "assets" / "1.jpg").read_bytes())
        self.assertEqual(len(self.bundle(jpeg_paths={"asset-1": derivative}).assets), 3)
        with self.assertRaisesRegex(ValueError, "outside_allowlist"):
            self.bundle(jpeg_paths={"asset-1": self.root / "assets" / "1.jpg"})
        with self.assertRaisesRegex(ValueError, "unselected_derivative"):
            self.bundle(jpeg_paths={"asset-99": derivative})

    def test_non_jpeg_and_duplicate_bytes_rejected(self):
        path = self.root / "assets" / "1.jpg"
        path.write_bytes(b"not a jpeg")
        with self.assertRaisesRegex(ValueError, "invalid_jpeg"):
            self.bundle()
        path.write_bytes((self.root / "assets" / "2.jpg").read_bytes())
        with self.assertRaisesRegex(ValueError, "duplicate_jpegs"):
            self.bundle()

    def test_loopback_server_exposes_only_exact_allowlist_and_frozen_bytes(self):
        bundle = self.bundle()
        server = create_media_server(bundle, port=0)
        self.assertEqual(server.server_address[0], "127.0.0.1")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            asset = bundle.assets[0]
            (self.root / "assets" / "3.jpg").write_bytes(b"changed after approval")
            with urllib.request.urlopen(base + asset.route, timeout=2) as response:
                self.assertEqual(response.headers["Content-Type"], "image/jpeg")
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(response.read(), asset.data)
            request = urllib.request.Request(base + asset.route, method="HEAD")
            with urllib.request.urlopen(request, timeout=2) as response:
                self.assertEqual(response.read(), b"")
            for route in ("/", "/api/health", "/data/review_dashboard.db", "/../assets/1.jpg", "/%2e%2e/assets/1.jpg", asset.route + "?x=1", "/media/1/", "/favicon.ico"):
                with self.subTest(route=route), self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(base + route, timeout=2)
                self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_no_dashboard_port_and_expiry(self):
        with self.assertRaises(ValueError):
            create_media_server(self.bundle(), port=4180)
        for lifetime in (0, 21601):
            with self.assertRaises(ValueError):
                create_media_server(self.bundle(), port=0, lifetime_seconds=lifetime)
        with patch("creator_ops.public_media.time.monotonic", return_value=0):
            server = create_media_server(self.bundle(), port=0, lifetime_seconds=1)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}" + self.bundle().assets[0].route, timeout=2)
            self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
