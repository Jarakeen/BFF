from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class RotationDemandKind(str, Enum):
    HEALING = "healing"
    DAMAGE = "damage"
    MITIGATION = "mitigation"
    SUPPORT = "support"


class RotationDemandPattern(str, Enum):
    BURST = "burst"
    SUSTAINED = "sustained"


@dataclass(frozen=True)
class RotationDemandWindow:
    """One encounter-driven role requirement over a bounded time window.

    This contract describes *when* a role outcome matters. It deliberately does
    not invent required HPS/DPS/mitigation values. Numeric output thresholds
    belong to verified encounter evidence or caller-supplied assumptions later.
    Resource planning and action selection can use these windows without the
    Rotation Engine needing healer-, DD-, or tank-specific timestamp models.
    """

    name: str
    start_seconds: float
    end_seconds: float
    kind: RotationDemandKind
    pattern: RotationDemandPattern
    target_count: int = 1

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        if not name:
            raise ValueError("rotation demand name is required")
        object.__setattr__(self, "name", name)

        start = float(self.start_seconds)
        end = float(self.end_seconds)
        if not math.isfinite(start) or start < 0:
            raise ValueError("rotation demand start must be finite and non-negative")
        if not math.isfinite(end) or end <= start:
            raise ValueError("rotation demand end must be finite and after start")
        object.__setattr__(self, "start_seconds", start)
        object.__setattr__(self, "end_seconds", end)

        if not isinstance(self.kind, RotationDemandKind):
            object.__setattr__(self, "kind", RotationDemandKind(str(self.kind)))
        if not isinstance(self.pattern, RotationDemandPattern):
            object.__setattr__(self, "pattern", RotationDemandPattern(str(self.pattern)))

        if int(self.target_count) <= 0:
            raise ValueError("rotation demand target count must be positive")
        object.__setattr__(self, "target_count", int(self.target_count))

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


def create_staggered_burst_demands(
    *,
    name: str,
    first_start_seconds: float,
    second_start_seconds: float,
    deadline_seconds: float,
    kind: RotationDemandKind = RotationDemandKind.HEALING,
) -> tuple[RotationDemandWindow, RotationDemandWindow]:
    """Create two independently deadline-bound staggered burst requirements.

    Useful for mechanics such as two Sunspire hardmode Ice Cages: each target
    has its own rescue deadline even though the two windows overlap in one
    continuous resource timeline.
    """

    first = float(first_start_seconds)
    second = float(second_start_seconds)
    deadline = float(deadline_seconds)
    if not math.isfinite(deadline) or deadline <= 0:
        raise ValueError("burst deadline must be finite and positive")
    if not math.isfinite(second) or second <= first:
        raise ValueError("second burst start must be finite and after first start")

    return (
        RotationDemandWindow(
            name=f"{name} 1",
            start_seconds=first,
            end_seconds=first + deadline,
            kind=kind,
            pattern=RotationDemandPattern.BURST,
        ),
        RotationDemandWindow(
            name=f"{name} 2",
            start_seconds=second,
            end_seconds=second + deadline,
            kind=kind,
            pattern=RotationDemandPattern.BURST,
        ),
    )
