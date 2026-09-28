from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType

WORKER = "creator-ops-meta"
DEFAULT_ROOT = Path(r"C:\Zippoworkz")


def _root() -> Path:
    configured = os.environ.get("ZIPPOWORKZ_ROOT", "").strip()
    return Path(configured) if configured else DEFAULT_ROOT


def _load_broker(root: Path | None = None) -> ModuleType | None:
    path = (root or _root()) / "_system" / "SECRET_BROKER.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("zippoworkz_secret_broker", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_secret(
    name: str,
    default: str = "",
    *,
    worker: str = WORKER,
    root: Path | None = None,
) -> str:
    """Resolve a secret without logging or persisting its plaintext value.

    Process environment remains a backwards-compatible override for tests and
    emergency sessions. Normal Zippoworkz runtime falls back to the node-local
    DPAPI Secret Broker under C:/Zippoworkz/_system/Secrets.
    """
    env_value = os.environ.get(name, "")
    if env_value and env_value.strip():
        return env_value.strip()

    try:
        broker = _load_broker(root)
        if broker is None:
            return default
        value = broker.get_for_broker(name, worker)
    except (KeyError, PermissionError, FileNotFoundError, RuntimeError, OSError):
        return default
    return str(value).strip() if value is not None else default


def secret_present(
    name: str,
    *,
    worker: str = WORKER,
    root: Path | None = None,
) -> bool:
    return bool(get_secret(name, worker=worker, root=root))


def set_secret(
    name: str,
    value: str,
    *,
    worker: str,
    root: Path | None = None,
    expires_at: str | None = None,
) -> None:
    """Persist a secret in the node-local DPAPI broker without returning it.

    This is intentionally stricter than ``get_secret``: writes never fall back
    to process environment variables or plaintext files. Callers receive only
    success/failure and must not log ``value``.
    """
    if not name.strip() or not value:
        raise ValueError("secret_name_and_value_required")
    broker = _load_broker(root)
    if broker is None or not hasattr(broker, "set_secret"):
        raise RuntimeError("node_secret_broker_unavailable")
    broker.set_secret(
        name,
        value,
        allowed_workers=[worker],
        expires_at=expires_at,
    )
