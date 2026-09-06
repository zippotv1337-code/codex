from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from .review import ReviewDashboardService
from .background import BackgroundCoordinator, WAITING_FOR_CAPACITY
from .publishing import PublishQueueService
from .model_routing import ModelRoutingPolicy


CONTROL_PLANE_SCHEMA = 1


class ControlPlaneService:
    """Small, model-agnostic control surface for safe local autopilot work."""

    def __init__(
        self,
        review: ReviewDashboardService,
        state_path: Path,
        publishing: PublishQueueService | None = None,
    ) -> None:
        self.review = review
        self.state_path = state_path
        self.publishing = publishing
        self.background = BackgroundCoordinator(
            review.pipeline.db,
            state_path.parent.parent,
        )
        self._lock = threading.Lock()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def _default_state(self) -> dict[str, object]:
        return {
            "schema_version": CONTROL_PLANE_SCHEMA,
            "status": "IDLE",
            "last_command": None,
            "last_completed_task": None,
            "continuation_point": "Owner Review der vorhandenen Feedpakete",
            "checkpoint_at": None,
            "updated_at": self._now(),
            "run_count": 0,
            "active_run_key": None,
        }

    def _read_state(self) -> dict[str, object]:
        if not self.state_path.exists():
            return self._default_state()
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._default_state()
        if payload.get("schema_version") != CONTROL_PLANE_SCHEMA:
            return self._default_state()
        return {**self._default_state(), **payload}

    def _write_state(self, payload: dict[str, object]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", delete=False, dir=self.state_path.parent
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temporary = Path(handle.name)
        temporary.replace(self.state_path)

    @staticmethod
    def capabilities() -> list[dict[str, object]]:
        return [
            {
                "id": "review.read",
                "label": "Review-Queue lesen",
                "state": "AVAILABLE",
                "required": True,
            },
            {
                "id": "preview.large",
                "label": "Große lokale Vorschau",
                "state": "AVAILABLE",
                "required": False,
            },
            {
                "id": "checkpoint.atomic",
                "label": "Atomaren Speicherstand schreiben",
                "state": "AVAILABLE",
                "required": True,
            },
            {
                "id": "runtime.capacity_wait",
                "label": "Kapazitätsstopp mit fortsetzbarem Zustand",
                "state": "AVAILABLE",
                "required": True,
            },
            {
                "id": "publish.local_queue",
                "label": "Dauerhafte lokale Publish-Queue",
                "state": "AVAILABLE",
                "required": True,
            },
            {
                "id": "analytics.manual",
                "label": "Owner-Analytics auswerten",
                "state": "WAITING_FOR_INPUT",
                "required": False,
            },
            {
                "id": "generation.enhanced",
                "label": "Optionale stärkere Modellleistung",
                "state": "OPTIONAL_BONUS",
                "required": False,
            },
            {
                "id": "generation.astra",
                "label": "GPT-6 Astra HIGH (optional)",
                "state": "OPTIONAL_BONUS",
                "required": False,
            },
            {
                "id": "adworks.dry_run",
                "label": "Pack-zu-Revenue-Dry-Run",
                "state": "AVAILABLE",
                "required": False,
            },
            {
                "id": "adworks.real_events",
                "label": "Echte Funnel- und Umsatzdaten",
                "state": "WAITING_FOR_INPUT",
                "required": False,
            },
            {
                "id": "ads.paid",
                "label": "Bezahlte Kampagnen oder Budget",
                "state": "OWNER_GATE",
                "required": False,
            },
            {
                "id": "publish.external",
                "label": "Extern veröffentlichen",
                "state": "OWNER_GATE",
                "required": False,
            },
        ]

    def _work_queue(self) -> list[dict[str, object]]:
        queue = self.review.review_queue()
        items: list[dict[str, object]] = []
        for card in queue["cards"]:
            if card["status"] in {"READY_FOR_REVIEW", "PARTIAL_READY"}:
                items.append(
                    {
                        "kind": "OWNER_REVIEW",
                        "content_id": card["content_id"],
                        "persona": card["display_name"],
                        "series": card["series"],
                        "status": card["status"],
                        "external_action": False,
                    }
                )
        return items

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            state = self._read_state()
        work = self._work_queue()
        return {
            "contract": {
                "schema_version": CONTROL_PLANE_SCHEMA,
                "execution": "local-safe-only",
                "model_policy": "stable-current-model",
                "future_models": "optional-capability-bonus",
                "backward_compatible": True,
                "model_routing": ModelRoutingPolicy.load().describe(),
            },
            "state": state,
            "runtime": self.background.health(),
            "publish_queue": self.publishing.list() if self.publishing else [],
            "capabilities": self.capabilities(),
            "queue": work,
            "owner_gates": [
                "Live-Publishing",
                "Kommentare, Likes, Follows oder DMs",
                "Account- und Profiländerungen",
                "Kostenpflichtige Dienste",
            ],
        }

    def command(self, action: str) -> dict[str, object]:
        if action not in {"pause", "resume", "run-once", "checkpoint", "wait-for-capacity"}:
            raise ValueError("unsupported_control_plane_action")
        with self._lock:
            state = self._read_state()
            now = self._now()
            if action == "pause":
                state["status"] = "PAUSED"
                state["continuation_point"] = "Beim nächsten sicheren lokalen Task fortsetzen"
            elif action == "resume":
                state["status"] = "IDLE"
            elif action == "checkpoint":
                state["checkpoint_at"] = now
            elif action in {"run-once", "wait-for-capacity"}:
                if state["status"] == "PAUSED":
                    raise ValueError("autopilot_is_paused")
                work = self._work_queue()
                active_run_key = state.get("active_run_key")
                if state["status"] == WAITING_FOR_CAPACITY and active_run_key:
                    run_key = str(active_run_key)
                    run_number = int(state.get("run_count", 0))
                else:
                    run_number = int(state.get("run_count", 0)) + 1
                    run_key = f"control-plane:{run_number}"

                def local_task() -> dict[str, object]:
                    reconcile = self.publishing.reconcile() if self.publishing else {}
                    return {"review_items": len(work), "publish_reconcile": reconcile}

                result = self.background.run_once(
                    run_key,
                    "safe-local-queue-reconciliation",
                    local_task,
                    capacity_available=action != "wait-for-capacity",
                )
                state["status"] = result.status if result.status == WAITING_FOR_CAPACITY else "IDLE"
                state["run_count"] = run_number
                state["active_run_key"] = (
                    result.run_key if result.status == WAITING_FOR_CAPACITY else None
                )
                state["last_completed_task"] = (
                    "Review- und Publish-Queue sicher geprüft; Owner-Gates respektiert"
                    if result.status != WAITING_FOR_CAPACITY
                    else state.get("last_completed_task")
                )
                state["continuation_point"] = (
                    "Beim nächsten erlaubten Kapazitätsslot am gespeicherten Schritt fortsetzen"
                    if result.status == WAITING_FOR_CAPACITY
                    else (
                        f"{len(work)} Pakete warten auf Owner Review"
                        if work
                        else "Auf echte Analytics oder neue lokale Aufgaben warten"
                    )
                )
                state["checkpoint_at"] = now
            state["last_command"] = action
            state["updated_at"] = now
            self._write_state(state)
        return self.snapshot()
