from __future__ import annotations

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_max_resource_joint_feasibility_search_service import (
    ExtremeMaxResourceJointFeasibilitySearchService,
)
from services.extreme_max_resource_ordinary_named_gear_search_service import _Candidate
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)


_BODY = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
_WEAPONS = (
    "Axe",
    "Mace",
    "Sword",
    "Dagger",
    "Shield",
    "Two-Handed Sword",
    "Two-Handed Axe",
    "Two-Handed Mace",
    "Bow",
    "Restoration Staff",
    "Inferno Staff",
    "Ice Staff",
    "Lightning Staff",
)


def _broad(set_id: int) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Broad {set_id}",
        category="Trial",
        max_equip_count=5,
        armor_slots=_BODY,
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=_WEAPONS,
    )


def _ring(set_id: int) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Ring {set_id}",
        category="Trial",
        max_equip_count=1,
        jewelry_slots=("Ring",),
    )


def _candidate(row: ExtremeNamedGearSetSlotEligibility, count: int) -> _Candidate:
    return _Candidate(
        set_id=row.set_id,
        name=row.name,
        piece_count=count,
        exact_delta=1000.0,
        eligibility=row,
        objective_effect_signature=(),
    )


def test_joint_precheck_rejects_identity_physical_conflict_that_independent_checks_allow() -> None:
    # Set 10 is the only broad 1-piece identity, but it is also the only 2-piece
    # identity. Identity-only matching can reserve 10 for 2pc and use 20/30/40 at
    # 1pc. Shape-only matching can clone the broad 1pc shape and use two ring-only
    # shapes. No concrete assignment can do both: reserving 10 for 2pc leaves three
    # ring-only 1pc identities competing for two ring slots.
    broad = _broad(10)
    ring_20 = _ring(20)
    ring_30 = _ring(30)
    ring_40 = _ring(40)
    candidates = {
        2: (_candidate(broad, 2),),
        1: (
            _candidate(broad, 1),
            _candidate(ring_20, 1),
            _candidate(ring_30, 1),
            _candidate(ring_40, 1),
        ),
    }
    topology = ExtremeGearSetCountTopology(counts=(2, 1, 1, 1), unused_units=7)
    feasibility = ExtremePartialNamedGearPhysicalFeasibilityService()

    assert ExtremeMaxResourceJointFeasibilitySearchService._identity_legality_possible(
        counts=topology.counts,
        candidates_by_count=candidates,
    ) is True
    assert ExtremeMaxResourceJointFeasibilitySearchService._physical_shape_legality_possible(
        topology=topology,
        counts=topology.counts,
        candidates_by_count=candidates,
        feasibility=feasibility,
    ) is True
    assert ExtremeMaxResourceJointFeasibilitySearchService._joint_legality_possible(
        topology=topology,
        candidates_by_count=candidates,
        feasibility=feasibility,
    ) is False


def test_joint_precheck_allows_concrete_feasible_assignment() -> None:
    broad_10 = _broad(10)
    broad_11 = _broad(11)
    ring_20 = _ring(20)
    ring_30 = _ring(30)
    candidates = {
        2: (_candidate(broad_10, 2),),
        1: (
            _candidate(broad_11, 1),
            _candidate(ring_20, 1),
            _candidate(ring_30, 1),
        ),
    }
    topology = ExtremeGearSetCountTopology(counts=(2, 1, 1, 1), unused_units=7)

    assert ExtremeMaxResourceJointFeasibilitySearchService._joint_legality_possible(
        topology=topology,
        candidates_by_count=candidates,
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    ) is True


def test_joint_search_service_keeps_shared_max_resource_contract() -> None:
    service = ExtremeMaxResourceJointFeasibilitySearchService(
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(sets=()),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(sets=()),
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key="max_magicka",
            evidence=(),
        ),
    )

    assert "max_health" in service.SUPPORTED_OBJECTIVES
    assert "max_magicka" in service.SUPPORTED_OBJECTIVES
    assert "max_stamina" in service.SUPPORTED_OBJECTIVES
