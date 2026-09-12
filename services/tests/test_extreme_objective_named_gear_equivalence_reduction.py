from __future__ import annotations

from minmax.effect_kinds import EffectKind
from minmax.effects import Effect, EffectOperation, EffectUnit
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
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
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


def _eligibility(set_id: int, name: str, *, armor_slots=_BODY):
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=name,
        category="Trial",
        max_equip_count=5,
        armor_slots=tuple(armor_slots),
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=_WEAPONS,
    )


def _breakpoint(set_id: int, name: str, count: int = 2):
    return ExtremeGearSetBonusBreakpoints(
        set_id=set_id,
        name=name,
        max_equip_count=5,
        bonus_counts=(count,),
    )


def _evidence(
    set_id: int,
    name: str,
    *,
    count: int = 2,
    value: float = 1206.0,
    unresolved: tuple[str, ...] = (),
):
    effect = Effect(
        operation=EffectOperation.ADD,
        value=value,
        source=f"{name} ({count})",
        stat=StatId.MAX_HEALTH,
        kind=EffectKind.STAT,
        unit=EffectUnit.FLAT,
    )
    candidate = ExtremeGearSetObjectiveCandidate(
        set_id=set_id,
        set_name=name,
        category="Trial",
        equipped_piece_count=count,
        objective_key="max_health",
        reviewed_delta=value,
        source_effects=(effect,),
        unresolved=unresolved,
    )
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=name,
        piece_count=count,
        objective_key="max_health",
        status=ExtremeGearSetObjectiveRelevance.RELEVANT,
        reviewed_delta=value,
        candidate=candidate,
    )


def _service(rows, *, topologies):
    eligibilities = tuple(_eligibility(set_id, name) for set_id, name, _, _ in rows)
    breakpoints = tuple(_breakpoint(set_id, name, count) for set_id, name, count, _ in rows)
    evidence = tuple(
        _evidence(set_id, name, count=count, value=value)
        for set_id, name, count, value in rows
    )
    service = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(sets=breakpoints),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(sets=eligibilities),
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key="max_health",
            evidence=evidence,
        ),
    )
    topology_catalog = ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=tuple(topologies),
    )
    return service, topology_catalog


def _retained_ids(catalog, count: int) -> tuple[int, ...]:
    return tuple(
        sorted(
            int(row.set_id)
            for row in catalog.sets
            if int(count) in tuple(int(value) for value in row.bonus_counts)
        )
    )


def test_equivalent_candidates_keep_only_topology_part_limit():
    rows = tuple((set_id, f"Set {set_id}", 2, 1206.0) for set_id in range(10, 20))
    service, topology = _service(
        rows,
        topologies=(ExtremeGearSetCountTopology(counts=(2, 2, 2), unused_units=6),),
    )

    reduced, pruned, limit = service.proof_reduced_breakpoints(topology)

    assert limit == 3
    assert pruned == 7
    assert _retained_ids(reduced, 2) == (10, 11, 12)


def test_different_objective_effect_values_do_not_collapse_together():
    rows = (
        (10, "Low A", 2, 1206.0),
        (11, "Low B", 2, 1206.0),
        (20, "High A", 2, 1487.0),
        (21, "High B", 2, 1487.0),
    )
    service, topology = _service(
        rows,
        topologies=(ExtremeGearSetCountTopology(counts=(2,), unused_units=10),),
    )

    reduced, pruned, limit = service.proof_reduced_breakpoints(topology)

    assert limit == 1
    assert pruned == 2
    assert _retained_ids(reduced, 2) == (10, 20)


def test_different_physical_eligibility_does_not_collapse():
    rows = (
        (10, "Body Set", 2, 1206.0),
        (20, "Other Body Set", 2, 1206.0),
    )
    breakpoints = ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(_breakpoint(set_id, name) for set_id, name, _, _ in rows)
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=(
            _eligibility(10, "Body Set", armor_slots=_BODY),
            _eligibility(20, "Other Body Set", armor_slots=("Head", "Shoulders")),
        )
    )
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_health",
        evidence=tuple(_evidence(set_id, name) for set_id, name, _, _ in rows),
    )
    service = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    topology = ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=(ExtremeGearSetCountTopology(counts=(2,), unused_units=10),),
    )

    reduced, pruned, _ = service.proof_reduced_breakpoints(topology)

    assert pruned == 0
    assert _retained_ids(reduced, 2) == (10, 20)


def test_unresolved_candidate_is_never_equivalence_pruned():
    rows = tuple((set_id, f"Set {set_id}") for set_id in (10, 20, 30))
    service = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(
            sets=tuple(_breakpoint(set_id, name) for set_id, name in rows)
        ),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(
            sets=tuple(_eligibility(set_id, name) for set_id, name in rows)
        ),
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key="max_health",
            evidence=tuple(
                _evidence(
                    set_id,
                    name,
                    unresolved=("relevant set effect requires condition mystery",),
                )
                for set_id, name in rows
            ),
        ),
    )
    topology = ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=(ExtremeGearSetCountTopology(counts=(2,), unused_units=10),),
    )

    reduced, pruned, _ = service.proof_reduced_breakpoints(topology)

    assert pruned == 0
    assert _retained_ids(reduced, 2) == (10, 20, 30)


def test_build_preserves_denominator_proof_after_exact_equivalence_reduction():
    rows = tuple((set_id, f"Set {set_id}", 2, 1206.0) for set_id in (10, 20, 30, 40))
    service, topology = _service(
        rows,
        topologies=(ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8),),
    )

    result = service.build(topology)

    assert result.breakpoints_pruned_equivalent == 2
    assert result.representative_limit_per_equivalence_class == 2
    assert result.equivalence_reduction_proven is True
    assert result.assignments_considered == 1
    assert result.assignments_realized == 1
    assert result.denominator_proven is True
    assert result.realization.topologies[0].realizations[0].set_ids == (10, 20)
