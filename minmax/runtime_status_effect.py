from __future__ import annotations

"""Runtime status-effect application built on the Phase 7 effect engine.

Status effects remain ordinary canonical ``EffectVariant`` instances whose
category is ``SupportEffectCategory.STATUS``. This module does not duplicate
trigger/chance/cooldown/window/stacking logic; it adapts the verified runtime
transition so callers can ask target-scoped status truth at a specific time.
"""

from dataclasses import dataclass
import math

from .character_build.effect_instance import EffectVariant
from .runtime_effect_eligibility import RuntimeCooldownScope
from .runtime_effect_runtime import (
    RuntimeEffectRuntimeState,
    RuntimeEffectTransitionResult,
    apply_effect_variant_runtime_event,
)
from .runtime_event import RuntimeEvent
from .support_effect_category import SupportEffectCategory


@dataclass(frozen=True)
class RuntimeStatusApplicationResult:
    """One status application attempt and resulting canonical effect state."""

    transition: RuntimeEffectTransitionResult
    unresolved: tuple[str, ...] = ()

    @property
    def applied(self) -> bool:
        return self.transition.activated

    @property
    def state(self) -> RuntimeEffectRuntimeState:
        return self.transition.state

    @property
    def resolved(self) -> bool:
        return not self.unresolved


def apply_runtime_status_event(
    event: RuntimeEvent,
    effect: EffectVariant,
    *,
    state: RuntimeEffectRuntimeState = RuntimeEffectRuntimeState(),
    cooldown_scope: RuntimeCooldownScope = RuntimeCooldownScope.GLOBAL,
    chance_roll: float | None = None,
) -> RuntimeStatusApplicationResult:
    """Apply one canonical status effect to one explicit runtime target.

    The event target is mandatory because status truth is target-scoped. A
    successful application with no explicit positive duration records the
    activation/cooldown history but cannot establish ongoing status truth, so
    that limitation is returned as ``status_duration_required``.
    """

    if effect.category is not SupportEffectCategory.STATUS:
        raise ValueError("runtime status application requires a STATUS EffectVariant")
    if event.target is None or not str(event.target).strip():
        raise ValueError("runtime status application requires an explicit target identity")

    transition = apply_effect_variant_runtime_event(
        event,
        effect,
        state=state,
        cooldown_scope=cooldown_scope,
        chance_roll=chance_roll,
    )

    unresolved = list(transition.unresolved)
    if transition.activated and (effect.duration is None or float(effect.duration) <= 0):
        unresolved.append("status_duration_required")

    return RuntimeStatusApplicationResult(
        transition=transition,
        unresolved=tuple(dict.fromkeys(unresolved)),
    )


def status_active_on_target(
    state: RuntimeEffectRuntimeState,
    *,
    target: str,
    at_time_seconds: float,
) -> bool:
    """Whether any retained status window is active on ``target`` now."""

    if not str(target or "").strip():
        raise ValueError("status query requires a target identity")
    if not math.isfinite(at_time_seconds) or at_time_seconds < 0:
        raise ValueError("status query time must be finite and non-negative")

    return any(
        window.target == target and window.is_active_at(at_time_seconds)
        for window in state.windows
    )


def active_status_targets(
    state: RuntimeEffectRuntimeState,
    *,
    at_time_seconds: float,
) -> tuple[str, ...]:
    """Return deterministic target identities with this status active now."""

    if not math.isfinite(at_time_seconds) or at_time_seconds < 0:
        raise ValueError("status query time must be finite and non-negative")

    targets = {
        window.target
        for window in state.windows
        if window.target is not None and window.is_active_at(at_time_seconds)
    }
    return tuple(sorted(targets))
