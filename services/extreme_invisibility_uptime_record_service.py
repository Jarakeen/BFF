from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.extreme_invisibility_gear_provider_service import (
    ExtremeInvisibilityGearProviderService,
    ExtremeReviewedInvisibilityGearProvider,
)
from services.extreme_invisibility_runtime_service import (
    ExtremeInvisibilityRuntimeResult,
    ExtremeInvisibilityRuntimeService,
)
from services.runtime_interval_coverage_service import RuntimeInterval


@dataclass(frozen=True)
class ExtremeInvisibilityUptimeRecordResult:
    provider: ExtremeReviewedInvisibilityGearProvider | None
    duration_seconds: float
    covered_seconds: float
    uptime_ratio: float
    window_count: int
    mechanic_complete: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeInvisibilityUptimeRecordService:
    """Project a reviewed invisibility-uptime lower bound over an explicit horizon.

    Provider discovery remains owned by ``ExtremeInvisibilityGearProviderService``.
    This service only converts reviewed duration/cooldown semantics into explicit
    legal windows and delegates neutral temporal coverage to the shared runtime
    interval engine.  The current provider corpus is intentionally incomplete, so
    the result is a constructive lower bound rather than a global-maximum proof.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        gear_providers: ExtremeInvisibilityGearProviderService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.gear_providers = gear_providers or ExtremeInvisibilityGearProviderService(
            self.database_path
        )

    @staticmethod
    def _windows_for(
        provider: ExtremeReviewedInvisibilityGearProvider,
        *,
        duration_seconds: float,
    ) -> tuple[RuntimeInterval, ...]:
        horizon = float(duration_seconds)
        if horizon <= 0.0:
            raise ValueError("invisibility uptime duration must be greater than zero")
        if provider.duration_seconds <= 0.0:
            raise ValueError("reviewed invisibility provider duration must be greater than zero")
        if provider.cooldown_seconds <= 0.0:
            raise ValueError("reviewed invisibility provider cooldown must be greater than zero")

        windows: list[RuntimeInterval] = []
        start = 0.0
        while start < horizon:
            windows.append(
                RuntimeInterval(
                    start_seconds=start,
                    end_seconds=start + provider.duration_seconds,
                    source=provider.name,
                )
            )
            start += provider.cooldown_seconds
        return tuple(windows)

    def evaluate(self, *, duration_seconds: float) -> ExtremeInvisibilityUptimeRecordResult:
        reviewed = self.gear_providers.reviewed_providers()
        if not reviewed:
            return ExtremeInvisibilityUptimeRecordResult(
                provider=None,
                duration_seconds=float(duration_seconds),
                covered_seconds=0.0,
                uptime_ratio=0.0,
                window_count=0,
                mechanic_complete=False,
                evidence=(),
                unresolved=(
                    "No reviewed legal invisibility provider with recurrence semantics was discovered",
                ),
            )

        best_provider: ExtremeReviewedInvisibilityGearProvider | None = None
        best_runtime: ExtremeInvisibilityRuntimeResult | None = None
        for provider in reviewed:
            windows = self._windows_for(provider, duration_seconds=duration_seconds)
            runtime = ExtremeInvisibilityRuntimeService.evaluate(
                windows,
                duration_seconds=float(duration_seconds),
            )
            if best_runtime is None or runtime.uptime_ratio > best_runtime.uptime_ratio:
                best_provider = provider
                best_runtime = runtime

        assert best_provider is not None and best_runtime is not None
        unresolved = (
            "Invisibility provider corpus is not yet exhaustive across skills, potions, and other legal sources",
        )
        evidence = (
            *best_provider.evidence,
            f"Constructive recurrence schedule starts at 0s and repeats every {best_provider.cooldown_seconds:g}s",
            f"Reviewed horizon: {float(duration_seconds):g}s",
        )
        return ExtremeInvisibilityUptimeRecordResult(
            provider=best_provider,
            duration_seconds=best_runtime.duration_seconds,
            covered_seconds=best_runtime.covered_seconds,
            uptime_ratio=best_runtime.uptime_ratio,
            window_count=best_runtime.window_count,
            mechanic_complete=False,
            evidence=evidence,
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeInvisibilityUptimeRecordResult",
    "ExtremeInvisibilityUptimeRecordService",
]
