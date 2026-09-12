from __future__ import annotations

from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from services.extreme_gear_search_state_rule_service import ExtremeGearSearchStateRule
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
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchService,
    _Candidate,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
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


def _eligibility(set_id: int, *, rings_only: bool = False) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Set {set_id}",
        category="Trial",
        max_equip_count=5,
        armor_slots=() if rings_only else _BODY,
        jewelry_slots=("Ring",) if rings_only else ("Necklace", "Ring"),
        weapon_types=() if rings_only else _WEAPONS,
    )


def _breakpoint(set_id: int, count: int) -> ExtremeGearSetBonusBreakpoints:
    return ExtremeGearSetBonusBreakpoints(
        set_id=set_id,
        name=f"Set {set_id}",
        max_equip_count=5,
        bonus_counts=(count,),
    )


def _evidence(
    set_id: int,
    count: int,
    delta: float,
    *,
    search_state_rule: ExtremeGearSearchStateRule | None = None,
    unresolved: tuple[str, ...] = (),
) -> ExtremeGearSetObjectiveBreakpointEvidence:
    effect = Effect(
        operation=EffectOperation.ADD,
        value=float(delta),
        source=f"Set {set_id} ({count})",
        stat=StatId.MAX_HEALTH,
    )
    candidate = ExtremeGearSetObjectiveCandidate(
        set_id=set_id,
        set_name=f"Set {set_id}",
        category="Trial",
        equipped_piece_count=count,
        objective_key="max_health",
        reviewed_delta=float(delta),
        source_effects=(effect,),
        unresolved=unresolved,
    )
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=f"Set {set_id}",
        piece_count=count,
        objective_key="max_health",
        status=ExtremeGearSetObjectiveRelevance.RELEVANT,
        reviewed_delta=float(delta),
        candidate=candidate,
        search_state_rule=search_state_rule,
    )


def _service(
    rows: tuple[tuple[int, int, float], ...],
    *,
    rings_only: frozenset[int] = frozenset(),
    extra_evidence: tuple[ExtremeGearSetObjectiveBreakpointEvidence, ...] = (),
):
    breakpoints = ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(_breakpoint(set_id, count) for set_id, count, _delta in rows)
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=tuple(
            _eligibility(set_id, rings_only=set_id in rings_only)
            for set_id, _count, _delta in rows
        )
    )
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_health",
        evidence=tuple(
            (*(_evidence(set_id, count, delta) for set_id, count, delta in rows), *extra_evidence)
        ),
    )
    return (
        ExtremeMaxResourceOrdinaryNamedGearSearchService(
            breakpoints=breakpoints,
            eligibility=eligibility,
            relevance=relevance,
        ),
        breakpoints,
        eligibility,
        relevance,
    )


def test_distinct_id_remaining_bound_respects_used_ids_within_count_class() -> None:
    candidates = {
        2: (
            _Candidate(10, "Set 10", 2, 1000.0, _eligibility(10), ()),
            _Candidate(20, "Set 20", 2, 900.0, _eligibility(20), ()),
            _Candidate(30, "Set 30", 2, 800.0, _eligibility(30), ()),
        )
    }

    fresh = ExtremeMaxResourceOrdinaryNamedGearSearchService._distinct_id_remaining_bound(
        counts=(2, 2),
        position=0,
        candidates_by_count=candidates,
        used_ids=set(),
    )
    after_10 = ExtremeMaxResourceOrdinaryNamedGearSearchService._distinct_id_remaining_bound(
        counts=(2, 2),
        position=0,
        candidates_by_count=candidates,
        used_ids={10},
    )

    assert fresh == 1900.0
    assert after_10 == 1700.0


def test_distinct_id_remaining_bound_stays_optimistic_across_count_classes() -> None:
    candidates = {
        2: (
            _Candidate(10, "Set 10", 2, 1000.0, _eligibility(10), ()),
            _Candidate(20, "Set 20", 2, 900.0, _eligibility(20), ()),
        ),
        3: (
            _Candidate(10, "Set 10", 3, 700.0, _eligibility(10), ()),
            _Candidate(30, "Set 30", 3, 600.0, _eligibility(30), ()),
        ),
    }

    bound = ExtremeMaxResourceOrdinaryNamedGearSearchService._distinct_id_remaining_bound(
        counts=(2, 2, 3),
        position=0,
        candidates_by_count=candidates,
        used_ids=set(),
    )

    assert bound == 2600.0


