from __future__ import annotations

from dataclasses import dataclass

from .models import ContentStage


TARGET_SHARES = {
    ContentStage.ALLTAG: 0.40,
    ContentStage.TEASER: 0.35,
    ContentStage.ADULT_18: 0.25,
}


@dataclass(frozen=True)
class MixRecommendation:
    next_stage: ContentStage
    current: dict[str, int]
    target_percent: dict[str, int]


class ContentMixPlanner:
    """Suggest the largest content-stage deficit without creating or publishing."""

    def recommend(self, counts: dict[str, int]) -> MixRecommendation:
        normalized = {stage: int(counts.get(stage.value, 0)) for stage in TARGET_SHARES}
        next_total = sum(normalized.values()) + 1
        stage = max(
            TARGET_SHARES,
            key=lambda candidate: (
                TARGET_SHARES[candidate] * next_total - normalized[candidate],
                -list(TARGET_SHARES).index(candidate),
            ),
        )
        return MixRecommendation(
            next_stage=stage,
            current={candidate.value: normalized[candidate] for candidate in TARGET_SHARES},
            target_percent={
                candidate.value: round(share * 100)
                for candidate, share in TARGET_SHARES.items()
            },
        )

    def plan(self, slots: int = 20) -> tuple[ContentStage, ...]:
        counts: dict[str, int] = {}
        result: list[ContentStage] = []
        for _ in range(slots):
            stage = self.recommend(counts).next_stage
            result.append(stage)
            counts[stage.value] = counts.get(stage.value, 0) + 1
        return tuple(result)
