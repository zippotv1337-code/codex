from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "healthcheck.py"


def _run(database: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--db", str(database)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_healthcheck_reads_one_valid_database(tmp_path: Path) -> None:
    database = tmp_path / "review_dashboard.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")
    result = _run(database)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Integrity: ok" in result.stdout
    assert "Foreign-key errors: 0" in result.stdout


def test_healthcheck_fails_when_database_is_missing(tmp_path: Path) -> None:
    result = _run(tmp_path / "missing.db")
    assert result.returncode == 1
    assert "operational database missing" in result.stdout


def test_healthcheck_fails_on_invalid_database(tmp_path: Path) -> None:
    database = tmp_path / "invalid.db"
    database.write_bytes(b"not a SQLite database")
    result = _run(database)
    assert result.returncode == 1
    assert "Database: ERROR" in result.stdout
