from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_finite_family_dominance_search_service import (
    ExtremeSustainedDPSFiniteFamilyDominanceSearchService,
)


def test_search_service_exposes_three_explicit_family_entry_points() -> None:
    assert callable(ExtremeSustainedDPSFiniteFamilyDominanceSearchService.champion_points)
    assert callable(ExtremeSustainedDPSFiniteFamilyDominanceSearchService.passive_ranks)
    assert callable(ExtremeSustainedDPSFiniteFamilyDominanceSearchService.dual_bar_gear)


def test_family_methods_keep_distinct_names_for_catalog_and_callers() -> None:
    names = {
        ExtremeSustainedDPSFiniteFamilyDominanceSearchService.champion_points.__name__,
        ExtremeSustainedDPSFiniteFamilyDominanceSearchService.passive_ranks.__name__,
        ExtremeSustainedDPSFiniteFamilyDominanceSearchService.dual_bar_gear.__name__,
    }
    assert names == {"champion_points", "passive_ranks", "dual_bar_gear"}
