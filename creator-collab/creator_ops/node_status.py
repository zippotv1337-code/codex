from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AutonomyNodeStatus:
    """Read-only multi-node status projected into the existing control plane."""

    def __init__(self, runtime_root: Path) -> None:
        self.runtime_root = Path(runtime_root)

    @staticmethod
    def _json(path: Path) -> dict[str, Any] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def snapshot(self) -> dict[str, object]:
        run = self._json(self.runtime_root / "Tasks" / "RUN_STATE.json")
        local = {
            "node": "LOCAL_AI",
            "status": "WAITING_EXTERNAL_NODE",
            "run_state": None,
            "active": False,
        }
        if run is not None:
            local = {
                "node": "LOCAL_AI",
                "status": (
                    "READY" if run.get("state") == "IDLE_CLEAN"
                    else "BUSY" if run.get("active") is True
                    else "ATTENTION"
                ),
                "run_state": run.get("state"),
                "active": bool(run.get("active", False)),
                "machine_id": run.get("machine_id"),
                "updated_at": run.get("updated_at") or run.get("last_update"),
            }

        vps_candidates = (
            self.runtime_root / "Exchange" / "VPS_TO_CODEX" / "Current" / "NODE_STATUS.json",
            self.runtime_root / "Exchange" / "VPS_TO_LOCALAI" / "Current" / "NODE_STATUS.json",
        )
        vps_payload = next(
            (payload for path in vps_candidates if (payload := self._json(path)) is not None),
            None,
        )
        vps = {
            "node": "VPS",
            "status": "WAITING_EXTERNAL_NODE",
            "reason": "no_current_structured_node_status",
        }
        if vps_payload is not None:
            vps = {
                "node": "VPS",
                "status": str(vps_payload.get("status") or "UNKNOWN"),
                "updated_at": vps_payload.get("updated_at"),
                "machine_id": vps_payload.get("machine_id"),
            }
        return {
            "schema": "zippoworkz-autonomy-nodes-v1",
            "local_ai": local,
            "vps": vps,
            "global_blocked": False,
        }
