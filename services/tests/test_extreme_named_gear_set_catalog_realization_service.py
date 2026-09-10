from __future__ import annotations

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


_BODY = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
_WEAPONS = (
    "Axe", "Mace", "Sword", "Dagger", "Shield",
    "Two-Handed Sword", "Two-Handed Axe", "Two-Handed Mace",
    "Bow", "Restoration Staff", "Inferno Staff", "Ice Staff", "Lightning Staff",
)


def _ordinary(set_id: int, name: str, *, breakpoints=(5,)):
    eligibility = ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=name,
        category="Trial",
        max_equip_count=5,
        armor_slots=_BODY,
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=_WEAPONS,
    )
    bp = ExtremeGearSetBonusBreakpoints(
        set_id=set_id,
        name=name,
        max_equip_count=5,
        bonus_counts=tuple(breakpoints),
    )
    return eligibility, bp


def _monster(set_id: int, name: str):
    eligibility = ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=name,
        category="Monster Set",
        max_equip_count=2,
        armor_slots=("Head", "Shoulders"),
    )
    bp = ExtremeGearSetBonusBreakpoints(
        set_id=set_id,
        name=name,
        max_equip_count=2,
        bonus_counts=(1, 2),
    )
    return eligibility, bp


def _service(rows, *, breakpoint_unresolved=(), eligibility_unresolved=()):
    eligibilities = tuple(row[0] for row in rows)
    breakpoints = tuple(row[1] for row in rows)
    return ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(
            sets=breakpoints,
            unresolved=tuple(breakpoint_unresolved),
        ),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(
            sets=eligibilities,
            unresolved=tuple(eligibility_unresolved),
        ),
    )


def test_catalog_realizer_finds_concrete_five_five_two_named_assignment():
    service = _service(
        (
            _ordinary(10, "Five A"),
            _ordinary(20, "Five B"),
            _monster(30, "Monster"),
        )
    )
    topology = ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0)

    result = service.realize_topology(topology)

    assert result.denominator_proven is True
    assert result.assignments_considered == 1
    assert result.assignments_realized == 1
    assert result.assignments_rejected == 0
    assert result.realizations[0].set_ids == (10, 20, 30)


def test_equal_count_parts_are_symmetry_reduced_by_set_identity():
    rows = tuple(_ordinary(set_id, f"Set {set_id}", breakpoints=(2,)) for set_id in (10, 20, 30))
    service = _service(rows)
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)

    result = service.realize_topology(topology)

    assert result.assignments_considered == 3
    assert result.assignments_realized == 3
    assert {row.set_ids for row in result.realizations} == {
        (10, 20),
        (10, 30),
        (20, 30),
    }


def test_slot_collisions_are_counted_as_rejected_named_assignments():
    service = _service((_monster(30, "Monster A"), _monster(31, "Monster B")))
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)

    result = service.realize_topology(topology)

    assert result.assignments_considered == 1
    assert result.assignments_realized == 0
    assert result.assignments_rejected == 1
    assert result.denominator_proven is True


def test_assignment_limit_marks_result_truncated_and_blocks_denominator_proof():
    rows = tuple(_ordinary(set_id, f"Set {set_id}", breakpoints=(2,)) for set_id in (10, 20, 30, 40))
    service = _service(rows)
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)

    result = service.realize_topology(topology, max_assignments=2)

    assert result.assignments_considered == 2
    assert result.truncated is True
    assert result.denominator_proven is False


def test_catalog_unresolved_evidence_propagates_and_blocks_proof():
    service = _service(
        (_ordinary(10, "Five A"),),
        breakpoint_unresolved=("broken bonus row",),
        eligibility_unresolved=("missing slot row",),
    )
    topology = ExtremeGearSetCountTopology(counts=(5,), unused_units=7)

    result = service.realize_topology(topology)

    assert result.assignments_realized == 1
    assert result.denominator_proven is False
    assert result.unresolved == ("broken bonus row", "missing slot row")


def test_build_aggregates_counts_and_preserves_topology_catalog_unresolved():
    service = _service((_ordinary(10, "Five A"), _ordinary(20, "Five B")))
    topologies = ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=(
            ExtremeGearSetCountTopology(counts=(), unused_units=12),
            ExtremeGearSetCountTopology(counts=(5,), unused_units=7),
        ),
        unresolved=("topology evidence gap",),
    )

    result = service.build(topologies)

    assert len(result.topologies) == 2
    assert result.assignments_considered == 3
    assert result.assignments_realized == 3
    assert result.assignments_rejected == 0
    assert result.denominator_proven is False
    assert result.unresolved == ("topology evidence gap",)
