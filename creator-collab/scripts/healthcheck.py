import os
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

print("=== ZippoWorkz Local Healthcheck ===")
print("Python:", sys.version.split()[0])
print("Project:", ROOT)

# Virtual environment
venv_ok = sys.prefix != sys.base_prefix
print("VENV:", "OK" if venv_ok else "NOT ACTIVE")

# Disk space
drive = ROOT.drive + "\\"
total, used, free = shutil.disk_usage(drive)
print("Free disk:", round(free / (1024**3), 1), "GB")

# Find SQLite databases
db_files = list(ROOT.rglob("*.db")) + list(ROOT.rglob("*.sqlite")) + list(ROOT.rglob("*.sqlite3"))

if not db_files:
    print("Database: UNKNOWN / none found")
else:
    print("Databases found:", len(db_files))
    for db in db_files:
        try:
            with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
                result = conn.execute("PRAGMA integrity_check;").fetchone()[0]
            print(f"DB: {db.name} -> {result}")
        except Exception as exc:
            print(f"DB: {db.name} -> ERROR: {exc}")

print("=== Healthcheck complete ===")