def test_branch_bound_winner_matches_exhaustive_small_catalog() -> None:
    rows = (
        (10, 2, 1000.0),
        (20, 2, 900.0),
        (30, 2, 800.0),
        (40, 2, 700.0),
    )
    service, breakpoints, eligibility, relevance = _service(rows)
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    catalog = ExtremeGearSetTopologyCatalog(sets=(), topologies=(topology,))

    result = service.search(catalog)
    winner = result.topologies[0]

    exhaustive = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
    ).realize_topology(topology)
    delta_by_id = {row.set_id: row.reviewed_delta for row in relevance.evidence}
    exhaustive_scores = {
        realization.set_ids: sum(delta_by_id[set_id] for set_id in realization.set_ids)
        for realization in exhaustive.realizations
    }
    exhaustive_best = max(exhaustive_scores.values())
    exhaustive_winners = {
        set_ids for set_ids, score in exhaustive_scores.items() if score == exhaustive_best
    }

    assert result.ordinary_denominator_proven is True
    assert result.full_named_gear_denominator_proven is True
    assert winner.best_exact_flat_delta == exhaustive_best == 1900.0
    assert {row.set_ids for row in winner.realizations} == exhaustive_winners == {(10, 20)}


def test_semantically_identical_tied_leaves_keep_one_representative() -> None:
    rows = ((10, 2, 1000.0), (20, 2, 1000.0), (30, 2, 1000.0))
    service, breakpoints, eligibility, _relevance = _service(rows)
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    signature = (("same-objective-effect",),)
    candidates = {
        2: tuple(
            _Candidate(
                set_id,
                f"Set {set_id}",
                2,
                1000.0,
                _eligibility(set_id),
                signature,
            )
            for set_id in (10, 20, 30)
        )
    }
    frontier = ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(_breakpoint(set_id, 2) for set_id in (10, 20, 30))
    )

    winner = service._search_topology(
        topology,
        candidates,
        frontier,
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    )

    assert winner.best_exact_flat_delta == 2000.0
    assert winner.stats.leaves == 3
    assert winner.stats.semantic_leaf_classes == 1
    assert winner.stats.semantic_duplicate_leaves == 2
    assert winner.stats.witness_checks == 1
    assert len(winner.realizations) == 1


def test_numerically_tied_different_effect_signatures_remain_distinct() -> None:
    rows = ((10, 2, 1000.0), (20, 2, 1000.0), (30, 2, 1000.0))
    service, _breakpoints, _eligibility_catalog, _relevance = _service(rows)
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    candidates = {
        2: (
            _Candidate(10, "Set 10", 2, 1000.0, _eligibility(10), (("A",),)),
            _Candidate(20, "Set 20", 2, 1000.0, _eligibility(20), (("B",),)),
            _Candidate(30, "Set 30", 2, 1000.0, _eligibility(30), (("A",),)),
        )
    }
    frontier = ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(_breakpoint(set_id, 2) for set_id in (10, 20, 30))
    )

    winner = service._search_topology(
        topology,
        candidates,
        frontier,
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    )

    assert winner.best_exact_flat_delta == 2000.0
    assert winner.stats.semantic_leaf_classes == 3
    assert winner.stats.semantic_duplicate_leaves == 0
    assert winner.stats.witness_checks == 3
    assert len(winner.realizations) == 3


def test_partial_physical_pruning_rejects_impossible_prefix_before_leaf() -> None:
    rows = (
        (10, 3, 1500.0),
        (20, 3, 1400.0),
        (30, 2, 500.0),
    )
    service, _breakpoints, _eligibility_catalog, _relevance = _service(
        rows,
        rings_only=frozenset({10}),
    )
    topology = ExtremeGearSetCountTopology(counts=(3, 2), unused_units=7)
    catalog = ExtremeGearSetTopologyCatalog(sets=(), topologies=(topology,))

    result = service.search(catalog)
    winner = result.topologies[0]

    assert winner.best_exact_flat_delta == 1900.0
    assert {row.set_ids for row in winner.realizations} == {(20, 30)}
    assert winner.stats.physical_pruned > 0
    assert winner.stats.rejected_leaves == 0


def test_special_search_state_candidate_remains_explicit_and_keeps_full_denominator_open() -> None:
    rows = (
        (10, 2, 1000.0),
        (20, 2, 900.0),
        (161, 5, 1206.0),
    )
    special = _evidence(
        161,
        5,
        1206.0,
        search_state_rule=ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS,
        unresolved=("reviewed search-state mutation",),
    )
    ordinary_rows = rows[:2]
    breakpoints = ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(_breakpoint(set_id, count) for set_id, count, _delta in rows)
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=tuple(_eligibility(set_id) for set_id, _count, _delta in rows)
    )
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_health",
        evidence=tuple(
            [
                *(_evidence(set_id, count, delta) for set_id, count, delta in ordinary_rows),
                special,
            ]
        ),
    )
    service = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    topology = ExtremeGearSetCountTopology(counts=(5, 2), unused_units=5)
    catalog = ExtremeGearSetTopologyCatalog(sets=(), topologies=(topology,))

    result = service.search(catalog)

    assert result.ordinary_denominator_proven is True
    assert result.full_named_gear_denominator_proven is False
    assert result.special_or_nonflat_pairs == ((161, "Set 161", 5),)
