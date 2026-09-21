from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from html import unescape
from typing import Any, Protocol

from .database import CreatorDatabase, utc_now


CONNECTED = "CONNECTED"
READ_ONLY = "READ_ONLY"
WRITE_READY = "WRITE_READY"
SESSION_EXPIRED = "SESSION_EXPIRED"
HUMAN_GATE = "HUMAN_GATE"
LIMITED = "LIMITED"
ERROR = "ERROR"

ALLOWED_ACCOUNT_STATUSES = {
    CONNECTED,
    READ_ONLY,
    WRITE_READY,
    SESSION_EXPIRED,
    HUMAN_GATE,
    LIMITED,
    ERROR,
}


@dataclass(frozen=True)
class FiverrGigSnapshot:
    gig_key: str
    title: str
    status: str
    public_url: str | None = None
    edit_url: str | None = None
    packages: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    assets: list[str] | None = None


@dataclass(frozen=True)
class FiverrAccountSnapshot:
    username: str
    connection_status: str
    session_status: str
    read_provider: str
    write_provider: str
    public_profile_url: str
    gigs: tuple[FiverrGigSnapshot, ...] = ()
    last_error: str | None = None
    next_action: str = "NONE"


class FiverrReadProvider(Protocol):
    name: str

    def read(self, username: str) -> FiverrAccountSnapshot: ...


class FiverrWriteProvider(Protocol):
    name: str

    def readiness(self) -> str: ...


