from __future__ import annotations

"""Deterministic Phase 7 execution for verified triggered resource restores.

Phase 4 remains authoritative for restoration amounts and resource identities via
``TriggeredRestorationSource``. This module adds only runtime trigger matching and
cooldown state, then emits the existing ``ResourceRestorationEvent`` objects.
"""

from dataclasses import dataclass
import math

from .restoration_events import ResourceRestorationEvent
from .runtime_event import RuntimeEvent
from .triggered_restoration import TriggeredRestorationSource


@dataclass(frozen=True)
class RuntimeTriggeredRestorationRule:
    """One verified restoration source bound to an existing runtime trigger."""

    source: TriggeredRestorationSource
    trigger: str

    def __post_init__(self) -> None:
        if not str(self.trigger or "").strip():
            raise ValueError("triggered restoration rule requires a trigger")


@dataclass(frozen=True)
class RuntimeTriggeredRestorationState:
    """Last successful activation time for one restoration rule."""

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
class RuntimeTriggeredRestorationResult:
    """One runtime restoration attempt and resulting immutable state."""

    activated: bool
    state: RuntimeTriggeredRestorationState
    restoration_events: tuple[ResourceRestorationEvent, ...] = ()
    reasons: tuple[str, ...] = ()
    cooldown_ready_at_seconds: float | None = None


def apply_runtime_triggered_restoration(
    event: RuntimeEvent,
    rule: RuntimeTriggeredRestorationRule,
    *,
    state: RuntimeTriggeredRestorationState = RuntimeTriggeredRestorationState(),
) -> RuntimeTriggeredRestorationResult:
    """Apply one observed event without guessing trigger or cooldown behavior."""

    if event.trigger != rule.trigger:
        return RuntimeTriggeredRestorationResult(
            activated=False,
            state=state,
            reasons=("trigger_mismatch",),
        )

    ready_at: float | None = None
    previous = state.last_activation_time_seconds
    cooldown = float(rule.source.cooldown_seconds)
    if previous is not None:
        if event.time_seconds + 1e-12 < previous:
            raise ValueError("triggered restoration events cannot move runtime state backward in time")
        ready_at = previous + cooldown
        if event.time_seconds + 1e-12 < ready_at:
            return RuntimeTriggeredRestorationResult(
                activated=False,
                state=state,
                reasons=("cooldown_active",),
                cooldown_ready_at_seconds=ready_at,
            )

    updated = RuntimeTriggeredRestorationState(
        last_activation_time_seconds=event.time_seconds,
    )
    return RuntimeTriggeredRestorationResult(
        activated=True,
        state=updated,
        restoration_events=rule.source.create_events(time_seconds=event.time_seconds),
        cooldown_ready_at_seconds=ready_at,
    )
