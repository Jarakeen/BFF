from __future__ import annotations

from types import SimpleNamespace

from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)
from tools.audit_extreme_resource_record_closure import (
    _objective_candidate_ids_by_count,
    _topology_assignment_upper_bound,
)


def _eligibility(set_id: int, *, max_count: int = 5, physical: bool = True):
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Set {set_id}",
        category="Trial",
        max_equip_count=max_count,
        armor_slots=("Chest",) if physical else (),
    )


def _evidence(set_id: int, count: int, status: ExtremeGearSetObjectiveRelevance):
    return SimpleNamespace(
        set_id=set_id,
        piece_count=count,
        status=status,
    )


def test_candidate_count_diagnostic_matches_objective_and_physical_gates():
    relevance = SimpleNamespace(
        evidence=(
            _evidence(10, 5, ExtremeGearSetObjectiveRelevance.RELEVANT),
            _evidence(20, 5, ExtremeGearSetObjectiveRelevance.UNRESOLVED),
            _evidence(30, 5, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
            _evidence(40, 2, ExtremeGearSetObjectiveRelevance.RELEVANT),
            _evidence(50, 2, ExtremeGearSetObjectiveRelevance.RELEVANT),
            _evidence(60, 5, ExtremeGearSetObjectiveRelevance.RELEVANT),
        )
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=(
            _eligibility(10),
            _eligibility(20),
            _eligibility(30),
            _eligibility(40, max_count=2),
            _eligibility(50, max_count=2, physical=False),
            _eligibility(60, max_count=2),
        )
    )

    result = _objective_candidate_ids_by_count(relevance, eligibility)

    assert result == {
        2: (40,),
        5: (10, 20),
    }


def test_topology_upper_bound_uses_combinations_for_equal_count_parts():
    candidates = {
        5: (10, 20, 30, 40),
        2: (50, 60, 70),
    }
    topology = ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0)

    # choose two of four 5-piece sets, then one of three 2-piece sets
    assert _topology_assignment_upper_bound(topology, candidates) == 18


def test_topology_upper_bound_is_zero_when_bucket_cannot_fill_topology():
    candidates = {5: (10,), 2: (50, 60)}
    topology = ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0)

    assert _topology_assignment_upper_bound(topology, candidates) == 0
