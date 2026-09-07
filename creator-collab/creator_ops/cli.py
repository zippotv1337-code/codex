from __future__ import annotations

import argparse
import json
import os
import tomllib
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from .database import CreatorDatabase
from .asset_import import LocalAssetImportService
from .current_state import CurrentStateService
from .evening import EveningRunCoordinator
from .exporting import ExportBackupService
from .external_readiness import ExternalReadinessService
from .pipeline import VerticalPipeline
from .reconcile import ManualInstagramService
from .recovery import RecoveryBackupService
from .checkpoint import AutopilotCheckpointService
from .adworks import AdWorksService
from .publishing import (
    MetaInstagramPublishingAdapter,
    PublishQueueService,
    UnconfiguredInstagramAdapter,
)
from .morning import MorningContentFactory
from .offline import OfflineSnapshotService
from .operations_audit import OperationsAuditService
from .review import ReviewDashboardService
from .style_reference import StyleReferenceService


ROOT = Path(__file__).resolve().parents[1]


def build_pipeline(database_path: Path) -> VerticalPipeline:
    return VerticalPipeline(
        CreatorDatabase(database_path),
        ROOT / "config" / "personas.json",
        ROOT / "config" / "prime_time.json",
    )


def live_publishing_requested(config_path: Path) -> bool:
    settings = tomllib.loads(config_path.read_text(encoding="utf-8"))
    publishing = settings.get("publishing", {})
    scheduler = settings.get("scheduler", {})
    capabilities = settings.get("capabilities", {})
    return bool(publishing.get("live_enabled", False)) and bool(
        scheduler.get("dispatch_live", False)
    ) and bool(capabilities.get("official_instagram_publish", False)) and bool(
        capabilities.get("live_external_actions", False)
    )


