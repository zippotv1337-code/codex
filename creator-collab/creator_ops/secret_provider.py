from __future__ import annotations

import ctypes
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping, Protocol


SECRET_ALIAS_RE = re.compile(r"^secret://[a-z0-9][a-z0-9._/-]*$")

DEFAULT_ALIAS_ENV: dict[str, str] = {
    "secret://meta/access_token": "META_ACCESS_TOKEN",
    "secret://meta/leona-voss/ig-user-id": "META_IG_USER_ID_LEONA_VOSS",
    "secret://meta/leona-voss/access-token": "META_ACCESS_TOKEN_LEONA_VOSS",
    "secret://meta/mara-field/ig-user-id": "META_IG_USER_ID_MARA_FIELD",
    "secret://meta/mara-field/access-token": "META_ACCESS_TOKEN_MARA_FIELD",
    "secret://tiktok/client_key": "TIKTOK_CLIENT_KEY",
    "secret://tiktok/client_secret": "TIKTOK_CLIENT_SECRET",
    "secret://tiktok/client-key": "TIKTOK_CLIENT_KEY",
    "secret://tiktok/client-secret": "TIKTOK_CLIENT_SECRET",
    "secret://tiktok/milo-der-zug/access-token": "TIKTOK_MILO_ACCESS_TOKEN",
    "secret://tiktok/milo-der-zug/open-id": "TIKTOK_MILO_OPEN_ID",
    "secret://runway/api-key": "RUNWAY_API_KEY",
    "secret://stability/api-key": "STABILITY_API_KEY",
    "secret://github/token": "GITHUB_TOKEN",
}


def validate_alias(alias: str) -> str:
    normalized = str(alias).strip().lower()
    if not SECRET_ALIAS_RE.fullmatch(normalized):
        raise ValueError("invalid_secret_alias")
    return normalized


@dataclass(frozen=True, repr=False)
class SecretValue:
    """A value that cannot be exposed accidentally through repr/str/JSON."""

    alias: str
    _value: str

    def __post_init__(self) -> None:
        validate_alias(self.alias)
        if not self._value:
            raise ValueError("empty_secret_value")

    def reveal(self) -> str:
        """Reveal only at the final adapter boundary; never log the result."""
        return self._value

    def __repr__(self) -> str:
        return f"SecretValue(alias={self.alias!r}, value=<redacted>)"

    def __str__(self) -> str:
        return "<redacted>"


class SecretProvider(Protocol):
    provider_id: str

    @property
    def ready(self) -> bool: ...

    def get(self, alias: str) -> SecretValue | None: ...

    def has(self, alias: str) -> bool: ...


class NullSecretProvider:
    provider_id = "none"
    ready = False

    def get(self, alias: str) -> None:
        validate_alias(alias)
        return None

    def has(self, alias: str) -> bool:
        validate_alias(alias)
        return False


class EnvironmentSecretProvider:
    """Explicit, temporary runtime fallback; never enumerates the environment."""

    provider_id = "runtime-environment"

    def __init__(
        self,
        environ: Mapping[str, str] | None = None,
        alias_map: Mapping[str, str] | None = None,
    ) -> None:
        self._environ = environ if environ is not None else os.environ
        self._alias_map = {
            validate_alias(alias): env_name
            for alias, env_name in (alias_map or DEFAULT_ALIAS_ENV).items()
        }

    @property
    def ready(self) -> bool:
        return any(bool(self._environ.get(name)) for name in self._alias_map.values())

    def get(self, alias: str) -> SecretValue | None:
        normalized = validate_alias(alias)
        env_name = self._alias_map.get(normalized)
        value = self._environ.get(env_name, "") if env_name else ""
        return SecretValue(normalized, value) if value else None

    def has(self, alias: str) -> bool:
        normalized = validate_alias(alias)
        env_name = self._alias_map.get(normalized)
        return bool(env_name and self._environ.get(env_name))


