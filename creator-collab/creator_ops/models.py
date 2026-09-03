from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ContentStatus(StrEnum):
    PLANNED = "PLANNED"
    GENERATING = "GENERATING"
    CURATING = "CURATING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    OWNER_APPROVED = "OWNER_APPROVED"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    ANALYZED = "ANALYZED"
    PARTIAL_READY = "PARTIAL_READY"
    BLOCKED = "BLOCKED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"


class SafetyClass(StrEnum):
    SFW = "SFW"
    ADULT = "ADULT"


@dataclass(frozen=True)
class ComplianceInput:
    platform: str
    safety_class: SafetyClass
    ai_generated: bool
    needs_ai_disclosure: bool
    disclosure_present: bool
    rights_status: str


@dataclass(frozen=True)
class ComplianceResult:
    allowed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class VerticalRunResult:
    run_key: str
    creator_slug: str
    content_id: int
    publication_id: int
    final_status: ContentStatus
    learning_decision: str
    mock_url: str
    reused: bool = False


@dataclass(frozen=True)
class ScheduleDecision:
    scheduled_at: datetime
    local_time: str
    source: str
    confidence: float
    score: float


@dataclass(frozen=True)
class AudioSelection:
    label: str
    reference: str | None
    license_status: str
    provider: str
    fallback_used: bool


@dataclass(frozen=True)
class EveningRunResult:
    batch_key: str
    status: str
    requested_at: str
    results: tuple[VerticalRunResult, ...]
    reason: str | None = None
