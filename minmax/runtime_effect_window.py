from __future__ import annotations

"""Deterministic active-window primitives for Phase 7 EffectVariants.

Successful activation and cooldown history remain owned by the runtime
activation layer. This module uses only explicit ``EffectVariant.duration`` to
represent a bounded period during which that activation is active. It does not
infer duration, stacking, refresh behavior, or theoretical uptime.
"""

from dataclasses import dataclass
import math
from typing import Iterable

from .character_build.effect_instance import EffectVariant
from .runtime_effect_activation import RuntimeEffectActivationResult
from .runtime_event import RuntimeEvent


@dataclass(frozen=True)
class RuntimeEffectActiveWindow:
    """One concrete successful activation with an explicit bounded lifetime."""

    effect_name: str
    source: str
    start_time_seconds: float
    end_time_seconds: float
    target: str | None = None
    sequence: int = 0

    def __post_init__(self) -> None:
        if not str(self.effect_name or "").strip():
            raise ValueError("runtime effect window requires an effect identity")
        if not str(self.source or "").strip():
            raise ValueError("runtime effect window requires a source")
        if not math.isfinite(self.start_time_seconds) or self.start_time_seconds < 0:
            raise ValueError("runtime effect window start must be finite and non-negative")
        if not math.isfinite(self.end_time_seconds):
            raise ValueError("runtime effect window end must be finite")
        if self.end_time_seconds <= self.start_time_seconds:
            raise ValueError("runtime effect window end must be after its start")
        if self.sequence < 0:
            raise ValueError("runtime effect window sequence cannot be negative")

    @property
    def duration_seconds(self) -> float:
        return self.end_time_seconds - self.start_time_seconds

    def is_active_at(self, time_seconds: float) -> bool:
        if not math.isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("runtime query time must be finite and non-negative")
        return self.start_time_seconds <= time_seconds < self.end_time_seconds


@dataclass(frozen=True)
class RuntimeEffectWindowPartition:
    """Active and expired windows at one deterministic query time."""

    active: tuple[RuntimeEffectActiveWindow, ...]
    expired: tuple[RuntimeEffectActiveWindow, ...]


def active_window_from_effect_activation(
    event: RuntimeEvent,
    effect: EffectVariant,
    activation: RuntimeEffectActivationResult,
) -> RuntimeEffectActiveWindow | None:
    """Create a bounded active window from one successful activation.

    ``None`` means no bounded window can be represented from canonical effect
    metadata: either the activation failed, duration is absent, or duration is
    zero (an instantaneous effect). Negative/non-finite durations are rejected
    because they are invalid runtime metadata rather than an inference problem.
    """

    if not activation.activated:
        return None

    if effect.duration is None:
        return None

    duration = float(effect.duration)
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("EffectVariant.duration must be finite and non-negative at runtime")
    if duration == 0:
        return None

    return RuntimeEffectActiveWindow(
        effect_name=effect.name,
        source=effect.source,
        start_time_seconds=event.time_seconds,
        end_time_seconds=event.time_seconds + duration,
        target=event.target,
        sequence=event.sequence,
    )


def order_runtime_effect_windows(
    windows: Iterable[RuntimeEffectActiveWindow],
) -> tuple[RuntimeEffectActiveWindow, ...]:
    """Stable deterministic ordering for runtime window audit output."""

    return tuple(
        sorted(
            windows,
            key=lambda window: (
                window.start_time_seconds,
                window.sequence,
                window.effect_name,
                window.source,
                window.target or "",
            ),
        )
    )


def partition_runtime_effect_windows(
    windows: Iterable[RuntimeEffectActiveWindow],
    *,
    at_time_seconds: float,
) -> RuntimeEffectWindowPartition:
    """Partition windows into currently active and already expired groups.

    Windows whose activation starts after ``at_time_seconds`` are neither active
    nor expired yet and are intentionally omitted. A timeline caller may retain
    them as future scheduled activations rather than pretending they already
    exist in live effect state.
    """

    if not math.isfinite(at_time_seconds) or at_time_seconds < 0:
        raise ValueError("runtime query time must be finite and non-negative")

    active: list[RuntimeEffectActiveWindow] = []
    expired: list[RuntimeEffectActiveWindow] = []

    for window in order_runtime_effect_windows(windows):
        if window.start_time_seconds > at_time_seconds:
            continue
        if window.is_active_at(at_time_seconds):
            active.append(window)
        else:
            expired.append(window)

    return RuntimeEffectWindowPartition(
        active=tuple(active),
        expired=tuple(expired),
    )
