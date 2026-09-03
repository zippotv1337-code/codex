from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from .database import CreatorDatabase
from .asset_import import LocalAssetImportService
from .evening import EveningRunCoordinator
from .exporting import ExportBackupService
from .pipeline import VerticalPipeline


ROOT = Path(__file__).resolve().parents[1]


def build_pipeline(database_path: Path) -> VerticalPipeline:
    return VerticalPipeline(
        CreatorDatabase(database_path),
        ROOT / "config" / "personas.json",
        ROOT / "config" / "prime_time.json",
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Creator Ops local MVP")
    result.add_argument("--db", type=Path, default=ROOT / "data" / "creator_ops.db")
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
    subcommands.add_parser("status", help="Print database table counts")
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
        print(json.dumps(pipeline.db.table_counts(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
