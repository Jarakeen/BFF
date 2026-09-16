from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.sustain_result import SustainResult
from minmax.ultimate_resource_timeline import UltimateGenerationEvent


@dataclass(frozen=True)
class ExtremeResourceSustainRecord:
    duration_seconds: float
    starting_amount: int
    ending_amount: int
    net_resource: int
    net_resource_per_second: float
    minimum_amount: int
    sustains: bool
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return self.sustains and not self.unresolved


@dataclass(frozen=True)
class ExtremeUltimateGenerationRecord:
    duration_seconds: float
    total_generated: float
    generated_per_second: float
    event_count: int
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved


class ExtremeResourceTimelineRecordService:
    """Project sustained Extreme records from canonical resource timelines.

    Primary-resource timing and sustain interpretation remain owned by Phase 4's
    ``ResourceTimeline`` / ``SustainResult`` pipeline. Ultimate event validation
    remains owned by ``UltimateGenerationEvent``. Extreme only normalizes those
    reviewed timeline outputs into comparable record values over an explicit
    duration.
    """

    @staticmethod
    def _duration(value: float) -> float:
        duration = float(value)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("Extreme timeline duration must be finite and greater than zero")
        return duration

    @classmethod
    def resource_sustain(
        cls,
        sustain: SustainResult,
        *,
        duration_seconds: float,
        unresolved: tuple[str, ...] = (),
    ) -> ExtremeResourceSustainRecord:
        duration = cls._duration(duration_seconds)
        starting = int(sustain.starting_amount)
        ending = int(sustain.ending_amount)
        net = ending - starting
        blockers = list(tuple(unresolved))
        if not sustain.sustains and sustain.first_failure is not None:
            blockers.append(
                f"resource shortfall at {sustain.first_failure.time_seconds:g}s: "
                f"{sustain.first_failure.source} short by {sustain.first_failure.shortfall}"
            )
        return ExtremeResourceSustainRecord(
            duration_seconds=duration,
            starting_amount=starting,
            ending_amount=ending,
            net_resource=net,
            net_resource_per_second=float(net) / duration,
            minimum_amount=int(sustain.minimum_amount),
            sustains=bool(sustain.sustains),
            unresolved=tuple(dict.fromkeys(item for item in blockers if item)),
        )

    @classmethod
    def ultimate_generation(
        cls,
        events: tuple[UltimateGenerationEvent, ...],
        *,
        duration_seconds: float,
        unresolved: tuple[str, ...] = (),
    ) -> ExtremeUltimateGenerationRecord:
        duration = cls._duration(duration_seconds)
        if any(float(event.time_seconds) > duration for event in events):
            raise ValueError("Ultimate generation event cannot occur after Extreme timeline duration")
        total = sum(float(event.amount) for event in events)
        return ExtremeUltimateGenerationRecord(
            duration_seconds=duration,
            total_generated=total,
            generated_per_second=total / duration,
            event_count=len(events),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeResourceSustainRecord",
    "ExtremeResourceTimelineRecordService",
    "ExtremeUltimateGenerationRecord",
]
