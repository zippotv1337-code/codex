from __future__ import annotations

import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from .current_state import CurrentStateService
from .database import CreatorDatabase
from .publishing import PublishQueueService


SENSITIVE_ASSIGNMENT = re.compile(
    r"(?im)\b(password|passwort|token|secret|api[_-]?key|cookie)\b\s*[:=]\s*\S+"
)
EMAIL_ADDRESS = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")


class OfflineSnapshotService:
    """Write a static, read-only and secret-reduced operating snapshot."""

    DOCUMENTS = (
        "AUTOPILOT_CHECKPOINT.md",
        "docs/BACKUP_CHAIN.md",
        "docs/HUMAN_HANDOFF.md",
    )

    def __init__(self, database: CreatorDatabase, project_root: Path) -> None:
        self.database = database
        self.project_root = Path(project_root).resolve()

    @staticmethod
    def _sanitize(text: str) -> str:
        text = SENSITIVE_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
        return EMAIL_ADDRESS.sub("[EMAIL REDACTED]", text)

    @staticmethod
    def _atomic_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
        ) as handle:
            handle.write(text)
            temporary = Path(handle.name)
        temporary.replace(path)

    def build(self, destination: Path) -> dict[str, object]:
        destination = Path(destination)
        documents: dict[str, str] = {}
        for relative in self.DOCUMENTS:
            path = self.project_root / relative
            if path.is_file():
                documents[relative] = self._sanitize(
                    path.read_text(encoding="utf-8", errors="replace")[:20_000]
                )

        payload: dict[str, object] = {
            "schema": "creator-ops-offline-v1",
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "read_only": True,
            "current_state": CurrentStateService(
                self.database, self.project_root
            ).snapshot(),
            "publish_queue": PublishQueueService(self.database).list(),
            "documents": documents,
        }
        json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        self._atomic_text(destination / "snapshot.json", json_text)

        state = payload["current_state"]
        assert isinstance(state, dict)
        content = state.get("content", {})
        assets = state.get("assets", {})
        queue = payload["publish_queue"]
        assert isinstance(queue, list)
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(str(item.get('content_id', '—')))}</td>"
            f"<td>{html.escape(str(item.get('status', '—')))}</td>"
            f"<td>{html.escape(str(item.get('planned_at', '—')))}</td>"
            "</tr>"
            for item in queue
        ) or '<tr><td colspan="3">Keine Queuejobs vorhanden.</td></tr>'
        document_blocks = "".join(
            f"<details><summary>{html.escape(name)}</summary>"
            f"<pre>{html.escape(text)}</pre></details>"
            for name, text in documents.items()
        )
        page = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Creator Ops – Offline-Snapshot</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;margin:0;background:#111318;color:#f5f5f5}}
main{{max-width:1050px;margin:auto;padding:24px}}h1{{margin-bottom:4px}}
.muted{{color:#aeb4c0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:24px 0}}
.card,details{{background:#1d2129;border:1px solid #343a46;border-radius:14px;padding:16px}}
.value{{font-size:1.6rem;font-weight:700}}table{{width:100%;border-collapse:collapse;background:#1d2129}}
th,td{{padding:10px;border-bottom:1px solid #343a46;text-align:left}}pre{{white-space:pre-wrap;word-break:break-word}}
</style></head><body><main>
<h1>Creator Ops – Offline-Snapshot</h1>
<p class="muted">Nur Lesen · erstellt {html.escape(str(payload['generated_at']))}</p>
<section class="grid">
<div class="card"><div class="muted">Version</div><div class="value">{html.escape(str(state.get('app_version', '—')))}</div></div>
<div class="card"><div class="muted">Inhalte</div><div class="value">{html.escape(str(content.get('total', 0) if isinstance(content, dict) else 0))}</div></div>
<div class="card"><div class="muted">Owner-Review</div><div class="value">{html.escape(str(content.get('review_required', 0) if isinstance(content, dict) else 0))}</div></div>
<div class="card"><div class="muted">Reale Assets</div><div class="value">{html.escape(str(assets.get('real', 0) if isinstance(assets, dict) else 0))}</div></div>
</section>
<h2>Lokale Publish Queue</h2><table><thead><tr><th>Content</th><th>Status</th><th>Termin</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Letzte Übergaben</h2>{document_blocks or '<p class="muted">Keine Dokumente vorhanden.</p>'}
</main></body></html>"""
        self._atomic_text(destination / "index.html", page)
        return {
            "directory": str(destination.resolve()),
            "html": str((destination / "index.html").resolve()),
            "json": str((destination / "snapshot.json").resolve()),
            "queue_jobs": len(queue),
            "read_only": True,
        }
