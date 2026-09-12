from __future__ import annotations

import pytest

from minmax.stat_ids import StatId
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_max_resource_semantic_special_subset_search_service import (
    ExtremeMaxResourceSemanticSpecialSubsetSearchService,
)
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialNamedGearBranchService,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)
from services.tests.test_extreme_max_resource_named_gear_candidate_search_service import (
    _service,
)


@pytest.mark.parametrize(
    ("objective", "stat"),
    (("max_magicka", StatId.MAX_MAGICKA), ("max_stamina", StatId.MAX_STAMINA)),
)
def test_semantic_special_subset_matches_legacy_exact_winner(
    objective: str,
    stat: StatId,
) -> None:
    service = _service(objective, stat)
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    catalog = ExtremeGearSetTopologyCatalog(sets=(), topologies=(topology,))

    ordinary = service.ordinary_service.search(catalog)
    classified = ExtremeMaxResourceSpecialNamedGearBranchService(
        service.ordinary_service.relevance
    ).build(ordinary.special_or_nonflat_pairs)
    assert classified.denominator_classified is True
    assert len(classified.branches) == 1

    reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=service.ordinary_service.breakpoints,
        eligibility=service.eligibility,
        relevance=service.ordinary_service.relevance,
    )
    reduced, _equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(
        catalog
    )
    frontier, _frontier_pruned = service.ordinary_service._frontier(
        reduced,
        representative_limit,
    )
    ordinary_candidates, _special = service.ordinary_service._candidates(frontier)
    feasibility = ExtremePartialNamedGearPhysicalFeasibilityService()
    subset = (classified.branches[0],)

    legacy = service._search_subset(
        topology=topology,
        subset=subset,
        ordinary_candidates_by_count=ordinary_candidates,
        frontier=frontier,
        feasibility=feasibility,
    )
    semantic = ExtremeMaxResourceSemanticSpecialSubsetSearchService.search(
        service,
        topology=topology,
        subset=subset,
        ordinary_candidates_by_count=ordinary_candidates,
        frontier=frontier,
        feasibility=feasibility,
    )

    assert semantic.best_ordinary_flat_delta == legacy.best_ordinary_flat_delta
    assert {row.set_ids for row in semantic.realizations} == {
        row.set_ids for row in legacy.realizations
    }
    assert semantic.stats.leaves <= legacy.stats.leaves


def test_production_max_resource_search_uses_semantic_special_subset_path(monkeypatch) -> None:
    service = _service("max_magicka", StatId.MAX_MAGICKA)
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    catalog = ExtremeGearSetTopologyCatalog(sets=(), topologies=(topology,))

    calls = 0
    original = ExtremeMaxResourceSemanticSpecialSubsetSearchService.search

    def wrapped(owner, **kwargs):
        nonlocal calls
        calls += 1
        return original(owner, **kwargs)

    monkeypatch.setattr(
        ExtremeMaxResourceSemanticSpecialSubsetSearchService,
        "search",
        staticmethod(wrapped),
    )

    result = service.search(catalog)

    assert result.candidate_reduction_proven is True
    assert calls > 0
