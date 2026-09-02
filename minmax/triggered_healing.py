from __future__ import annotations

"""Minimal event contract for Phase 7 triggered healing consequences.

Healing magnitude remains owned by the existing static/component healing math.
This module represents only a resolved healing consequence at a concrete runtime
instant so temporal trigger execution does not invent a second healing formula.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class TriggeredHealingEvent:
    """One resolved triggered heal emitted onto the runtime timeline."""

    time_seconds: float
    amount: float
    source: str
    target: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.time_seconds) or self.time_seconds < 0:
            raise ValueError("Triggered healing event time must be finite and non-negative")
        if not math.isfinite(self.amount) or self.amount < 0:
            raise ValueError("Triggered healing amount must be finite and non-negative")
        if not str(self.source or "").strip():
            raise ValueError("Triggered healing event requires a source")
        if not str(self.target or "").strip():
            raise ValueError("Triggered healing event requires a target")
