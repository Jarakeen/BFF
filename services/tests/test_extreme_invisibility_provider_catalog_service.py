from services.extreme_invisibility_provider_catalog_service import (
    ExtremeInvisibilityProvider,
    ExtremeInvisibilityProviderCatalogService,
    ExtremeInvisibilityProviderStatus,
)
from services.runtime_interval_coverage_service import RuntimeInterval


def test_verified_provider_requires_reviewed_duration_or_windows_to_be_useful() -> None:
    provider = ExtremeInvisibilityProvider(
        entity_id="verified-cloak",
        name="Verified Cloak",
        status=ExtremeInvisibilityProviderStatus.VERIFIED,
        duration_seconds=3.0,
        windows=(RuntimeInterval(0.0, 3.0),),
        evidence=("reviewed provider identity",),
    )

    assert provider.has_verified_duration is True
    assert provider.has_verified_windows is True


def test_unresolved_provider_cannot_prove_catalog_denominator() -> None:
    catalog = ExtremeInvisibilityProviderCatalogService.build(
        (
            ExtremeInvisibilityProvider(
                entity_id="known-name-unknown-runtime",
                name="Known Name",
                status=ExtremeInvisibilityProviderStatus.UNRESOLVED,
                unresolved=("provider duration semantics are not source-reviewed",),
            ),
        )
    )

    assert catalog.verified == ()
    assert len(catalog.unresolved_providers) == 1
    assert catalog.denominator_proven is False


def test_catalog_deduplicates_global_unresolved_and_sorts_providers() -> None:
    catalog = ExtremeInvisibilityProviderCatalogService.build(
        (
            ExtremeInvisibilityProvider(
                entity_id="z",
                name="Zulu",
                status=ExtremeInvisibilityProviderStatus.VERIFIED,
                duration_seconds=2.0,
            ),
            ExtremeInvisibilityProvider(
                entity_id="a",
                name="Alpha",
                status=ExtremeInvisibilityProviderStatus.VERIFIED,
                duration_seconds=4.0,
            ),
        ),
        unresolved=("provider corpus denominator remains open", "provider corpus denominator remains open"),
    )

    assert tuple(provider.name for provider in catalog.providers) == ("Alpha", "Zulu")
    assert catalog.unresolved == ("provider corpus denominator remains open",)
    assert catalog.denominator_proven is False
