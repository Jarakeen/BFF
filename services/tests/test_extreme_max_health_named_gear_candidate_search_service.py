from __future__ import annotations

from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveBreakpointEvidence,
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_max_health_named_gear_candidate_search_service import (
    ExtremeMaxHealthNamedGearCandidateSearchService,
)
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


_BODY = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
_WEAPONS = (
    "Axe", "Mace", "Sword", "Dagger", "Shield",
    "Two-Handed Sword", "Two-Handed Axe", "Two-Handed Mace", "Bow",
    "Restoration Staff", "Inferno Staff", "Ice Staff", "Lightning Staff",
)


def _eligibility(set_id: int) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Set {set_id}",
        category="Trial",
        max_equip_count=5,
        armor_slots=_BODY,
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=_WEAPONS,
    )


def _breakpoint(set_id: int, count: int = 2) -> ExtremeGearSetBonusBreakpoints:
    return ExtremeGearSetBonusBreakpoints(
        set_id=set_id,
        name=f"Set {set_id}",
        max_equip_count=5,
        bonus_counts=(count,),
    )


def _evidence(
    set_id: int,
    delta: float,
    *,
    condition: str | None = None,
) -> ExtremeGearSetObjectiveBreakpointEvidence:
    effect = Effect(
        operation=EffectOperation.ADD,
        value=float(delta),
        source=f"Set {set_id}",
        stat=StatId.MAX_HEALTH,
        condition=condition,
    )
    unresolved = () if condition is None else ("relevant set effect requires condition",)
    candidate = ExtremeGearSetObjectiveCandidate(
        set_id=set_id,
        set_name=f"Set {set_id}",
        category="Trial",
        equipped_piece_count=2,
        objective_key="max_health",
        reviewed_delta=(float(delta) if condition is None else 0.0),
        source_effects=(effect,),
        unresolved=unresolved,
    )
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=f"Set {set_id}",
        piece_count=2,
        objective_key="max_health",
        status=ExtremeGearSetObjectiveRelevance.RELEVANT,
        reviewed_delta=float(candidate.reviewed_delta),
        candidate=candidate,
    )


def _service(*, two_specials: bool = False) -> ExtremeMaxHealthNamedGearCandidateSearchService:
    ids = (10, 20, 30, 40) if two_specials else (10, 20, 30)
    breakpoints = ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(_breakpoint(set_id) for set_id in ids)
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=tuple(_eligibility(set_id) for set_id in ids)
    )
    evidence = [
        _evidence(10, 1000.0),
        _evidence(20, 900.0),
        _evidence(30, 500.0, condition="food_buff_active"),
    ]
    if two_specials:
        evidence.append(_evidence(40, 700.0, condition="transformed"))
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_health",
        evidence=tuple(evidence),
    )
    ordinary = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    return ExtremeMaxHealthNamedGearCandidateSearchService(
        ordinary_service=ordinary,
        eligibility=eligibility,
    )


def test_special_family_keeps_best_ordinary_filler_beside_ordinary_winner() -> None:
    service = _service()
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    catalog = ExtremeGearSetTopologyCatalog(sets=(), topologies=(topology,))

    result = service.search(catalog)

    assert result.candidate_reduction_proven is True
    assert {row.set_ids for row in result.ordinary.winning_realizations} == {(10, 20)}
    special = [row for row in result.special_subsets if row.special_pairs == ((30, "Set 30", 2),)]
    assert len(special) == 1
    assert special[0].best_ordinary_flat_delta == 1000.0
    assert {row.set_ids for row in special[0].realizations} == {(10, 30)}
    assert {row.set_ids for row in result.candidate_realizations} == {(10, 20), (10, 30)}


def test_every_legal_special_subset_gets_its_own_candidate_family() -> None:
    service = _service(two_specials=True)
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    catalog = ExtremeGearSetTopologyCatalog(sets=(), topologies=(topology,))

    result = service.search(catalog)
    by_special_ids = {
        tuple(pair[0] for pair in row.special_pairs): row
        for row in result.special_subsets
        if row.winner_found
    }

    assert set(by_special_ids) == {(30,), (40,), (30, 40)}
    assert {row.set_ids for row in by_special_ids[(30,)].realizations} == {(10, 30)}
    assert {row.set_ids for row in by_special_ids[(40,)].realizations} == {(10, 40)}
    assert by_special_ids[(30, 40)].best_ordinary_flat_delta == 0.0
    assert {row.set_ids for row in by_special_ids[(30, 40)].realizations} == {(30, 40)}
