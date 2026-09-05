from __future__ import annotations

import hashlib
import shutil
from datetime import date
from pathlib import Path

from .database import utc_now
from .pipeline import VerticalPipeline
from .review import ReviewDashboardService


ALLOWED_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class LocalAssetImportService:
    """Copy rights-cleared local images into managed storage and review slots."""

    def __init__(self, pipeline: VerticalPipeline, project_root: Path):
        self.pipeline = pipeline
        self.project_root = project_root.resolve()
        self.storage_root = (self.project_root / "data" / "media" / "sfw").resolve()
        self.legacy_storage_root = (
            self.project_root / "data" / "imported-assets"
        ).resolve()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def import_files(
        self,
        creator_slug: str,
        run_date: date,
        sources: list[Path],
        *,
        rights_status: str = "AI_GENERATED",
        safety_class: str = "SFW",
    ) -> list[dict]:
        if creator_slug not in self.pipeline.personas:
            raise ValueError(f"unknown_creator: {creator_slug}")
        if rights_status not in {"AI_GENERATED", "OWNED", "LICENSED"}:
            raise ValueError("rights_status must be AI_GENERATED, OWNED or LICENSED")
        if safety_class != "SFW":
            raise ValueError("dashboard_import_accepts_sfw_only")
        if not sources:
            raise ValueError("at_least_one_image_required")

        ReviewDashboardService(self.pipeline).ensure_date(run_date)
        target_dir = self.storage_root / creator_slug / run_date.isoformat()
        target_dir.mkdir(parents=True, exist_ok=True)
        imported: list[dict] = []

        with self.pipeline.db.transaction() as connection:
            content = connection.execute(
                """
                SELECT c.id, c.creator_id, c.series_id
                FROM content_items c
                JOIN creators cr ON cr.id = c.creator_id
                JOIN runs r ON r.id = c.run_id
                WHERE cr.slug = ? AND r.run_date = ? AND c.run_key LIKE 'review:%'
                """,
                (creator_slug, run_date.isoformat()),
            ).fetchone()
            if content is None:
                raise RuntimeError("review_package_not_found")

            slots = list(
                connection.execute(
                    """
                    SELECT id FROM assets
                    WHERE content_id = ? AND generator = 'mock-generator'
                    ORDER BY id LIMIT ?
                    """,
                    (content["id"], len(sources)),
                )
            )
            if len(slots) < len(sources):
                raise ValueError(f"only_{len(slots)}_mock_slots_available")

            for source_value, slot in zip(sources, slots, strict=True):
                source = source_value.expanduser().resolve()
                suffix = source.suffix.lower()
                if suffix not in ALLOWED_IMAGE_TYPES:
                    raise ValueError(f"unsupported_image_type: {source.name}")
                if not source.is_file():
                    raise FileNotFoundError(source)
                checksum = self._sha256(source)
                target = target_dir / f"{checksum[:20]}{suffix}"
                if not target.exists():
                    shutil.copy2(source, target)
                relative_path = target.relative_to(self.project_root).as_posix()
                connection.execute(
                    """
                    UPDATE assets
                    SET file_path = ?, safety_class = ?, rights_status = ?,
                        perceptual_hash = ?, generator = 'local-import',
                        status = 'GENERATED', created_at = ?
                    WHERE id = ?
                    """,
                    (relative_path, safety_class, rights_status, checksum[:16], utc_now(), slot["id"]),
                )
                imported.append(
                    {
                        "asset_id": int(slot["id"]),
                        "file_path": relative_path,
                        "sha256": checksum,
                    }
                )
        return imported

    def preview_path(self, asset_id: int) -> tuple[Path, str] | None:
        row = self.pipeline.db.one(
            "SELECT file_path, generator FROM assets WHERE id = ?", (asset_id,)
        )
        if row is None or row["generator"] != "local-import":
            return None
        candidate = (self.project_root / row["file_path"]).resolve()
        managed_roots = (self.storage_root, self.legacy_storage_root)
        if not any(root in candidate.parents for root in managed_roots) or not candidate.is_file():
            return None
        content_type = ALLOWED_IMAGE_TYPES.get(candidate.suffix.lower())
        return None if content_type is None else (candidate, content_type)
