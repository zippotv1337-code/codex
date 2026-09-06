from __future__ import annotations

import hashlib
import re
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs" / "FIVERR_GIG_DRAFT.md"
CATALOG = ROOT / "docs" / "FIVERR_GIG1_PACKAGE_CATALOG.md"
COVER = ROOT / "docs" / "assets" / "fiverr-gig-cover-ai-workflow-automation-v1.png"


class FiverrGig1PackageTests(unittest.TestCase):
    def test_copy_and_package_limits_are_publish_ready(self) -> None:
        draft = DRAFT.read_text(encoding="utf-8")
        catalog = CATALOG.read_text(encoding="utf-8")

        title = "I will build AI workflow automation for your business"
        self.assertIn(title, draft)
        self.assertLessEqual(len(title), 80)

        description_block = draft.split("## Description", 1)[1].split("## FAQ", 1)[0]
        description = "\n".join(
            re.sub(r"^> ?", "", line)
            for line in description_block.splitlines()
            if line.startswith(">")
        )
        self.assertLessEqual(len(description), 1_200)

        for price in ("149 USD", "349 USD", "699 USD"):
            self.assertIn(price, catalog)
        for scope in (
            "Up to three workflows",
            "Up to three integrations",
            "One dashboard",
            "seven calendar days of post-delivery support",
            "Revisions: **3**",
        ):
            self.assertIn(scope, catalog)

    def test_primary_gallery_cover_is_valid_and_stable(self) -> None:
        payload = COVER.read_bytes()
        self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", payload[16:24])
        self.assertGreaterEqual(width, 712)
        self.assertGreaterEqual(height, 430)
        self.assertLessEqual(width, 4_000)
        self.assertLessEqual(height, 2_416)
        self.assertEqual((width, height), (1_619, 971))
        self.assertEqual(
            hashlib.sha256(payload).hexdigest().upper(),
            "3DB079745D6763248A360FFB093E7A5C7964DC0CA936A0F111AFB2700CE3EF9F",
        )


if __name__ == "__main__":
    unittest.main()
