from __future__ import annotations

from services.extreme_invisibility_duration_record_service import (
    ExtremeInvisibilityDurationRecordService,
)
from services.extreme_invisibility_provider_catalog_service import (
    ExtremeInvisibilityProvider,
    ExtremeInvisibilityProviderCatalogService,
    ExtremeInvisibilityProviderStatus,
)


class _GearProviders:
    def __init__(self, providers=(), unresolved=()):
        self._catalog = ExtremeInvisibilityProviderCatalogService.build(
            tuple(providers),
            unresolved=tuple(unresolved),
        )

    def catalog(self):
        return self._catalog


def test_duration_record_selects_longest_verified_provider() -> None:
    service = ExtremeInvisibilityDurationRecordService(
        gear_providers=_GearProviders(
            (
                ExtremeInvisibilityProvider(
                    entity_id="short",
                    name="Short",
                    status=ExtremeInvisibilityProviderStatus.VERIFIED,
                    duration_seconds=3.0,
                    evidence=("short evidence",),
                ),
                ExtremeInvisibilityProvider(
                    entity_id="long",
                    name="Long",
                    status=ExtremeInvisibilityProviderStatus.VERIFIED,
                    duration_seconds=10.0,
                    evidence=("long evidence",),
                ),
            ),
            unresolved=("provider denominator open",),
        )
    )

    result = service.evaluate()

    assert result.provider is not None
    assert result.provider.entity_id == "long"
    assert result.duration_seconds == 10.0
    assert "long evidence" in result.evidence
    assert "Reviewed longest contiguous invisibility lower bound: 10s" in result.evidence
    assert result.unresolved == ("provider denominator open",)
    assert result.mechanic_complete is False


def test_duration_record_reports_missing_provider_explicitly() -> None:
    service = ExtremeInvisibilityDurationRecordService(
        gear_providers=_GearProviders(unresolved=("provider denominator open",))
    )

    result = service.evaluate()

    assert result.provider is None
    assert result.duration_seconds is None
    assert "No reviewed legal invisibility provider duration is currently available" in result.unresolved
