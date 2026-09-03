from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo

from .database import utc_now
from .models import EveningRunResult
from .pipeline import VerticalPipeline


class EveningRunCoordinator:
    def __init__(self, pipeline: VerticalPipeline):
        self.pipeline = pipeline
        self.timezone = ZoneInfo(pipeline.prime_time["timezone"])

    def run(self, requested_at: datetime) -> EveningRunResult:
        local = (
            requested_at.astimezone(self.timezone)
            if requested_at.tzinfo
            else requested_at.replace(tzinfo=self.timezone)
        )
        batch_key = f"{local.date().isoformat()}:evening"
        settings = self.pipeline.prime_time["evening_run"]
        if not self.pipeline.scheduler.in_evening_window(local):
            return EveningRunResult(
                batch_key=batch_key,
                status="SKIPPED_OUTSIDE_WINDOW",
                requested_at=local.isoformat(timespec="seconds"),
                results=(),
                reason=f"allowed window is {settings['start']}-{settings['end']} Europe/Berlin",
            )

        results = tuple(
            result
            for slug in ("leona-voss", "mara-field")
            if (result := self.pipeline.run_safe(slug, local.date())) is not None
        )
        status = "COMPLETE" if len(results) == 2 else "PARTIAL_READY"
        serialized = json.dumps(
            [
                {
                    **asdict(result),
                    "final_status": result.final_status.value,
                }
                for result in results
            ],
            ensure_ascii=False,
        )
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO evening_batches
                    (batch_key, run_date, requested_at, window_start, window_end,
                     status, results_json, reason, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(batch_key) DO UPDATE SET
                    requested_at=excluded.requested_at,
                    status=excluded.status,
                    results_json=excluded.results_json,
                    reason=excluded.reason,
                    completed_at=excluded.completed_at
                """,
                (
                    batch_key,
                    local.date().isoformat(),
                    local.isoformat(timespec="seconds"),
                    settings["start"],
                    settings["end"],
                    status,
                    serialized,
                    None if status == "COMPLETE" else "one or more creator runs are retryable",
                    utc_now(),
                ),
            )
        return EveningRunResult(
            batch_key=batch_key,
            status=status,
            requested_at=local.isoformat(timespec="seconds"),
            results=results,
            reason=None if status == "COMPLETE" else "one or more creator runs are retryable",
        )

    @staticmethod
    def serialize(result: EveningRunResult) -> str:
        return json.dumps(
            {
                **asdict(result),
                "results": [
                    {**asdict(item), "final_status": item.final_status.value}
                    for item in result.results
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
