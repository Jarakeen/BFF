from __future__ import annotations

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchService,
    _Candidate,
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


def _eligibility(set_id: int, *, category: str = "Trial") -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Set {set_id}",
        category=category,
        max_equip_count=5,
        armor_slots=_BODY,
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=_WEAPONS,
    )


def _ring_only(set_id: int) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Ring Set {set_id}",
        category="Trial",
        max_equip_count=1,
        jewelry_slots=("Ring",),
    )


def _candidate(set_id: int, count: int, *, category: str = "Trial") -> _Candidate:
    return _Candidate(
        set_id=set_id,
        name=f"Set {set_id}",
        piece_count=count,
        exact_delta=1000.0,
        eligibility=_eligibility(set_id, category=category),
        objective_effect_signature=(),
    )


def _service(*rows: ExtremeNamedGearSetSlotEligibility) -> ExtremeMaxResourceOrdinaryNamedGearSearchService:
    return ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(sets=()),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(sets=tuple(rows)),
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key="max_health",
            evidence=(),
        ),
    )


def test_identity_precheck_rejects_two_required_mythic_positions() -> None:
    candidates = {
        1: (
            _candidate(10, 1, category="Mythic"),
            _candidate(20, 1, category="Mythic"),
        )
    }

    possible = ExtremeMaxResourceOrdinaryNamedGearSearchService._identity_legality_possible(
        counts=(1, 1),
        candidates_by_count=candidates,
    )

    assert possible is False


def test_identity_precheck_allows_one_mythic_plus_distinct_non_mythic() -> None:
    candidates = {
        1: (
            _candidate(10, 1, category="Mythic"),
            _candidate(20, 1),
        )
    }

    possible = ExtremeMaxResourceOrdinaryNamedGearSearchService._identity_legality_possible(
        counts=(1, 1),
        candidates_by_count=candidates,
    )

    assert possible is True


def test_identity_precheck_rejects_cross_count_duplicate_identity_only_domain() -> None:
    shared = _eligibility(10)
    candidates = {
        2: (_Candidate(10, "Set 10", 2, 1000.0, shared, ()),),
        3: (_Candidate(10, "Set 10", 3, 1000.0, shared, ()),),
    }

    possible = ExtremeMaxResourceOrdinaryNamedGearSearchService._identity_legality_possible(
        counts=(2, 3),
        candidates_by_count=candidates,
    )

    assert possible is False


def test_identity_precheck_allows_distinct_non_mythic_cross_count_matching() -> None:
    candidates = {
        2: (
            _candidate(10, 2),
            _candidate(20, 2),
        ),
        3: (
            _candidate(10, 3),
            _candidate(30, 3),
        ),
    }

    possible = ExtremeMaxResourceOrdinaryNamedGearSearchService._identity_legality_possible(
        counts=(2, 3),
        candidates_by_count=candidates,
    )

    assert possible is True


def test_impossible_identity_topology_returns_before_dfs() -> None:
    mythic_10 = _eligibility(10, category="Mythic")
    mythic_20 = _eligibility(20, category="Mythic")
    service = _service(mythic_10, mythic_20)
    topology = ExtremeGearSetCountTopology(counts=(1, 1), unused_units=10)
    candidates = {
        1: (
            _Candidate(10, "Set 10", 1, 1000.0, mythic_10, ()),
            _Candidate(20, "Set 20", 1, 900.0, mythic_20, ()),
        )
    }
    frontier = ExtremeGearSetBonusBreakpointCatalog(
        sets=(
            ExtremeGearSetBonusBreakpoints(
                set_id=10,
                name="Set 10",
                max_equip_count=1,
                bonus_counts=(1,),
            ),
            ExtremeGearSetBonusBreakpoints(
                set_id=20,
                name="Set 20",
                max_equip_count=1,
                bonus_counts=(1,),
            ),
        )
    )

    winner = service._search_topology(
        topology,
        candidates,
        frontier,
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    )

    assert winner.winner_found is False
    assert winner.best_exact_flat_delta is None
    assert winner.realizations == ()
    assert winner.stats.nodes == 0
    assert winner.stats.physical_pruned == 0


