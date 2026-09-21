from __future__ import annotations

from dataclasses import dataclass

import pytest

from minmax.character_progression import AttributeAllocation
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverse
from services.extreme_sustained_dps_generated_candidate_service import (
    ExtremeSustainedDPSGeneratedCandidateService,
)


@dataclass(frozen=True)
class _Route:
    name: str


class _UniverseService:
    def __init__(self, universe):
        self.universe = universe

    def build(self):
        return self.universe


def _universe(*, proven: bool = True):
    return ExtremeGlobalSearchUniverse(
        races=("Argonian", "Khajiit"),
        class_routes=(_Route("A"), _Route("B"), _Route("C")),
        attribute_allocations=(
            AttributeAllocation(health=64, magicka=0, stamina=0),
            AttributeAllocation(health=0, magicka=64, stamina=0),
        ),
        active_bars=("front", "back"),
        structural_scope=("race", "route", "attributes", "bar"),
        deferred_dynamic_axes=("gear", "skills", "rotation"),
    ) if proven else ExtremeGlobalSearchUniverse(
        races=(),
        class_routes=(_Route("A"),),
        attribute_allocations=(AttributeAllocation(health=64, magicka=0, stamina=0),),
        active_bars=("front", "back"),
        structural_scope=("race", "route", "attributes", "bar"),
        deferred_dynamic_axes=("gear", "skills", "rotation"),
    )


def test_frontier_counts_structural_cross_product_without_claiming_dynamic_axes() -> None:
    service = ExtremeSustainedDPSGeneratedCandidateService(
        "unused.db",
        universe_service=_UniverseService(_universe()),
    )

    result = service.frontier()

    assert result.structural_candidate_count == 24
    assert result.structural_denominator_proven is True
    assert result.expanded_axes == (
        "race",
        "legal class route",
        "64-point attribute allocation",
        "active bar",
    )
    assert result.deferred_axes == ("gear", "skills", "rotation")
    assert result.generated_search_complete is False
    assert any("no gear, skills, CP" in row for row in result.evidence)


def test_candidate_at_uses_deterministic_mixed_radix_order() -> None:
    service = ExtremeSustainedDPSGeneratedCandidateService(
        "unused.db",
        universe_service=_UniverseService(_universe()),
    )

    first = service.candidate_at(0)
    second = service.candidate_at(1)
    third = service.candidate_at(2)
    last = service.candidate_at(23)

    assert (first.race, first.class_route.name, first.attributes.health, first.active_bar) == (
        "Argonian",
        "A",
        64,
        "front",
    )
    assert second.active_bar == "back"
    assert third.attributes.magicka == 64
    assert (last.race, last.class_route.name, last.attributes.magicka, last.active_bar) == (
        "Khajiit",
        "C",
        64,
        "back",
    )


def test_page_returns_requested_slice_without_materializing_whole_frontier() -> None:
    service = ExtremeSustainedDPSGeneratedCandidateService(
        "unused.db",
        universe_service=_UniverseService(_universe()),
    )

    rows = service.page(offset=5, limit=4)

    assert tuple(row.structural_index for row in rows) == (5, 6, 7, 8)
    assert service.page(offset=1000, limit=4) == ()
    assert service.page(offset=0, limit=0) == ()


def test_invalid_candidate_index_fails_closed() -> None:
    service = ExtremeSustainedDPSGeneratedCandidateService(
        "unused.db",
        universe_service=_UniverseService(_universe()),
    )

    with pytest.raises(IndexError):
        service.candidate_at(-1)
    with pytest.raises(IndexError):
        service.candidate_at(24)


def test_incomplete_structural_universe_blocks_denominator_proof() -> None:
    service = ExtremeSustainedDPSGeneratedCandidateService(
        "unused.db",
        universe_service=_UniverseService(_universe(proven=False)),
    )

    result = service.frontier()

    assert result.structural_candidate_count == 0
    assert result.structural_denominator_proven is False
    assert result.generated_search_complete is False
    assert result.unresolved
