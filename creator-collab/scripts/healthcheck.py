"""Compact, persisted local healthcheck; uses the existing project runtime."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from creator_ops.local_ops import main
if __name__ == "__main__":
    raise SystemExit(main(["health", *sys.argv[1:]]))
