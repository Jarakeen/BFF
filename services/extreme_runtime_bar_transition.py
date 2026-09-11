from __future__ import annotations

"""One explicit active-bar transition on the unified Extreme runtime timeline."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ExtremeRuntimeBarTransition:
    """Preserve one proven front/back transition in deterministic runtime order."""

    time_seconds: float
    sequence: int
    from_bar: str
    to_bar: str

    def __post_init__(self) -> None:
        timestamp = float(self.time_seconds)
        if not math.isfinite(timestamp) or timestamp < 0.0:
            raise ValueError("runtime bar-transition time must be finite and non-negative")
        sequence = int(self.sequence)
        if sequence < 0:
            raise ValueError("runtime bar-transition sequence cannot be negative")
        from_bar = str(self.from_bar or "").strip().casefold()
        to_bar = str(self.to_bar or "").strip().casefold()
        if from_bar not in {"front", "back"} or to_bar not in {"front", "back"}:
            raise ValueError("runtime bar-transition endpoints must be front or back")
        if from_bar == to_bar:
            raise ValueError("runtime bar transition must change the active bar")

        object.__setattr__(self, "time_seconds", timestamp)
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "from_bar", from_bar)
        object.__setattr__(self, "to_bar", to_bar)


__all__ = ["ExtremeRuntimeBarTransition"]
