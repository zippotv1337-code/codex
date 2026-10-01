"""Read-only health check for the one operational Creator Ops database."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "review_dashboard.db"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args(argv)
    database = args.db.resolve()

    print("=== ZippoWorkz Local Healthcheck ===")
    print("Python:", sys.version.split()[0])
    print("Project:", ROOT)
    print("VENV:", "OK" if sys.prefix != sys.base_prefix else "NOT ACTIVE")
    free = shutil.disk_usage(ROOT.anchor).free
    print("Free disk:", round(free / (1024**3), 1), "GB")

    if not database.is_file():
        print("Database: ERROR / operational database missing")
        return 1
    try:
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_key_errors = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    except sqlite3.Error as exc:
        print("Database: ERROR /", type(exc).__name__)
        return 1

    print("Database:", database)
    print("Integrity:", integrity)
    print("Foreign-key errors:", foreign_key_errors)
    if integrity != "ok" or foreign_key_errors:
        return 1
    print("=== Healthcheck complete ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
