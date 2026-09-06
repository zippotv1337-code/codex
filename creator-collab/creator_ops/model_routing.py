from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "model_routing.toml"


@dataclass(frozen=True)
class ModelRoutingPolicy:
    preferred_model: str
    fallback_model: str
    reasoning_effort: str
    preferred_required: bool
    capability_based: bool

    @classmethod
    def load(cls, path: Path = DEFAULT_POLICY_PATH) -> "ModelRoutingPolicy":
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        selection = payload.get("selection", {})
        policy = cls(
            preferred_model=str(selection.get("preferred_model", "")).strip(),
            fallback_model=str(selection.get("fallback_model", "")).strip(),
            reasoning_effort=str(selection.get("reasoning_effort", "high")).strip(),
            preferred_required=bool(selection.get("preferred_required", False)),
            capability_based=bool(selection.get("capability_based", True)),
        )
        if not policy.preferred_model or not policy.fallback_model:
            raise ValueError("model_routing_requires_preferred_and_fallback")
        if policy.reasoning_effort not in {"low", "medium", "high", "xhigh", "max"}:
            raise ValueError("unsupported_reasoning_effort")
        if policy.preferred_required:
            raise ValueError("preferred_model_must_remain_optional")
        if not policy.capability_based:
            raise ValueError("model_routing_must_be_capability_based")
        return policy

    def resolve(self, available_models: Iterable[str]) -> dict[str, object]:
        available = set(available_models)
        if self.preferred_model in available:
            selected = self.preferred_model
            source = "preferred-capability"
        elif self.fallback_model in available:
            selected = self.fallback_model
            source = "stable-fallback"
        else:
            selected = None
            source = "runtime-default"
        return {
            **asdict(self),
            "selected_model": selected,
            "selection_source": source,
        }

    def describe(self) -> dict[str, object]:
        return {
            **asdict(self),
            "selected_model": None,
            "selection_source": "resolved-at-runtime",
        }
