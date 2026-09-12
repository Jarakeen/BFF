from __future__ import annotations

import pytest

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
from services.extreme_max_resource_named_gear_candidate_search_service import (
    ExtremeMaxResourceNamedGearCandidateSearchService,
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


def _breakpoint(set_id: int) -> ExtremeGearSetBonusBreakpoints:
    return ExtremeGearSetBonusBreakpoints(
        set_id=set_id,
        name=f"Set {set_id}",
        max_equip_count=5,
        bonus_counts=(2,),
    )


def _evidence(
    *,
    objective: str,
    stat: StatId,
    set_id: int,
    delta: float,
    condition: str | None = None,
) -> ExtremeGearSetObjectiveBreakpointEvidence:
    effect = Effect(
        operation=EffectOperation.ADD,
        value=float(delta),
        source=f"Set {set_id}",
        stat=stat,
        condition=condition,
    )
    candidate = ExtremeGearSetObjectiveCandidate(
        set_id=set_id,
        set_name=f"Set {set_id}",
        category="Trial",
        equipped_piece_count=2,
        objective_key=objective,
        reviewed_delta=(float(delta) if condition is None else 0.0),
        source_effects=(effect,),
        unresolved=(() if condition is None else ("relevant set effect requires condition",)),
    )
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=f"Set {set_id}",
        piece_count=2,
        objective_key=objective,
        status=ExtremeGearSetObjectiveRelevance.RELEVANT,
        reviewed_delta=float(candidate.reviewed_delta),
        candidate=candidate,
    )


def _service(
    objective: str,
    stat: StatId,
    *,
    two_specials: bool = False,
) -> ExtremeMaxResourceNamedGearCandidateSearchService:
    ids = (10, 20, 30, 40) if two_specials else (10, 20, 30)
    breakpoints = ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(_breakpoint(set_id) for set_id in ids)
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=tuple(_eligibility(set_id) for set_id in ids)
    )
    evidence = [
        _evidence(objective=objective, stat=stat, set_id=10, delta=1000.0),
        _evidence(objective=objective, stat=stat, set_id=20, delta=900.0),
        _evidence(
            objective=objective,
            stat=stat,
            set_id=30,
            delta=500.0,
            condition="drink_buff_active",
        ),
    ]
    if two_specials:
        evidence.append(
            _evidence(
                objective=objective,
                stat=stat,
                set_id=40,
                delta=700.0,
                condition="transformed",
            )
        )
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key=objective,
        evidence=tuple(evidence),
    )
    ordinary = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    return ExtremeMaxResourceNamedGearCandidateSearchService(
        ordinary_service=ordinary,
        eligibility=eligibility,
    )


@pytest.mark.parametrize(
    ("objective", "stat"),
    (("max_magicka", StatId.MAX_MAGICKA), ("max_stamina", StatId.MAX_STAMINA)),
)
def test_special_family_is_composed_beside_ordinary_winner(
    objective: str,
    stat: StatId,
) -> None:
    service = _service(objective, stat)
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    catalog = ExtremeGearSetTopologyCatalog(sets=(), topologies=(topology,))

    result = service.search(catalog)

    assert result.objective_key == objective
    assert result.candidate_reduction_proven is True
    assert {row.set_ids for row in result.ordinary.winning_realizations} == {(10, 20)}
    special = next(row for row in result.special_subsets if row.special_pairs == ((30, "Set 30", 2),))
    assert special.best_ordinary_flat_delta == 1000.0
    assert {row.set_ids for row in special.realizations} == {(10, 30)}
    assert {row.set_ids for row in result.candidate_realizations} == {(10, 20), (10, 30)}


@pytest.mark.parametrize(
    ("objective", "stat"),
    (("max_magicka", StatId.MAX_MAGICKA), ("max_stamina", StatId.MAX_STAMINA)),
)
def test_combined_special_subset_is_preserved(
    objective: str,
    stat: StatId,
) -> None:
    service = _service(objective, stat, two_specials=True)
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    catalog = ExtremeGearSetTopologyCatalog(sets=(), topologies=(topology,))

    result = service.search(catalog)
    by_special_ids = {
        tuple(pair[0] for pair in row.special_pairs): row
        for row in result.special_subsets
        if row.winner_found
    }

    assert set(by_special_ids) == {(30,), (40,), (30, 40)}
    assert {row.set_ids for row in by_special_ids[(30, 40)].realizations} == {(30, 40)}


@pytest.mark.parametrize(
    ("objective", "stat"),
    (("max_magicka", StatId.MAX_MAGICKA), ("max_stamina", StatId.MAX_STAMINA)),
)
def test_structurally_equivalent_single_specials_reuse_one_exact_filler_search(
    monkeypatch,
    objective: str,
    stat: StatId,
) -> None:
    service = _service(objective, stat, two_specials=True)
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    catalog = ExtremeGearSetTopologyCatalog(sets=(), topologies=(topology,))

    original = service._search_max_resource_subset
    calls = 0

    def wrapped(**kwargs):
        nonlocal calls
        calls += 1
        return original(**kwargs)

    monkeypatch.setattr(service, "_search_max_resource_subset", wrapped)
    result = service.search(catalog)

    by_special_ids = {
        tuple(pair[0] for pair in row.special_pairs): row
        for row in result.special_subsets
        if row.winner_found
    }
    assert calls == 2
    assert set(by_special_ids) == {(30,), (40,), (30, 40)}
    assert {row.set_ids for row in by_special_ids[(30,)].realizations} == {(10, 30)}
    assert {row.set_ids for row in by_special_ids[(40,)].realizations} == {(10, 40)}
    assert by_special_ids[(30,)].best_ordinary_flat_delta == by_special_ids[(40,)].best_ordinary_flat_delta
