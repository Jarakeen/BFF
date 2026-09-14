from __future__ import annotations

import sqlite3

from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_constrained_named_gear_exact_flat_search_service import (
    ExtremeConstrainedNamedGearExactFlatSearchService,
    ExtremeNamedGearRequirement,
)
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
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


_EQUIP_IDS = {
    "Head": 1,
    "Necklace": 2,
    "Chest": 3,
    "Shoulders": 4,
    "Waist": 8,
    "Legs": 9,
    "Feet": 10,
    "Ring": 12,
    "Hands": 13,
}
_BODY = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
_WEAPONS = (
    "Axe", "Mace", "Sword", "Dagger", "Shield",
    "Two-Handed Sword", "Two-Handed Axe", "Two-Handed Mace",
    "Bow", "Restoration Staff", "Inferno Staff", "Ice Staff", "Lightning Staff",
)


def _database(path, weighted_sets: tuple[tuple[int, int], ...]):
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE gear_set_piece (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                equip_type INTEGER,
                armor_type INTEGER,
                weapon_type INTEGER
            )
            """
        )
        rows = []
        for set_id, weight in weighted_sets:
            for slot in _BODY:
                rows.append((set_id, _EQUIP_IDS[slot], weight, 0))
        connection.executemany(
            "INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES (?, ?, ?, ?)",
            rows,
        )


def _ordinary(set_id: int) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Set {set_id}",
        category="Trial",
        max_equip_count=5,
        armor_slots=_BODY,
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=_WEAPONS,
    )


def _monster(set_id: int) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Set {set_id}",
        category="Monster Set",
        max_equip_count=2,
        armor_slots=("Head", "Shoulders"),
    )


def _evidence(set_id: int, count: int, delta: float, *, irrelevant: bool = False):
    effect = Effect(
        operation=EffectOperation.ADD,
        value=float(delta),
        source=f"Set {set_id} ({count})",
        stat=StatId.HEALTH_RECOVERY,
    )
    candidate = ExtremeGearSetObjectiveCandidate(
        set_id=set_id,
        set_name=f"Set {set_id}",
        category="Monster Set" if count == 2 else "Trial",
        equipped_piece_count=count,
        objective_key="health_recovery",
        reviewed_delta=float(delta),
        source_effects=(effect,),
    )
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=f"Set {set_id}",
        piece_count=count,
        objective_key="health_recovery",
        status=(
            ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT
            if irrelevant
            else ExtremeGearSetObjectiveRelevance.RELEVANT
        ),
        reviewed_delta=float(delta),
        candidate=candidate,
    )


def test_required_medium_five_piece_can_survive_heavy_filter_via_nonarmor_slots(tmp_path):
    database = tmp_path / "eso.db"
    _database(database, ((10, 3), (20, 2), (30, 3)))
    raw = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=(_ordinary(10), _ordinary(20), _ordinary(30))
    )
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database, raw, required_armor_weight="Heavy"
    )
    breakpoints = ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(
            ExtremeGearSetBonusBreakpoints(
                set_id=set_id,
                name=f"Set {set_id}",
                max_equip_count=5,
                bonus_counts=(5,),
            )
            for set_id in (10, 20, 30)
        )
    )
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="health_recovery",
        evidence=(_evidence(10, 5, 100.0), _evidence(20, 5, 0.0, irrelevant=True), _evidence(30, 5, 90.0)),
    )
    topology = ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=(ExtremeGearSetCountTopology(counts=(5, 5), unused_units=2),),
    )

    result = ExtremeConstrainedNamedGearExactFlatSearchService(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=relevance,
        requirements=(ExtremeNamedGearRequirement("Set 20", 5),),
    ).search(topology)

    assert filtered.denominator_proven is True
    assert filtered.catalog.by_set_id(20).armor_slots == ()
    assert result.winner_found is True
    assert result.best_exact_flat_delta == 100.0
    assert all(20 in witness.set_ids for witness in result.realizations)
    assert all(
        not any(assignment.set_id == 20 and assignment.slot in _BODY for assignment in witness.assignments)
        for witness in result.realizations
    )


def test_required_light_monster_set_is_rejected_by_heavy_filtered_shared_search(tmp_path):
    database = tmp_path / "eso.db"
    _database(database, ((10, 3), (20, 3), (30, 1)))
    raw = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=(_ordinary(10), _ordinary(20), _monster(30))
    )
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database, raw, required_armor_weight="Heavy"
    )
    breakpoints = ExtremeGearSetBonusBreakpointCatalog(
        sets=(
            ExtremeGearSetBonusBreakpoints(10, "Set 10", 5, (5,)),
            ExtremeGearSetBonusBreakpoints(20, "Set 20", 5, (5,)),
            ExtremeGearSetBonusBreakpoints(30, "Set 30", 2, (2,)),
        )
    )
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="health_recovery",
        evidence=(
            _evidence(10, 5, 100.0),
            _evidence(20, 5, 90.0),
            _evidence(30, 2, 0.0, irrelevant=True),
        ),
    )
    topology = ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=(ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0),),
    )

    result = ExtremeConstrainedNamedGearExactFlatSearchService(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=relevance,
        requirements=(ExtremeNamedGearRequirement("Set 30", 2),),
    ).search(topology)

    assert filtered.catalog.by_set_id(30).armor_slots == ()
    assert result.winner_found is False
