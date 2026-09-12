from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalog
from services.extreme_max_resource_joint_feasibility_search_service import (
    ExtremeMaxResourceJointFeasibilitySearchService,
)
from services.extreme_max_resource_named_gear_candidate_realization_adapter_service import (
    ExtremeMaxResourceNamedGearCandidateRealizationAdapterService,
)
from services.extreme_max_resource_named_gear_candidate_search_service import (
    ExtremeMaxResourceNamedGearCandidateSearchService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityCatalog,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)


@pytest.mark.parametrize("objective", ("max_magicka", "max_stamina"))
def test_uncapped_resource_objective_routes_through_composed_special_frontier(
    monkeypatch,
    objective: str,
) -> None:
    sentinel_candidate_search = SimpleNamespace(objective_key=objective)
    sentinel_result = object()
    seen: dict[str, object] = {}

    def fake_candidate_search(self, topology_catalog):
        seen["candidate_service"] = self
        seen["ordinary_service"] = self.ordinary_service
        seen["topology_catalog"] = topology_catalog
        return sentinel_candidate_search

    def fake_build(*, search, topology_catalog, relevance):
        seen["search"] = search
        seen["adapter_topology"] = topology_catalog
        seen["relevance"] = relevance
        return sentinel_result

    monkeypatch.setattr(
        ExtremeMaxResourceNamedGearCandidateSearchService,
        "search",
        fake_candidate_search,
    )
    monkeypatch.setattr(
        ExtremeMaxResourceNamedGearCandidateRealizationAdapterService,
        "build",
        staticmethod(fake_build),
    )

    topology_catalog = ExtremeGearSetTopologyCatalog(sets=(), topologies=())
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key=objective,
        evidence=(),
    )
    service = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(sets=()),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(sets=()),
        relevance=relevance,
    )

    result = service.build(topology_catalog)

    assert result is sentinel_result
    assert seen["search"] is sentinel_candidate_search
    assert isinstance(seen["ordinary_service"], ExtremeMaxResourceJointFeasibilitySearchService)
    assert seen["topology_catalog"] is topology_catalog
    assert seen["adapter_topology"] is topology_catalog
    assert seen["relevance"] is relevance