def test_physical_shape_precheck_rejects_four_ring_only_positions() -> None:
    topology = ExtremeGearSetCountTopology(counts=(1, 1, 1, 1), unused_units=8)
    ring_rows = tuple(_ring_only(set_id) for set_id in (10, 20, 30, 40))
    candidates = {
        1: tuple(
            _Candidate(
                row.set_id,
                row.name,
                1,
                1000.0,
                row,
                (),
            )
            for row in ring_rows
        )
    }

    possible = ExtremeMaxResourceOrdinaryNamedGearSearchService._physical_shape_legality_possible(
        topology=topology,
        counts=topology.counts,
        candidates_by_count=candidates,
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    )

    assert possible is False


def test_physical_shape_precheck_allows_broad_slot_positions() -> None:
    topology = ExtremeGearSetCountTopology(counts=(1, 1, 1, 1), unused_units=8)
    candidates = {
        1: tuple(_candidate(set_id, 1) for set_id in (10, 20, 30, 40))
    }

    possible = ExtremeMaxResourceOrdinaryNamedGearSearchService._physical_shape_legality_possible(
        topology=topology,
        counts=topology.counts,
        candidates_by_count=candidates,
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    )

    assert possible is True


def test_impossible_physical_shape_topology_returns_before_dfs() -> None:
    ring_rows = tuple(_ring_only(set_id) for set_id in (10, 20, 30, 40))
    service = _service(*ring_rows)
    topology = ExtremeGearSetCountTopology(counts=(1, 1, 1, 1), unused_units=8)
    candidates = {
        1: tuple(
            _Candidate(row.set_id, row.name, 1, 1000.0, row, ())
            for row in ring_rows
        )
    }
    frontier = ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(
            ExtremeGearSetBonusBreakpoints(
                set_id=row.set_id,
                name=row.name,
                max_equip_count=1,
                bonus_counts=(1,),
            )
            for row in ring_rows
        )
    )

    winner = service._search_topology(
        topology,
        candidates,
        frontier,
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    )

    assert winner.winner_found is False
    assert winner.best_exact_flat_delta is None
    assert winner.realizations == ()
    assert winner.stats.nodes == 0
    assert winner.stats.physical_pruned == 0


def test_physical_shape_precheck_respects_finite_broad_shape_capacity() -> None:
    topology = ExtremeGearSetCountTopology(counts=(1, 1, 1, 1), unused_units=8)
    broad = _eligibility(10)
    ring_rows = tuple(_ring_only(set_id) for set_id in (20, 30, 40))
    candidates = {
        1: (
            _Candidate(broad.set_id, broad.name, 1, 1000.0, broad, ()),
            *tuple(
                _Candidate(row.set_id, row.name, 1, 900.0, row, ())
                for row in ring_rows
            ),
        )
    }

    possible = ExtremeMaxResourceOrdinaryNamedGearSearchService._physical_shape_legality_possible(
        topology=topology,
        counts=topology.counts,
        candidates_by_count=candidates,
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    )

    assert possible is False


def test_physical_shape_precheck_allows_when_shape_capacity_is_sufficient() -> None:
    topology = ExtremeGearSetCountTopology(counts=(1, 1, 1, 1), unused_units=8)
    broad_rows = (_eligibility(10), _eligibility(11))
    ring_rows = (_ring_only(20), _ring_only(30))
    candidates = {
        1: tuple(
            _Candidate(row.set_id, row.name, 1, 1000.0, row, ())
            for row in (*broad_rows, *ring_rows)
        )
    }

    possible = ExtremeMaxResourceOrdinaryNamedGearSearchService._physical_shape_legality_possible(
        topology=topology,
        counts=topology.counts,
        candidates_by_count=candidates,
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    )

    assert possible is True


def test_finite_shape_capacity_impossible_topology_returns_before_dfs() -> None:
    broad = _eligibility(10)
    ring_rows = tuple(_ring_only(set_id) for set_id in (20, 30, 40))
    rows = (broad, *ring_rows)
    service = _service(*rows)
    topology = ExtremeGearSetCountTopology(counts=(1, 1, 1, 1), unused_units=8)
    candidates = {
        1: tuple(
            _Candidate(row.set_id, row.name, 1, 1000.0, row, ())
            for row in rows
        )
    }
    frontier = ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(
            ExtremeGearSetBonusBreakpoints(
                set_id=row.set_id,
                name=row.name,
                max_equip_count=row.max_equip_count,
                bonus_counts=(1,),
            )
            for row in rows
        )
    )

    winner = service._search_topology(
        topology,
        candidates,
        frontier,
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    )

    assert winner.winner_found is False
    assert winner.best_exact_flat_delta is None
    assert winner.realizations == ()
    assert winner.stats.nodes == 0
    assert winner.stats.physical_pruned == 0
