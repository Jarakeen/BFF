from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.extreme_invisibility_gear_provider_service import (
    ExtremeInvisibilityGearProviderService,
)
from services.extreme_invisibility_provider_catalog_service import (
    ExtremeInvisibilityProvider,
    ExtremeInvisibilityProviderCatalog,
)


@dataclass(frozen=True)
class ExtremeInvisibilityDurationRecordResult:
    provider: ExtremeInvisibilityProvider | None
    duration_seconds: float | None
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return self.duration_seconds is not None and not self.unresolved


class ExtremeInvisibilityDurationRecordService:
    """Return the longest reviewed contiguous invisibility provider duration.

    This is a proof-safe lower bound until the provider corpus denominator is
    closed. It does not need a runtime comparison horizon because the record asks
    only for the longest contiguous legal invisibility window.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        gear_providers: ExtremeInvisibilityGearProviderService | None = None,
    ) -> None:
        self.gear_providers = gear_providers or (
            ExtremeInvisibilityGearProviderService(database_path)
            if database_path is not None
            else None
        )

    def evaluate(self) -> ExtremeInvisibilityDurationRecordResult:
        if self.gear_providers is None:
            raise ValueError("Extreme invisibility duration record requires a canonical database path")

        catalog: ExtremeInvisibilityProviderCatalog = self.gear_providers.catalog()
        candidates = tuple(
            provider
            for provider in catalog.verified
            if provider.has_verified_duration
        )
        best = max(
            candidates,
            key=lambda provider: (
                float(provider.duration_seconds or 0.0),
                provider.name.casefold(),
                provider.entity_id,
            ),
            default=None,
        )
        unresolved = list(catalog.unresolved)
        unresolved.extend(
            problem
            for provider in catalog.unresolved_providers
            for problem in provider.unresolved
        )
        if best is None:
            unresolved.append("No reviewed legal invisibility provider duration is currently available")

        evidence: list[str] = []
        if best is not None:
            evidence.extend(best.evidence)
            evidence.append(
                f"Reviewed longest contiguous invisibility lower bound: {float(best.duration_seconds):g}s"
            )

        return ExtremeInvisibilityDurationRecordResult(
            provider=best,
            duration_seconds=(None if best is None else float(best.duration_seconds)),
            evidence=tuple(dict.fromkeys(item for item in evidence if item)),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeInvisibilityDurationRecordResult",
    "ExtremeInvisibilityDurationRecordService",
]