def build_publish_queue(
    pipeline: VerticalPipeline, config_path: Path
) -> PublishQueueService:
    settings = tomllib.loads(config_path.read_text(encoding="utf-8"))
    publishing = settings.get("publishing", {})
    enabled = live_publishing_requested(config_path)
    password_ready = len(os.environ.get("CREATOR_OPS_PASSWORD", "")) >= 12
    if enabled and password_ready and publishing.get("adapter") == "meta-graph":
        adapter = MetaInstagramPublishingAdapter.from_environment(pipeline.db, ROOT)
    else:
        adapter = UnconfiguredInstagramAdapter()
    return PublishQueueService(pipeline.db, adapter)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Creator Ops local MVP")
    result.add_argument("--db", type=Path, default=ROOT / "data" / "creator_ops.db")
    result.add_argument("--config", type=Path, default=ROOT / "config.toml")
    subcommands = result.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init", help="Initialize schema and persona seeds")
    demo = subcommands.add_parser("demo", help="Run both vertical mock pipelines")
    demo.add_argument("--date", default=date.today().isoformat())
    evening = subcommands.add_parser("evening-run", help="Run both creators inside 19:00-22:00 Berlin time")
    evening.add_argument("--at", default=datetime.now().astimezone().isoformat())
    engagement = subcommands.add_parser("engagement", help="List engagement suggestions")
    engagement.add_argument("--status", default="PROPOSED")
    approve = subcommands.add_parser("engagement-approve", help="Mark one suggestion for manual action")
    approve.add_argument("item_id", type=int)
    export = subcommands.add_parser("export", help="Create a secret-free JSON export")
    export.add_argument("--out", type=Path, default=ROOT / "backups")
    export.add_argument("--label")
    backup = subcommands.add_parser("backup", help="Create and integrity-check a SQLite backup")
    backup.add_argument("--out", type=Path, default=ROOT / "backups")
    backup.add_argument("--label")
    restore = subcommands.add_parser("restore", help="Restore a verified backup into a fresh database")
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--out", type=Path, required=True)
    asset_import = subcommands.add_parser(
        "import-assets", help="Copy local SFW images into tomorrow's review package"
    )
    asset_import.add_argument("--creator", required=True, choices=("leona-voss", "mara-field"))
    asset_import.add_argument("--date", required=True)
    asset_import.add_argument(
        "--rights-status", default="AI_GENERATED", choices=("AI_GENERATED", "OWNED", "LICENSED")
    )
    asset_import.add_argument("files", nargs="+")
    status = subcommands.add_parser("status", help="Print a dynamic, secret-free project snapshot")
    status.add_argument("--out", type=Path)
    status.add_argument("--include-remote-url", action="store_true")
    status.add_argument("--tests-passed", type=int)
    status.add_argument("--tests-failed", type=int)
    recovery = subcommands.add_parser("recovery-backup", help="Create a validated secret-free recovery ZIP")
    recovery.add_argument("--kind", required=True, choices=("weekly", "monthly", "milestone"))
    recovery.add_argument("--out", type=Path, default=ROOT / "backups")
    patch_backup = subcommands.add_parser(
        "patch-backup", help="Create a manifest-backed patch linked to a base backup"
    )
    patch_backup.add_argument("--base", type=Path, required=True)
    patch_backup.add_argument("--reason", required=True)
    patch_backup.add_argument("--label", required=True)
    patch_backup.add_argument("--file", action="append", required=True)
    patch_backup.add_argument("--out", type=Path, default=ROOT / "backups")
    reconcile = subcommands.add_parser("reconcile-instagram", help="Record an owner-confirmed native post")
    reconcile.add_argument("--creator", required=True, choices=("leona-voss", "mara-field"))
    reconcile.add_argument("--content-id", required=True, type=int)
    reconcile.add_argument("--url", required=True)
    reconcile.add_argument("--published-at", required=True)
    reconcile.add_argument(
        "--asset-id",
        type=int,
        action="append",
        help="Published asset id; repeat for every image in a confirmed carousel",
    )
    reconcile.add_argument("--no-ai-disclosure", action="store_true")
    analytics = subcommands.add_parser("manual-analytics", help="Append an owner-reported analytics snapshot")
    analytics.add_argument("--publication-id", required=True, type=int)
    analytics.add_argument("--window", required=True, type=int, choices=(24, 72, 168))
    for metric in ("reach", "views", "likes", "comments", "shares", "saves", "profile-visits", "follows", "link-clicks"):
        analytics.add_argument(f"--{metric}", type=int)
    analytics.add_argument("--revenue", type=float)
    analytics.add_argument("--note", default="")
    checkpoint = subcommands.add_parser("checkpoint", help="Write an atomic autopilot savegame")
    checkpoint.add_argument("--out", type=Path, default=ROOT / "AUTOPILOT_CHECKPOINT.md")
    checkpoint.add_argument("--last-completed", required=True)
    checkpoint.add_argument("--current-task", required=True)
    checkpoint.add_argument("--continuation", required=True)
    checkpoint.add_argument("--changed-file", action="append", default=[])
    checkpoint.add_argument("--tests-passed", type=int, required=True)
    checkpoint.add_argument("--tests-failed", type=int, default=0)
    checkpoint.add_argument("--backup-status", required=True)
    checkpoint.add_argument("--blocker", action="append", default=[])
    checkpoint.add_argument("--owner-gate", action="append", default=[])
    checkpoint.add_argument("--parked", action="append", default=[])
    checkpoint.add_argument("--next-task", action="append", required=True)
    subcommands.add_parser("adworks-status", help="Show real and dry-run revenue lanes separately")
    adworks = subcommands.add_parser("adworks-dry-run", help="Run the local Pack-to-Revenue acceptance path")
    adworks.add_argument("--pack", default="creator-sfw-basic")
    subcommands.add_parser("publish-queue", help="List the durable local publishing queue")
    meta_preflight = subcommands.add_parser(
        "meta-preflight",
        help="Run secret-free read-only checks for one exact Instagram package",
    )
    meta_preflight.add_argument("--publication-id", required=True, type=int)
    meta_preflight.add_argument("--content-id", required=True, type=int)
    subcommands.add_parser("publish-reconcile", help="Reconcile approved posts into the local queue")
    dispatch = subcommands.add_parser(
        "publish-dispatch-due", help="Dispatch due jobs through the configured fail-closed adapter"
    )
    dispatch.add_argument("--at", default=datetime.now().astimezone().isoformat())
    morning = subcommands.add_parser("morning-run", help="Prepare the idempotent 05:30 review batch")
    morning.add_argument("--at", default=datetime.now().astimezone().isoformat())
    morning.add_argument("--waiting-for-capacity", action="store_true")
    style = subcommands.add_parser(
        "style-reference-set", help="Mark an internal mz.poke-inspired experiment"
    )
    style.add_argument("--content-id", required=True, type=int)
    style.add_argument("--strength", required=True, choices=("light", "medium"))
    style.add_argument(
        "--format",
        required=True,
        choices=("fashion", "teaser", "humor_reel", "personality"),
    )
    offline = subcommands.add_parser(
        "offline-snapshot", help="Write a static read-only operating snapshot"
    )
    offline.add_argument("--out", type=Path, default=ROOT / "output" / "offline")
    subcommands.add_parser(
        "operations-audit",
        help="Print the read-only daily operating priorities from current state",
    )
    subcommands.add_parser(
        "external-readiness",
        help="Print secret-free readiness for Meta, Fiverr, and handoff mirror lanes",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    pipeline = build_pipeline(args.db)
    pipeline.initialize()
    if args.command == "init":
        print(f"Initialized {args.db}")
    elif args.command == "demo":
        results = pipeline.run_both(date.fromisoformat(args.date))
        print(pipeline.serialize_results(results))
    elif args.command == "evening-run":
        result = EveningRunCoordinator(pipeline).run(datetime.fromisoformat(args.at))
        print(EveningRunCoordinator.serialize(result))
    elif args.command == "engagement":
        with pipeline.db.transaction() as connection:
            items = pipeline.engagement.list(connection, args.status)
        print(json.dumps(items, ensure_ascii=False, indent=2))
    elif args.command == "engagement-approve":
        with pipeline.db.transaction() as connection:
            pipeline.engagement.approve_for_manual_action(connection, args.item_id)
        print(json.dumps({"item_id": args.item_id, "status": "APPROVED_MANUAL"}, indent=2))
    elif args.command == "export":
        path = ExportBackupService(pipeline.db).export_json(args.out, args.label)
        print(json.dumps({"export": str(path)}, ensure_ascii=False, indent=2))
    elif args.command == "backup":
        path = ExportBackupService(pipeline.db).backup_sqlite(args.out, args.label)
        print(json.dumps({"backup": str(path)}, ensure_ascii=False, indent=2))
    elif args.command == "restore":
        path = ExportBackupService.restore_sqlite(args.backup, args.out)
        print(json.dumps({"restored": str(path)}, ensure_ascii=False, indent=2))
    elif args.command == "import-assets":
        imported = LocalAssetImportService(pipeline, ROOT).import_files(
            args.creator,
            date.fromisoformat(args.date),
            [Path(value) for value in args.files],
            rights_status=args.rights_status,
        )
        print(json.dumps({"imported": imported}, ensure_ascii=False, indent=2))
    elif args.command == "status":
        service = CurrentStateService(pipeline.db, ROOT)
        snapshot = service.snapshot(
            include_remote_url=args.include_remote_url,
            tests_passed=args.tests_passed,
            tests_failed=args.tests_failed,
        )
        if args.out:
            service.write(args.out, snapshot)
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    elif args.command == "recovery-backup":
        path = RecoveryBackupService(pipeline.db, ROOT).build(args.out, kind=args.kind)
        print(json.dumps(RecoveryBackupService.validate(path), ensure_ascii=False, indent=2))
    elif args.command == "patch-backup":
        path = RecoveryBackupService(pipeline.db, ROOT).build_patch(
            args.out,
            changed_files=args.file,
            base_backup=args.base,
            reason=args.reason,
            label=args.label,
        )
        print(json.dumps(RecoveryBackupService.validate(path), ensure_ascii=False, indent=2))
    elif args.command == "reconcile-instagram":
        result = ManualInstagramService(pipeline.db).reconcile(
            creator_slug=args.creator,
            content_id=args.content_id,
            external_url=args.url,
            published_at=args.published_at,
            ai_disclosure=not args.no_ai_disclosure,
            asset_ids=args.asset_id,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "manual-analytics":
        metrics = {
            "reach": args.reach,
            "views": args.views,
            "likes": args.likes,
            "comments": args.comments,
            "shares": args.shares,
            "saves": args.saves,
            "profile_visits": args.profile_visits,
            "follows": args.follows,
            "link_clicks": args.link_clicks,
            "revenue": args.revenue,
        }
        event_id = ManualInstagramService(pipeline.db).append_analytics(
            args.publication_id,
            args.window,
            note=args.note,
            **metrics,
        )
        print(json.dumps({"analytics_event_id": event_id}, indent=2))
    elif args.command == "checkpoint":
        path = AutopilotCheckpointService(ROOT).write(
            args.out,
            last_completed_task=args.last_completed,
            current_task=args.current_task,
            continuation_point=args.continuation,
            changed_files=args.changed_file,
            tests_passed=args.tests_passed,
            tests_failed=args.tests_failed,
            backup_status=args.backup_status,
            blockers=args.blocker,
            owner_gates=args.owner_gate,
            parked_tasks=args.parked,
            next_tasks=args.next_task,
        )
        print(json.dumps({"checkpoint": str(path)}, ensure_ascii=False, indent=2))
    elif args.command == "adworks-status":
        print(json.dumps(AdWorksService(pipeline.db).dashboard(), ensure_ascii=False, indent=2))
    elif args.command == "adworks-dry-run":
        result = AdWorksService(pipeline.db).dry_run(args.pack)
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    elif args.command == "publish-queue":
        print(json.dumps(build_publish_queue(pipeline, args.config).list(), ensure_ascii=False, indent=2))
    elif args.command == "meta-preflight":
        adapter = MetaInstagramPublishingAdapter.from_environment(pipeline.db, ROOT)
        if isinstance(adapter, UnconfiguredInstagramAdapter):
            result = {
                "schema": "creator-ops-meta-live-preflight-v1",
                "status": "BLOCKED",
                "provider": adapter.provider,
                "publication_id": args.publication_id,
                "content_id": args.content_id,
                "checks": {"adapter": {"ok": False}},
                "errors": ["official_instagram_adapter_not_configured"],
            }
        else:
            result = adapter.preflight(args.publication_id, args.content_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "publish-reconcile":
        print(json.dumps(build_publish_queue(pipeline, args.config).reconcile(), ensure_ascii=False, indent=2))
    elif args.command == "publish-dispatch-due":
        print(
            json.dumps(
                build_publish_queue(pipeline, args.config).dispatch_due(
                    datetime.fromisoformat(args.at)
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "morning-run":
        service = MorningContentFactory(ReviewDashboardService(pipeline), ROOT)
        print(
            json.dumps(
                service.run(
                    datetime.fromisoformat(args.at),
                    capacity_available=not args.waiting_for_capacity,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "style-reference-set":
        print(
            json.dumps(
                StyleReferenceService(pipeline.db).mark(
                    args.content_id,
                    strength=args.strength,
                    reference_format=args.format,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "offline-snapshot":
        print(
            json.dumps(
                OfflineSnapshotService(pipeline.db, ROOT).build(args.out),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "operations-audit":
        reviews = ReviewDashboardService(pipeline)
        print(
            json.dumps(
                OperationsAuditService(
                    reviews,
                    build_publish_queue(pipeline, args.config),
                ).snapshot(),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "external-readiness":
        print(
            json.dumps(
                ExternalReadinessService(ROOT, args.config).snapshot(),
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