class WindowsCredentialProvider:
    """Read Windows Generic Credentials without adding a third-party dependency."""

    provider_id = "windows-credential-manager"

    def __init__(self, namespace: str = "zippoworkz") -> None:
        self.namespace = re.sub(r"[^a-zA-Z0-9_.-]", "-", namespace.strip()) or "zippoworkz"

    @property
    def ready(self) -> bool:
        return os.name == "nt"

    def _target(self, alias: str) -> str:
        return f"ZippoWorkz/{self.namespace}/{validate_alias(alias).removeprefix('secret://')}"

    def get(self, alias: str) -> SecretValue | None:
        normalized = validate_alias(alias)
        if os.name != "nt":
            return None

        from ctypes import wintypes

        class FILETIME(ctypes.Structure):
            _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

        class CREDENTIALW(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        credential_pointer = ctypes.POINTER(CREDENTIALW)()
        advapi = ctypes.WinDLL("Advapi32.dll")
        advapi.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(CREDENTIALW)),
        ]
        advapi.CredReadW.restype = wintypes.BOOL
        advapi.CredFree.argtypes = [ctypes.c_void_p]
        advapi.CredFree.restype = None
        if not advapi.CredReadW(self._target(normalized), 1, 0, ctypes.byref(credential_pointer)):
            return None
        try:
            credential = credential_pointer.contents
            if not credential.CredentialBlob or not credential.CredentialBlobSize:
                return None
            raw = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
            try:
                value = raw.decode("utf-16-le").rstrip("\x00")
            except UnicodeDecodeError:
                value = raw.decode("utf-8").rstrip("\x00")
            return SecretValue(normalized, value) if value else None
        finally:
            advapi.CredFree(credential_pointer)

    def has(self, alias: str) -> bool:
        return self.get(alias) is not None


class CompositeSecretProvider:
    provider_id = "composite"

    def __init__(self, providers: list[SecretProvider]) -> None:
        self.providers = providers

    @property
    def ready(self) -> bool:
        return any(provider.ready for provider in self.providers)

    def get(self, alias: str) -> SecretValue | None:
        normalized = validate_alias(alias)
        for provider in self.providers:
            value = provider.get(normalized)
            if value is not None:
                return value
        return None

    def has(self, alias: str) -> bool:
        normalized = validate_alias(alias)
        return any(provider.has(normalized) for provider in self.providers)


class SecretBroker:
    """Alias-only access boundary with a value-free local audit trail."""

    def __init__(self, provider: SecretProvider, audit_path: Path | None = None) -> None:
        self.provider = provider
        self.audit_path = Path(audit_path) if audit_path else None

    def get(self, alias: str, *, agent: str = "creator-ops") -> SecretValue | None:
        normalized = validate_alias(alias)
        value = self.provider.get(normalized)
        if self.audit_path is not None:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            event = {
                "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
                "alias": normalized,
                "agent": re.sub(r"[^a-zA-Z0-9_.-]", "-", agent)[:80],
                "provider": self.provider.provider_id,
                "found": value is not None,
            }
            with self.audit_path.open("a", encoding="utf-8") as output:
                output.write(json.dumps(event, ensure_ascii=False) + "\n")
        return value


def create_secret_provider(
    environ: Mapping[str, str] | None = None,
) -> SecretProvider:
    source = environ if environ is not None else os.environ
    selected = str(source.get("ZIPPOWORKZ_SECRET_PROVIDER", "auto")).strip().lower()
    namespace = str(source.get("ZIPPOWORKZ_SECRET_NAMESPACE", "zippoworkz"))
    environment = EnvironmentSecretProvider(source)
    windows = WindowsCredentialProvider(namespace)
    if selected in {"none", "disabled"}:
        return NullSecretProvider()
    if selected in {"environment", "env", "runtime-environment"}:
        return environment
    if selected in {"windows", "windows-credential-manager"}:
        return windows
    if selected not in {"", "auto"}:
        return NullSecretProvider()
    return CompositeSecretProvider([windows, environment])
