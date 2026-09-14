"""One-package, JPEG-only public media origin; never serves the dashboard.

This module does not start a tunnel, contact Meta, approve content or publish.
The caller must deliberately expose its loopback listener with a separate tunnel.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sqlite3
import stat
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlsplit

MANIFEST_SCHEMA = "creator-ops-meta-publish-v1"
MAX_JPEG_BYTES = 8 * 1024 * 1024


def _safe_file(workspace: Path, value: str | Path, roots: tuple[Path, ...]) -> Path:
    """Reject traversal, symlinks/junctions and hardlinks before reading bytes."""
    candidate = Path(value)
    if ".." in candidate.parts:
        raise ValueError("public_media_path_escape")
    candidate = candidate if candidate.is_absolute() else workspace / candidate
    if not any(candidate.is_relative_to(root) for root in roots):
        raise ValueError("public_media_path_outside_allowlist")
    for part in (candidate, *candidate.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("public_media_symlink_forbidden")
        if part == workspace:
            break
    try:
        resolved = candidate.resolve(strict=True)
        info = resolved.stat()
    except OSError:
        raise ValueError("public_media_asset_missing") from None
    if not any(resolved.is_relative_to(root.resolve()) for root in roots):
        raise ValueError("public_media_path_escape")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1:
        raise ValueError("public_media_regular_single_link_file_required")
    return resolved


def _https_base(value: str) -> str:
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https" or not host or parsed.username is not None
        or parsed.password is not None or parsed.query or parsed.fragment
        or parsed.path not in {"", "/"} or any(c.isspace() for c in value)
    ):
        raise ValueError("public_media_public_https_origin_required")
    try:
        public = ipaddress.ip_address(host).is_global
    except ValueError:
        public = "." in host and not host.lower().endswith((".local", ".localhost"))
    if not public or host.lower() == "localhost":
        raise ValueError("public_media_public_https_origin_required")
    try:
        if parsed.port not in {None, 443}:
            raise ValueError("public_media_https_port_required")
    except ValueError:
        raise ValueError("public_media_https_port_required") from None
    return f"https://{parsed.netloc}".rstrip("/")


@dataclass(frozen=True)
class PublicMediaAsset:
    asset_id: str
    route: str
    sha256: str
    data: bytes


class PublicMediaBundle:
    """Immutable allowlisted bytes for exactly three approved top-pick images."""

    def __init__(self, content_id: int, assets: tuple[PublicMediaAsset, ...]):
        if len(assets) != 3 or len({asset.route for asset in assets}) != 3:
            raise ValueError("three_unique_public_media_assets_required")
        self.content_id = content_id
        self.assets = assets
        self.routes = MappingProxyType({asset.route: asset for asset in assets})

    @classmethod
    def from_database(
        cls, database, workspace: Path, content_id: int, *,
        jpeg_paths: Mapping[str, str | Path] | None = None,
    ) -> PublicMediaBundle:
        workspace = workspace.resolve(strict=True)
        content = database.one(
            "SELECT * FROM content_items WHERE id=?", (content_id,)
        )
        if content is None:
            raise ValueError("public_media_content_not_found")
        if not content["approved"] or content["status"] not in {"OWNER_APPROVED", "SCHEDULED"}:
            raise ValueError("public_media_content_approval_required")
        if content["safety_class"] != "SFW" or content["visibility_scope"] != "PUBLIC_SFW" or content["adult"]:
            raise ValueError("public_media_content_not_public_sfw")
        rows = database.all(
            """SELECT a.* FROM assets a
               LEFT JOIN asset_usage_plan p ON p.asset_id=a.id AND p.content_id=a.content_id
               WHERE a.content_id=? AND a.is_top_pick=1
               ORDER BY COALESCE(p.priority,9999), a.id""", (content_id,),
        )
        if len(rows) != 3:
            raise ValueError("three_unpublished_public_top_picks_required")
        overrides = dict(jpeg_paths or {})
        if not set(overrides).issubset({str(row["asset_id"]) for row in rows}):
            raise ValueError("public_media_unselected_derivative_forbidden")
        original_roots = (
            workspace / "assets", workspace / "data" / "media" / "sfw",
            workspace / "data" / "imported-assets",
        )
        derivative_root = workspace / "output" / "meta-public-media" / str(content_id)
        selected: list[PublicMediaAsset] = []
        for row in rows:
            if (
                row["creator_id"] != content["creator_id"] or row["asset_type"] != "image"
                or row["safety_class"] != "SFW" or row["visibility_scope"] != "PUBLIC_SFW"
                or row["published_status"] != "UNPUBLISHED"
                or row["rights_status"] not in {"AI_GENERATED", "OWNED", "LICENSED"}
                or "instagram" not in str(row["platform_allowed"]).split(",")
                or row["status"] in {"BLOCKED", "REJECTED", "DELETED"}
            ):
                raise ValueError("public_media_asset_not_eligible")
            source = _safe_file(workspace, row["file_path"], original_roots)
            asset_id = str(row["asset_id"])
            served = _safe_file(workspace, overrides[asset_id], (derivative_root,)) if asset_id in overrides else source
            if served.suffix.lower() not in {".jpg", ".jpeg"}:
                raise ValueError("public_media_jpeg_derivative_required")
            if served.stat().st_size > MAX_JPEG_BYTES:
                raise ValueError("public_media_jpeg_too_large")
            data = served.read_bytes()
            if len(data) > MAX_JPEG_BYTES or not data.startswith(b"\xff\xd8\xff") or not data.endswith(b"\xff\xd9"):
                raise ValueError("public_media_invalid_jpeg")
            digest = hashlib.sha256(data).hexdigest()
            route = f"/media/{content_id}/{len(selected)+1}-{digest[:24]}.jpg"
            selected.append(PublicMediaAsset(asset_id, route, digest, data))
        if len({asset.sha256 for asset in selected}) != 3:
            raise ValueError("public_media_duplicate_jpegs")
        return cls(content_id, tuple(selected))

    def manifest(self, base_url: str, *, native_ai_disclosure_confirmed: bool = False) -> dict:
        base_url = _https_base(base_url)
        if type(native_ai_disclosure_confirmed) is not bool:
            raise ValueError("public_media_disclosure_boolean_required")
        return {
            "schema": MANIFEST_SCHEMA,
            "content": {
                str(self.content_id): {
                    "native_ai_disclosure_confirmed": native_ai_disclosure_confirmed,
                    "asset_urls": {asset.asset_id: base_url + asset.route for asset in self.assets},
                }
            },
        }


def create_media_server(bundle: PublicMediaBundle, *, port: int = 4181, lifetime_seconds: int = 3600) -> ThreadingHTTPServer:
    if not 0 <= port <= 65535 or port == 4180:
        raise ValueError("public_media_separate_valid_port_required")
    if not 1 <= lifetime_seconds <= 21600:
        raise ValueError("public_media_lifetime_1_to_21600_required")
    deadline = time.monotonic() + lifetime_seconds

    class Handler(BaseHTTPRequestHandler):
        server_version = "ZippoWorkz-Media"
        sys_version = ""

        def log_message(self, format, *args):
            pass  # No URLs, user agents, cookies or headers in logs.

        def _serve(self, head: bool = False):
            asset = bundle.routes.get(self.path) if time.monotonic() < deadline else None
            if asset is None:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(asset.data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head:
                self.wfile.write(asset.data)

        def do_GET(self):
            self._serve()

        def do_HEAD(self):
            self._serve(head=True)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


class _ReadonlyDatabase:
    def __init__(self, path: Path):
        path = path.resolve(strict=True)
        self.connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA query_only=ON")

    def one(self, sql, parameters=()):
        return self.connection.execute(sql, parameters).fetchone()

    def all(self, sql, parameters=()):
        return self.connection.execute(sql, parameters).fetchall()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-id", type=int, required=True)
    parser.add_argument("--port", type=int, default=4181)
    parser.add_argument("--lifetime-seconds", type=int, default=3600)
    parser.add_argument("--jpeg-map", type=Path, help="Local JSON mapping selected asset IDs to explicit derivatives")
    parser.add_argument("--base-url", help="Explicit public HTTPS origin; never guessed")
    parser.add_argument("--manifest-output", type=Path)
    parser.add_argument("--native-ai-disclosure-confirmed", action="store_true")
    parser.add_argument("--serve", action="store_true", help="Start only loopback media listener, no tunnel")
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[1]
    database = None
    try:
        database = _ReadonlyDatabase(workspace / "data" / "review_dashboard.db")
        mapping = json.loads(args.jpeg_map.read_text(encoding="utf-8")) if args.jpeg_map else None
        if mapping is not None and not isinstance(mapping, dict):
            raise ValueError("public_media_jpeg_map_invalid")
        bundle = PublicMediaBundle.from_database(database, workspace, args.content_id, jpeg_paths=mapping)
        if args.base_url:
            manifest = bundle.manifest(args.base_url, native_ai_disclosure_confirmed=args.native_ai_disclosure_confirmed)
            if args.manifest_output:
                target = args.manifest_output.absolute()
                allowed = workspace / "output" / "meta-public-media"
                if not target.is_relative_to(allowed) or ".." in target.parts:
                    raise ValueError("public_media_manifest_output_outside_scope")
                if target.is_symlink() or any(parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()) for parent in target.parents):
                    raise ValueError("public_media_symlink_forbidden")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            else:
                print(json.dumps(manifest, indent=2))
        elif args.manifest_output:
            raise ValueError("public_media_base_url_required")
        print(json.dumps({"status": "READY", "content_id": bundle.content_id, "asset_count": 3, "publishes": 0}), flush=True)
        if args.serve:
            server = create_media_server(bundle, port=args.port, lifetime_seconds=args.lifetime_seconds)
            timer = threading.Timer(args.lifetime_seconds, server.shutdown)
            timer.daemon = True
            timer.start()
            print(f"LOOPBACK_MEDIA_ORIGIN=http://127.0.0.1:{server.server_port}", flush=True)
            try:
                server.serve_forever(poll_interval=0.25)
            finally:
                timer.cancel()
                server.server_close()
        return 0
    except (OSError, ValueError, sqlite3.Error) as error:
        safe_error = str(error) if re.fullmatch(r"[a-z0-9_]+", str(error)) else "public_media_local_validation_failed"
        print(json.dumps({"status": "BLOCKED", "error": safe_error}))
        return 1
    finally:
        if database is not None:
            database.connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
