from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RuntimeInterval:
    start_seconds: float
    end_seconds: float
    source: str = ""

    def __post_init__(self) -> None:
        start = float(self.start_seconds)
        end = float(self.end_seconds)
        source = str(self.source or "").strip()
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError("runtime interval bounds must be finite")
        if start < 0:
            raise ValueError("runtime interval start must be non-negative")
        if end <= start:
            raise ValueError("runtime interval end must be greater than start")
        object.__setattr__(self, "start_seconds", start)
        object.__setattr__(self, "end_seconds", end)
        object.__setattr__(self, "source", source)


@dataclass(frozen=True)
class RuntimeIntervalCoverage:
    duration_seconds: float
    merged_intervals: tuple[RuntimeInterval, ...]
    covered_seconds: float
    longest_contiguous_seconds: float
    uptime_ratio: float


class RuntimeIntervalCoverageService:
    """Merge explicit runtime windows and compute neutral temporal coverage.

    This service owns no ESO mechanic semantics.  Callers remain responsible for
    proving that an interval really represents an active effect.  Once supplied,
    overlapping/touching windows are unioned deterministically, clipped to the
    requested timeline, and summarized for reusable uptime/duration objectives.
    """

    @staticmethod
    def evaluate(
        intervals: tuple[RuntimeInterval, ...],
        *,
        duration_seconds: float,
    ) -> RuntimeIntervalCoverage:
        duration = float(duration_seconds)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("runtime coverage duration must be finite and greater than zero")

        clipped: list[RuntimeInterval] = []
        for interval in intervals:
            if interval.start_seconds >= duration:
                continue
            start = max(0.0, float(interval.start_seconds))
            end = min(duration, float(interval.end_seconds))
            if end <= start:
                continue
            clipped.append(
                RuntimeInterval(
                    start_seconds=start,
                    end_seconds=end,
                    source=interval.source,
                )
            )

        ordered = sorted(
            clipped,
            key=lambda row: (row.start_seconds, row.end_seconds, row.source.casefold()),
        )
        merged: list[RuntimeInterval] = []
        for interval in ordered:
            if not merged or interval.start_seconds > merged[-1].end_seconds:
                merged.append(interval)
                continue
            previous = merged[-1]
            merged[-1] = RuntimeInterval(
                start_seconds=previous.start_seconds,
                end_seconds=max(previous.end_seconds, interval.end_seconds),
                source=previous.source or interval.source,
            )

        lengths = tuple(row.end_seconds - row.start_seconds for row in merged)
        covered = sum(lengths)
        longest = max(lengths, default=0.0)
        return RuntimeIntervalCoverage(
            duration_seconds=duration,
            merged_intervals=tuple(merged),
            covered_seconds=covered,
            longest_contiguous_seconds=longest,
            uptime_ratio=covered / duration,
        )


__all__ = [
    "RuntimeInterval",
    "RuntimeIntervalCoverage",
    "RuntimeIntervalCoverageService",
]
