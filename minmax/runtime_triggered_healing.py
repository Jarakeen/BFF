from __future__ import annotations

"""Deterministic Phase 7 execution for triggered healing consequences.

The caller supplies an already-resolved healing amount. This layer owns only
runtime trigger matching, optional cooldown state, target identity, and emission
of ``TriggeredHealingEvent``. It does not recalculate healing magnitude.
"""

from dataclasses import dataclass
import math

from .runtime_event import RuntimeEvent
from .triggered_healing import TriggeredHealingEvent


@dataclass(frozen=True)
class RuntimeTriggeredHealingRule:
    """One triggered-healing consequence bound to an existing runtime trigger."""

    source: str
    trigger: str
    cooldown_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not str(self.source or "").strip():
            raise ValueError("triggered healing rule requires a source")
        if not str(self.trigger or "").strip():
            raise ValueError("triggered healing rule requires a trigger")
        if not math.isfinite(self.cooldown_seconds) or self.cooldown_seconds < 0:
            raise ValueError("triggered healing cooldown must be finite and non-negative")


@dataclass(frozen=True)
class RuntimeTriggeredHealingState:
    """Last successful activation time for one triggered-healing rule."""

    last_activation_time_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.last_activation_time_seconds is not None and (
            not math.isfinite(self.last_activation_time_seconds)
            or self.last_activation_time_seconds < 0
        ):
            raise ValueError(
                "last_activation_time_seconds must be finite and non-negative when present"
            )


@dataclass(frozen=True)
class RuntimeTriggeredHealingResult:
    """One runtime healing attempt and resulting immutable state."""

    activated: bool
    state: RuntimeTriggeredHealingState
    healing_event: TriggeredHealingEvent | None = None
    reasons: tuple[str, ...] = ()
    cooldown_ready_at_seconds: float | None = None


def apply_runtime_triggered_healing(
    event: RuntimeEvent,
    rule: RuntimeTriggeredHealingRule,
    *,
    amount: float,
    state: RuntimeTriggeredHealingState = RuntimeTriggeredHealingState(),
    target: str | None = None,
) -> RuntimeTriggeredHealingResult:
    """Emit one resolved heal when the observed trigger and cooldown allow it."""

    if not math.isfinite(amount) or amount < 0:
        raise ValueError("triggered healing amount must be finite and non-negative")

    if event.trigger != rule.trigger:
        return RuntimeTriggeredHealingResult(
            activated=False,
            state=state,
            reasons=("trigger_mismatch",),
        )

    resolved_target = str(target if target is not None else (event.target or "")).strip()
    if not resolved_target:
        return RuntimeTriggeredHealingResult(
            activated=False,
            state=state,
            reasons=("target_identity_required",),
        )

    ready_at: float | None = None
    previous = state.last_activation_time_seconds
    if previous is not None:
        if event.time_seconds + 1e-12 < previous:
            raise ValueError("triggered healing events cannot move runtime state backward in time")
        ready_at = previous + float(rule.cooldown_seconds)
        if event.time_seconds + 1e-12 < ready_at:
            return RuntimeTriggeredHealingResult(
                activated=False,
                state=state,
                reasons=("cooldown_active",),
                cooldown_ready_at_seconds=ready_at,
            )

    updated = RuntimeTriggeredHealingState(
        last_activation_time_seconds=event.time_seconds,
    )
    healing = TriggeredHealingEvent(
        time_seconds=event.time_seconds,
        amount=float(amount),
        source=rule.source,
        target=resolved_target,
    )
    return RuntimeTriggeredHealingResult(
        activated=True,
        state=updated,
        healing_event=healing,
        cooldown_ready_at_seconds=ready_at,
    )
