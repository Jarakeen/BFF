from __future__ import annotations

from dataclasses import dataclass
import math

from .heavy_attack_opportunity import (
    HeavyAttackOpportunityEvidence,
    HeavyAttackPurpose,
)
from .heavy_attack_runtime_state import (
    HeavyAttackEffectRuntimeState,
    evaluate_required_heavy_attack_due_state,
)
from .healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from .healer_wait_decision_provider import HealerHeavyAttackCandidate


@dataclass(frozen=True)
class HeavyAttackDecisionWindow:
    """Caller-proven channel evidence for one current-bar heavy opportunity."""

    time_seconds: float
    bar: str
    available_window_seconds: float
    required_window_seconds: float
    encounter_allows_channel: bool = True
    higher_priority_action_ready: bool = False
    refresh_due_before_completion: bool = False

    def __post_init__(self) -> None:
        bar = str(self.bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("heavy attack decision window bar must be front or back")
        object.__setattr__(self, "bar", bar)

        for name, raw in (
            ("time_seconds", self.time_seconds),
            ("available_window_seconds", self.available_window_seconds),
            ("required_window_seconds", self.required_window_seconds),
        ):
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError(f"heavy attack decision window {name} must be finite")
            if value < 0:
                raise ValueError(f"heavy attack decision window {name} cannot be negative")
            object.__setattr__(self, name, value)
        if self.required_window_seconds <= 0:
            raise ValueError("heavy attack decision required window must be positive")


def build_required_heavy_attack_candidates(
    *,
    incentives: tuple[HealerHeavyAttackBuildIncentive, ...],
    window: HeavyAttackDecisionWindow,
    runtime_states: tuple[HeavyAttackEffectRuntimeState, ...] = (),
) -> tuple[HealerHeavyAttackCandidate, ...]:
    """Build required-effect heavy candidates that are due at this exact window.

    Static build discovery says which required heavy effects exist. Runtime state
    says whether each recurrence is currently eligible. The supplied decision
    window owns encounter safety, channel length, refresh collision, and whether a
    higher-priority action currently preempts the heavy.
    """

    runtime_by_key = {
        (state.incentive_name.casefold(), state.bar): state
        for state in runtime_states
    }
    candidates: list[HealerHeavyAttackCandidate] = []

    for incentive in incentives:
        if incentive.kind is not HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT:
            continue
        if incentive.bar != window.bar:
            continue
        runtime = runtime_by_key.get((incentive.name.casefold(), incentive.bar))
        due = evaluate_required_heavy_attack_due_state(
            incentive=incentive,
            current_time_seconds=window.time_seconds,
            runtime=runtime,
        )
        if not due.due:
            continue

        candidates.append(
            HealerHeavyAttackCandidate(
                bar=incentive.bar,
                evidence=HeavyAttackOpportunityEvidence(
                    weapon=incentive.weapon,
                    purpose=HeavyAttackPurpose.REQUIRED_EFFECT,
                    requirement_name=incentive.name,
                    available_window_seconds=window.available_window_seconds,
                    required_window_seconds=window.required_window_seconds,
                    encounter_allows_channel=window.encounter_allows_channel,
                    higher_priority_action_ready=window.higher_priority_action_ready,
                    refresh_due_before_completion=window.refresh_due_before_completion,
                ),
            )
        )

    return tuple(candidates)
