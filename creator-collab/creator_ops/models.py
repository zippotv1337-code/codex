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


class PublishStatus(StrEnum):
    NOT_READY = "NOT_READY"
    LOCAL_SCHEDULED = "LOCAL_SCHEDULED"
    PUBLISH_DUE = "PUBLISH_DUE"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    NEEDS_RESCHEDULE_REVIEW = "NEEDS_RESCHEDULE_REVIEW"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    BLOCKED_EXTERNAL_PUBLISHING = "BLOCKED_EXTERNAL_PUBLISHING"
    OWNER_ACTION_REQUIRED = "OWNER_ACTION_REQUIRED"


class SafetyClass(StrEnum):
    SFW = "SFW"
    ADULT = "ADULT"


class ContentStage(StrEnum):
    ALLTAG = "ALLTAG"
    TEASER = "TEASER"
    ADULT_18 = "ADULT_18"


class VisibilityScope(StrEnum):
    PUBLIC_SFW = "PUBLIC_SFW"
    ADULT_ONLY = "ADULT_ONLY"
    LOCAL_ONLY = "LOCAL_ONLY"


class PoseSlot(StrEnum):
    FRONTAL = "FRONTAL"
    LEFT_3Q = "LEFT_3Q"
    RIGHT_3Q = "RIGHT_3Q"
    FULL_BODY_ACTION = "FULL_BODY_ACTION"
    CANDID = "CANDID"


POSE_SLOT_ORDER = (
    PoseSlot.FRONTAL,
    PoseSlot.LEFT_3Q,
    PoseSlot.RIGHT_3Q,
    PoseSlot.FULL_BODY_ACTION,
    PoseSlot.CANDID,
)


@dataclass(frozen=True)
class ComplianceInput:
    platform: str
    safety_class: SafetyClass
    ai_generated: bool
    needs_ai_disclosure: bool
    disclosure_present: bool
    rights_status: str
    content_stage: ContentStage = ContentStage.ALLTAG
    visibility_scope: VisibilityScope = VisibilityScope.PUBLIC_SFW


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
