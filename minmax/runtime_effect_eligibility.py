from __future__ import annotations

"""Deterministic Phase 7 runtime eligibility for canonical EffectVariants.

EffectVariant remains authoritative for effect identity, trigger, chance,
cooldown, and static eligibility. This module applies only runtime facts supplied
by the caller: the observed event, prior activation times, explicit cooldown
scope, and an optional deterministic chance roll.
"""

from dataclasses import dataclass
from enum import Enum
import math

from .character_build.effect_instance import EffectVariant
from .runtime_event import RuntimeEvent, runtime_event_matches_effect_variant


class RuntimeCooldownScope(str, Enum):
    GLOBAL = "global"
    TARGET = "target"


@dataclass(frozen=True)
class RuntimeEffectState:
    """Prior activation facts for one canonical EffectVariant."""

    last_activation_time_seconds: float | None = None
    target_last_activation_times: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        if self.last_activation_time_seconds is not None:
            if (
                not math.isfinite(self.last_activation_time_seconds)
                or self.last_activation_time_seconds < 0
            ):
                raise ValueError(
                    "last_activation_time_seconds must be finite and non-negative when present"
                )

        seen: set[str] = set()
        for target, timestamp in self.target_last_activation_times:
            normalized_target = str(target or "").strip()
            if not normalized_target:
                raise ValueError("target cooldown state requires a non-empty target identity")
            if normalized_target in seen:
                raise ValueError(f"duplicate target cooldown state: {normalized_target}")
            seen.add(normalized_target)
            if not math.isfinite(timestamp) or timestamp < 0:
                raise ValueError("target cooldown timestamps must be finite and non-negative")

    def last_activation_for_target(self, target: str) -> float | None:
        for candidate, timestamp in self.target_last_activation_times:
            if candidate == target:
                return timestamp
        return None


@dataclass(frozen=True)
class RuntimeEffectEligibilityResult:
    eligible: bool
    reasons: tuple[str, ...] = ()
    cooldown_ready_at_seconds: float | None = None
    chance_roll_required: bool = False


def evaluate_effect_variant_runtime_eligibility(
    event: RuntimeEvent,
    effect: EffectVariant,
    *,
    state: RuntimeEffectState = RuntimeEffectState(),
    cooldown_scope: RuntimeCooldownScope = RuntimeCooldownScope.GLOBAL,
    chance_roll: float | None = None,
) -> RuntimeEffectEligibilityResult:
    """Evaluate whether an EffectVariant may activate for one observed event.

    No random number is generated here. When ``effect.chance`` is below 1.0,
    callers must provide an explicit deterministic ``chance_roll`` in [0, 1].
    Per-target cooldown behavior is likewise caller-selected rather than inferred
    from free-form condition text.
    """

    if not effect.eligible:
        return RuntimeEffectEligibilityResult(
            eligible=False,
            reasons=("effect_not_statically_eligible",),
        )

    reasons: list[str] = []

    if not runtime_event_matches_effect_variant(event, effect):
        reasons.append("trigger_mismatch")

    cooldown_ready_at: float | None = None
    if effect.cooldown is not None and effect.cooldown > 0:
        last_activation: float | None
        if cooldown_scope is RuntimeCooldownScope.TARGET:
            if event.target is None or not str(event.target).strip():
                reasons.append("target_identity_required_for_cooldown")
                last_activation = None
            else:
                last_activation = state.last_activation_for_target(event.target)
        else:
            last_activation = state.last_activation_time_seconds

        if last_activation is not None:
            cooldown_ready_at = last_activation + float(effect.cooldown)
            if event.time_seconds + 1e-12 < cooldown_ready_at:
                reasons.append("cooldown_active")

    chance = effect.chance if effect.chance is not None else 1.0
    chance_roll_required = chance < 1.0 and chance_roll is None
    if chance_roll_required:
        reasons.append("chance_roll_required")
    elif chance_roll is not None:
        if not math.isfinite(chance_roll) or not 0.0 <= chance_roll <= 1.0:
            raise ValueError("chance_roll must be finite and between 0 and 1")
        if chance_roll >= chance:
            reasons.append("chance_failed")

    return RuntimeEffectEligibilityResult(
        eligible=not reasons,
        reasons=tuple(reasons),
        cooldown_ready_at_seconds=cooldown_ready_at,
        chance_roll_required=chance_roll_required,
    )
