from __future__ import annotations

"""Deterministic activation-state transitions for Phase 7 EffectVariants.

Eligibility remains owned by ``runtime_effect_eligibility``. This module applies
one successful runtime activation to the immutable state for that same canonical
EffectVariant. It does not own effect identity and does not infer cooldown scope
from free-form source text.
"""

from dataclasses import dataclass

from .character_build.effect_instance import EffectVariant
from .runtime_effect_eligibility import (
    RuntimeCooldownScope,
    RuntimeEffectEligibilityResult,
    RuntimeEffectState,
    evaluate_effect_variant_runtime_eligibility,
)
from .runtime_event import RuntimeEvent


@dataclass(frozen=True)
class RuntimeEffectActivationResult:
    """Eligibility decision plus the resulting immutable runtime state."""

    activated: bool
    eligibility: RuntimeEffectEligibilityResult
    state: RuntimeEffectState


def _record_global_activation(
    state: RuntimeEffectState,
    *,
    time_seconds: float,
) -> RuntimeEffectState:
    previous = state.last_activation_time_seconds
    if previous is not None and time_seconds + 1e-12 < previous:
        raise ValueError("runtime activations cannot move global cooldown state backward in time")
    return RuntimeEffectState(
        last_activation_time_seconds=float(time_seconds),
        target_last_activation_times=state.target_last_activation_times,
    )


def _record_target_activation(
    state: RuntimeEffectState,
    *,
    target: str,
    time_seconds: float,
) -> RuntimeEffectState:
    previous = state.last_activation_for_target(target)
    if previous is not None and time_seconds + 1e-12 < previous:
        raise ValueError("runtime activations cannot move target cooldown state backward in time")

    updated = {
        candidate: timestamp
        for candidate, timestamp in state.target_last_activation_times
    }
    updated[target] = float(time_seconds)
    return RuntimeEffectState(
        last_activation_time_seconds=state.last_activation_time_seconds,
        target_last_activation_times=tuple(sorted(updated.items())),
    )


def apply_effect_variant_runtime_activation(
    event: RuntimeEvent,
    effect: EffectVariant,
    *,
    state: RuntimeEffectState = RuntimeEffectState(),
    cooldown_scope: RuntimeCooldownScope = RuntimeCooldownScope.GLOBAL,
    chance_roll: float | None = None,
) -> RuntimeEffectActivationResult:
    """Evaluate and, when eligible, record one EffectVariant activation.

    Failed eligibility never mutates runtime history. Successful target-scoped
    activation records only the event target; successful global activation
    records only the global timestamp. The caller remains responsible for
    storing one ``RuntimeEffectState`` per canonical EffectVariant instance.
    """

    eligibility = evaluate_effect_variant_runtime_eligibility(
        event,
        effect,
        state=state,
        cooldown_scope=cooldown_scope,
        chance_roll=chance_roll,
    )
    if not eligibility.eligible:
        return RuntimeEffectActivationResult(
            activated=False,
            eligibility=eligibility,
            state=state,
        )

    if cooldown_scope is RuntimeCooldownScope.TARGET:
        if event.target is None or not str(event.target).strip():
            # Eligibility already enforces target identity when a target-scoped
            # cooldown exists. Preserve the same requirement for zero/no-cooldown
            # target-scoped state rather than creating an anonymous target key.
            raise ValueError("target-scoped runtime activation requires a target identity")
        updated_state = _record_target_activation(
            state,
            target=event.target,
            time_seconds=event.time_seconds,
        )
    else:
        updated_state = _record_global_activation(
            state,
            time_seconds=event.time_seconds,
        )

    return RuntimeEffectActivationResult(
        activated=True,
        eligibility=eligibility,
        state=updated_state,
    )
