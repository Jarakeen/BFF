from __future__ import annotations

from dataclasses import dataclass

from services.runtime_interval_coverage_service import (
    RuntimeInterval,
    RuntimeIntervalCoverageService,
)


@dataclass(frozen=True)
class ExtremeInvisibilityRuntimeResult:
    duration_seconds: float
    longest_contiguous_seconds: float
    covered_seconds: float
    uptime_ratio: float
    window_count: int
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved


class ExtremeInvisibilityRuntimeService:
    """Project duration and uptime records from proven invisibility windows.

    Source discovery is deliberately external to this service.  The caller must
    prove each supplied interval represents legal player invisibility.  Extreme
    reuses the neutral interval-union service so duration and uptime share one
    timeline truth instead of maintaining separate overlap logic.
    """

    @staticmethod
    def evaluate(
        windows: tuple[RuntimeInterval, ...],
        *,
        duration_seconds: float,
        unresolved: tuple[str, ...] = (),
    ) -> ExtremeInvisibilityRuntimeResult:
        coverage = RuntimeIntervalCoverageService.evaluate(
            windows,
            duration_seconds=duration_seconds,
        )
        return ExtremeInvisibilityRuntimeResult(
            duration_seconds=coverage.duration_seconds,
            longest_contiguous_seconds=coverage.longest_contiguous_seconds,
            covered_seconds=coverage.covered_seconds,
            uptime_ratio=coverage.uptime_ratio,
            window_count=len(coverage.merged_intervals),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeInvisibilityRuntimeResult",
    "ExtremeInvisibilityRuntimeService",
]
