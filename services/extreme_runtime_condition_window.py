from __future__ import annotations

"""Role-neutral explicit condition window on the unified Extreme runtime timeline."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ExtremeRuntimeConditionWindow:
    """One explicitly evidenced condition window evaluated by E1 at exact time ``t``.

    This type carries temporal truth only. It does not decide whether a build is
    mechanically eligible for the condition's downstream effect. Build/passive/
    weapon/class legality remains owned by the mechanic-specific resolver.
    """

    condition_id: str
    active_from_seconds: float
    active_until_seconds: float
    source_evidence: str
    sequence: int = 0

    def __post_init__(self) -> None:
        condition_id = str(self.condition_id or "").strip().casefold()
        source_evidence = str(self.source_evidence or "").strip()
        start = float(self.active_from_seconds)
        end = float(self.active_until_seconds)
        sequence = int(self.sequence)

        if not condition_id:
            raise ValueError("runtime condition id cannot be empty")
        if not source_evidence:
            raise ValueError("runtime condition window requires source evidence")
        if not math.isfinite(start) or start < 0.0:
            raise ValueError("runtime condition start must be finite and non-negative")
        if not math.isfinite(end) or end < start:
            raise ValueError("runtime condition end must be finite and not precede its start")
        if sequence < 0:
            raise ValueError("runtime condition sequence cannot be negative")

        object.__setattr__(self, "condition_id", condition_id)
        object.__setattr__(self, "active_from_seconds", start)
        object.__setattr__(self, "active_until_seconds", end)
        object.__setattr__(self, "source_evidence", source_evidence)
        object.__setattr__(self, "sequence", sequence)

    @property
    def time_seconds(self) -> float:
        return self.active_from_seconds

    def active_at(self, time_seconds: float) -> bool:
        instant = float(time_seconds)
        return self.active_from_seconds - 1e-12 <= instant <= self.active_until_seconds + 1e-12


__all__ = ["ExtremeRuntimeConditionWindow"]
