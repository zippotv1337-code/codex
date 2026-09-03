from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .database import CreatorDatabase
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
    elif args.command == "status":
        print(json.dumps(pipeline.db.table_counts(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

