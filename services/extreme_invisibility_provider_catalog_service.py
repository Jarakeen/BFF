from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.runtime_interval_coverage_service import RuntimeInterval


class ExtremeInvisibilityProviderStatus(str, Enum):
    VERIFIED = "verified"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ExtremeInvisibilityProvider:
    entity_id: str
    name: str
    status: ExtremeInvisibilityProviderStatus
    duration_seconds: float | None = None
    windows: tuple[RuntimeInterval, ...] = ()
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def has_verified_duration(self) -> bool:
        return (
            self.status is ExtremeInvisibilityProviderStatus.VERIFIED
            and self.duration_seconds is not None
            and self.duration_seconds >= 0.0
            and not self.unresolved
        )

    @property
    def has_verified_windows(self) -> bool:
        return (
            self.status is ExtremeInvisibilityProviderStatus.VERIFIED
            and bool(self.windows)
            and not self.unresolved
        )


@dataclass(frozen=True)
class ExtremeInvisibilityProviderCatalog:
    providers: tuple[ExtremeInvisibilityProvider, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def verified(self) -> tuple[ExtremeInvisibilityProvider, ...]:
        return tuple(
            provider
            for provider in self.providers
            if provider.status is ExtremeInvisibilityProviderStatus.VERIFIED
        )

    @property
    def unresolved_providers(self) -> tuple[ExtremeInvisibilityProvider, ...]:
        return tuple(
            provider
            for provider in self.providers
            if provider.status is ExtremeInvisibilityProviderStatus.UNRESOLVED
        )

    @property
    def denominator_proven(self) -> bool:
        return bool(self.providers) and not self.unresolved and not self.unresolved_providers


class ExtremeInvisibilityProviderCatalogService:
    """Own the proof contract for legal player invisibility providers.

    Provider discovery is deliberately separate from runtime interval math.
    Callers may add a provider only when canonical ESO evidence proves both the
    provider identity and the relevant duration/window semantics. Tooltip keyword
    matching is not accepted as mechanics evidence.
    """

    @staticmethod
    def build(
        providers: tuple[ExtremeInvisibilityProvider, ...],
        *,
        unresolved: tuple[str, ...] = (),
    ) -> ExtremeInvisibilityProviderCatalog:
        ordered = tuple(
            sorted(
                providers,
                key=lambda provider: (
                    provider.name.casefold(),
                    provider.name,
                    provider.entity_id,
                ),
            )
        )
        return ExtremeInvisibilityProviderCatalog(
            providers=ordered,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeInvisibilityProvider",
    "ExtremeInvisibilityProviderCatalog",
    "ExtremeInvisibilityProviderCatalogService",
    "ExtremeInvisibilityProviderStatus",
]
