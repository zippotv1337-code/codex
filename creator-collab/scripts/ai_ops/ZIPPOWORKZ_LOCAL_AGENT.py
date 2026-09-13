"""Compatibility entry point: fixed safe worker, no open-ended file agent."""
import runpy
import sys
from pathlib import Path

project = Path(r"C:\Zippoworkz\Workspace\codex_ingest\creator-collab")
if not (project / "creator_ops" / "local_ai_runtime.py").is_file():
    raise SystemExit("WORKSPACE_MISSING")
sys.path.insert(0, str(project))
runpy.run_module("creator_ops.local_ai_runtime", run_name="__main__")