class FiverrPublicHttpReadProvider:
    """Free public-data reader; never calls private or undocumented endpoints."""

    name = "direct-public-http"
    USER_AGENT = "Mozilla/5.0 (compatible; ZippoWorkz/1.0; public Fiverr sync)"

    @staticmethod
    def _strip_html(value: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(value))).strip()

    def read(self, username: str) -> FiverrAccountSnapshot:
        normalized = username.strip().lstrip("@").lower()
        if not re.fullmatch(r"[a-z0-9_-]{3,64}", normalized):
            raise ValueError("invalid_fiverr_username")
        profile_url = f"https://www.fiverr.com/{normalized}"
        request = urllib.request.Request(profile_url, headers={"User-Agent": self.USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                final_url = response.geturl()
                payload = response.read(2_000_000).decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError):
            return FiverrAccountSnapshot(
                username=normalized,
                connection_status=LIMITED,
                session_status="PUBLIC_READ_UNAVAILABLE",
                read_provider=self.name,
                write_provider="playwright-seller-webflow",
                public_profile_url=profile_url,
                last_error="public_http_unavailable",
                next_action="Use authenticated browser snapshot without retry loop",
            )
        lowered = payload.lower()
        if "loading challenge" in lowered or "pxcr" in lowered or "captcha" in lowered:
            return FiverrAccountSnapshot(
                username=normalized,
                connection_status=LIMITED,
                session_status="PUBLIC_CHALLENGE",
                read_provider=self.name,
                write_provider="playwright-seller-webflow",
                public_profile_url=final_url,
                last_error="fiverr_public_challenge",
                next_action="Use authenticated browser snapshot; do not bypass challenge",
            )
        title_match = re.search(r"<title[^>]*>(.*?)</title>", payload, re.I | re.S)
        title = self._strip_html(title_match.group(1)) if title_match else ""
        status = READ_ONLY if normalized in lowered or normalized in final_url.lower() else LIMITED
        return FiverrAccountSnapshot(
            username=normalized,
            connection_status=status,
            session_status="PUBLIC_READ_OK" if status == READ_ONLY else "PUBLIC_PROFILE_UNCONFIRMED",
            read_provider=self.name,
            write_provider="playwright-seller-webflow",
            public_profile_url=final_url,
            last_error=None if status == READ_ONLY else "public_profile_not_confirmed",
            next_action="Sync authenticated seller snapshot",
            gigs=(),
        )


class FiverrPlaywrightWriteProvider:
    """Descriptor for the supported normal seller-webflow automation lane."""

    name = "playwright-seller-webflow"

    def __init__(self, session_status: str) -> None:
        self.session_status = session_status

    def readiness(self) -> str:
        if self.session_status == "AUTHENTICATED_SELLER":
            return WRITE_READY
        if self.session_status in {"CAPTCHA", "OTP", "KYC", "TERMS"}:
            return HUMAN_GATE
        if self.session_status == "EXPIRED":
            return SESSION_EXPIRED
        return LIMITED


class FiverrAutomationService:
    """Durable Fiverr account/gig sync and idempotent operation ledger."""

    def __init__(self, database: CreatorDatabase) -> None:
        self.database = database

    @staticmethod
    def _account_key(username: str) -> str:
        return f"fiverr:{username.strip().lstrip('@').lower()}"

    @staticmethod
    def _operation_key(account_key: str, kind: str, fingerprint: str) -> str:
        return hashlib.sha256(f"{account_key}|{kind}|{fingerprint}".encode()).hexdigest()

    def sync(self, snapshot: FiverrAccountSnapshot) -> dict[str, Any]:
        if snapshot.connection_status not in ALLOWED_ACCOUNT_STATUSES:
            raise ValueError("invalid_fiverr_connection_status")
        username = snapshot.username.strip().lstrip("@").lower()
        account_key = self._account_key(username)
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO fiverr_accounts(
                    account_key,username,public_profile_url,connection_status,
                    session_status,read_provider,write_provider,last_sync_at,
                    last_error,next_action,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(account_key) DO UPDATE SET
                    public_profile_url=excluded.public_profile_url,
                    connection_status=excluded.connection_status,
                    session_status=excluded.session_status,
                    read_provider=excluded.read_provider,
                    write_provider=excluded.write_provider,
                    last_sync_at=excluded.last_sync_at,
                    last_error=excluded.last_error,
                    next_action=excluded.next_action,
                    updated_at=excluded.updated_at
                """,
                (
                    account_key, username, snapshot.public_profile_url,
                    snapshot.connection_status, snapshot.session_status,
                    snapshot.read_provider, snapshot.write_provider, now,
                    snapshot.last_error, snapshot.next_action, now, now,
                ),
            )
            account_id = int(
                connection.execute(
                    "SELECT id FROM fiverr_accounts WHERE account_key=?", (account_key,)
                ).fetchone()[0]
            )
            for gig in snapshot.gigs:
                connection.execute(
                    """
                    INSERT INTO fiverr_gigs(
                        account_id,gig_key,title,public_url,edit_url,status,
                        packages_json,metrics_json,assets_json,source,
                        last_verified_at,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(gig_key) DO UPDATE SET
                        title=excluded.title,public_url=excluded.public_url,
                        edit_url=excluded.edit_url,status=excluded.status,
                        packages_json=excluded.packages_json,
                        metrics_json=excluded.metrics_json,
                        assets_json=excluded.assets_json,source=excluded.source,
                        last_verified_at=excluded.last_verified_at,
                        updated_at=excluded.updated_at
                    """,
                    (
                        account_id, gig.gig_key, gig.title, gig.public_url,
                        gig.edit_url, gig.status,
                        json.dumps(gig.packages or {}, ensure_ascii=False),
                        json.dumps(gig.metrics or {}, ensure_ascii=False),
                        json.dumps(gig.assets or [], ensure_ascii=False),
                        snapshot.read_provider, now, now, now,
                    ),
                )
        return self.status(username)

    def sync_public(self, username: str) -> dict[str, Any]:
        return self.sync(FiverrPublicHttpReadProvider().read(username))

    def record_browser_snapshot(
        self,
        *,
        username: str,
        gigs: tuple[FiverrGigSnapshot, ...],
        session_status: str = "AUTHENTICATED_SELLER",
        next_action: str = "Verify public Gig URL",
    ) -> dict[str, Any]:
        write_status = FiverrPlaywrightWriteProvider(session_status).readiness()
        return self.sync(
            FiverrAccountSnapshot(
                username=username,
                connection_status=write_status,
                session_status=session_status,
                read_provider="playwright-authenticated-read",
                write_provider="playwright-seller-webflow",
                public_profile_url=f"https://www.fiverr.com/{username}",
                gigs=gigs,
                next_action=next_action,
            )
        )

    def record_human_gate(
        self,
        *,
        username: str,
        gate_type: str,
        page_url: str,
        action: str,
        reason: str,
        after_action: str,
        costs_money: bool = False,
    ) -> dict[str, Any]:
        account = self.status(username)
        if account.get("status") == "NOT_CONFIGURED":
            self.record_browser_snapshot(username=username, gigs=(), session_status="CAPTCHA")
            account = self.status(username)
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO fiverr_human_gates(
                    account_id,gate_type,page_url,action,reason,after_action,
                    costs_money,status,created_at)
                VALUES (?,?,?,?,?,?,?,'OPEN',?)
                """,
                (
                    account["account_id"], gate_type, page_url, action, reason,
                    after_action, 1 if costs_money else 0, now,
                ),
            )
            connection.execute(
                """
                UPDATE fiverr_accounts SET connection_status=?,session_status=?,
                    last_human_gate_at=?,last_error=?,next_action=?,updated_at=?
                WHERE id=?
                """,
                (HUMAN_GATE, gate_type, now, reason, action, now, account["account_id"]),
            )
        return self.status(username)

    def resolve_human_gate(
        self,
        *,
        username: str,
        gate_type: str,
        session_status: str = "AUTHENTICATED_SELLER",
        next_action: str = "Verify Gig fields before write",
    ) -> dict[str, Any]:
        account = self.status(username)
        if account.get("status") == "NOT_CONFIGURED":
            raise ValueError("fiverr_account_not_configured")
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE fiverr_human_gates SET status='RESOLVED',resolved_at=?
                WHERE account_id=? AND gate_type=? AND status='OPEN'
                """,
                (now, account["account_id"], gate_type),
            )
            connection.execute(
                """
                UPDATE fiverr_accounts SET connection_status=?,session_status=?,
                    last_error=NULL,next_action=?,updated_at=? WHERE id=?
                """,
                (
                    FiverrPlaywrightWriteProvider(session_status).readiness(),
                    session_status,
                    next_action,
                    now,
                    account["account_id"],
                ),
            )
        return self.status(username)

    def reserve_operation(
        self,
        *,
        username: str,
        kind: str,
        fingerprint: str,
        detail: dict[str, Any] | None = None,
        gig_key: str | None = None,
    ) -> dict[str, Any]:
        account = self.status(username)
        if account.get("status") == "NOT_CONFIGURED":
            raise ValueError("fiverr_account_not_configured")
        gig_id = None
        if gig_key:
            row = self.database.one("SELECT id FROM fiverr_gigs WHERE gig_key=?", (gig_key,))
            if row is None:
                raise KeyError("fiverr_gig_not_found")
            gig_id = int(row["id"])
        account_key = self._account_key(username)
        operation_key = self._operation_key(account_key, kind, fingerprint)
        now = utc_now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO fiverr_operations(
                    operation_key,account_id,gig_id,kind,fingerprint,status,
                    detail_json,created_at,updated_at)
                VALUES (?,?,?,?,?,'PLANNED',?,?,?)
                """,
                (
                    operation_key, account["account_id"], gig_id, kind,
                    fingerprint, json.dumps(detail or {}, ensure_ascii=False), now, now,
                ),
            )
            row = connection.execute(
                "SELECT id,status FROM fiverr_operations WHERE operation_key=?",
                (operation_key,),
            ).fetchone()
        return {
            "operation_id": int(row["id"]),
            "operation_key": operation_key,
            "status": row["status"],
            "reused": cursor.rowcount == 0,
        }

    def status(self, username: str) -> dict[str, Any]:
        account = self.database.one(
            "SELECT * FROM fiverr_accounts WHERE account_key=?",
            (self._account_key(username),),
        )
        if account is None:
            return {"schema": "zippo-fiverr-status-v1", "status": "NOT_CONFIGURED"}
        gigs = []
        for row in self.database.all(
            "SELECT * FROM fiverr_gigs WHERE account_id=? ORDER BY id", (account["id"],)
        ):
            item = dict(row)
            for key in ("packages_json", "metrics_json", "assets_json"):
                item[key.removesuffix("_json")] = json.loads(item.pop(key))
            gigs.append(item)
        gates = [
            dict(row)
            for row in self.database.all(
                "SELECT * FROM fiverr_human_gates WHERE account_id=? AND status='OPEN' ORDER BY id",
                (account["id"],),
            )
        ]
        return {
            "schema": "zippo-fiverr-status-v1",
            "status": account["connection_status"],
            "account_id": int(account["id"]),
            "username": account["username"],
            "public_profile_url": account["public_profile_url"],
            "session_status": account["session_status"],
            "read_provider": account["read_provider"],
            "write_provider": account["write_provider"],
            "last_successful_sync": account["last_sync_at"],
            "last_write_test": account["last_write_test_at"],
            "last_human_gate": account["last_human_gate_at"],
            "last_error": account["last_error"],
            "next_action": account["next_action"],
            "active_gig_count": sum(gig["status"] == "ACTIVE" for gig in gigs),
            "gigs": gigs,
            "human_gates": gates,
        }
