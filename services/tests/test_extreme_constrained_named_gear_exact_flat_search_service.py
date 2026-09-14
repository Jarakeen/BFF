from __future__ import annotations

from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
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


_BODY = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
_WEAPONS = (
    "Axe", "Mace", "Sword", "Dagger", "Shield",
    "Two-Handed Sword", "Two-Handed Axe", "Two-Handed Mace",
    "Bow", "Restoration Staff", "Inferno Staff", "Ice Staff", "Lightning Staff",
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


def _breakpoint(set_id: int, count: int = 5) -> ExtremeGearSetBonusBreakpoints:
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
    status: ExtremeGearSetObjectiveRelevance = ExtremeGearSetObjectiveRelevance.RELEVANT,
    operation: EffectOperation = EffectOperation.ADD,
) -> ExtremeGearSetObjectiveBreakpointEvidence:
    effect = Effect(
        operation=operation,
        value=float(delta),
        source=f"Set {set_id} (5)",
        stat=StatId.HEALTH_RECOVERY,
    )
    candidate = ExtremeGearSetObjectiveCandidate(
        set_id=set_id,
        set_name=f"Set {set_id}",
        category="Trial",
        equipped_piece_count=5,
        objective_key="health_recovery",
        reviewed_delta=float(delta),
        source_effects=(effect,),
    )
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=f"Set {set_id}",
        piece_count=5,
        objective_key="health_recovery",
        status=status,
        reviewed_delta=float(delta),
        candidate=candidate,
    )


def _service(
    evidence: tuple[ExtremeGearSetObjectiveBreakpointEvidence, ...],
    requirements: tuple[ExtremeNamedGearRequirement, ...],
) -> ExtremeConstrainedNamedGearExactFlatSearchService:
    ids = tuple(row.set_id for row in evidence)
    return ExtremeConstrainedNamedGearExactFlatSearchService(
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(
            sets=tuple(_breakpoint(set_id) for set_id in ids)
        ),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(
            sets=tuple(_eligibility(set_id) for set_id in ids)
        ),
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key="health_recovery",
            evidence=evidence,
        ),
        requirements=requirements,
    )


def _catalog() -> ExtremeGearSetTopologyCatalog:
    return ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=(ExtremeGearSetCountTopology(counts=(5, 5), unused_units=2),),
    )


def test_required_lower_scoring_set_beats_higher_unconstrained_pair() -> None:
    service = _service(
        (_evidence(10, 100.0), _evidence(20, 10.0), _evidence(30, 90.0)),
        (ExtremeNamedGearRequirement("Set 20", 5),),
    )

    result = service.search(_catalog())

    assert result.winner_found is True
    assert result.best_exact_flat_delta == 110.0
    assert all(20 in witness.set_ids for witness in result.realizations)
    assert all(frozenset(witness.set_ids) != frozenset({10, 30}) for witness in result.realizations)


def test_proven_irrelevant_required_set_is_retained_as_zero_delta_carrier() -> None:
    service = _service(
        (
            _evidence(10, 100.0),
            _evidence(20, 0.0, status=ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
            _evidence(30, 90.0),
        ),
        (ExtremeNamedGearRequirement("Set 20", 5),),
    )

    result = service.search(_catalog())

    assert result.winner_found is True
    assert result.best_exact_flat_delta == 100.0
    assert all(20 in witness.set_ids for witness in result.realizations)


def test_constraint_bonus_never_leaks_into_returned_objective_score() -> None:
    service = _service(
        (_evidence(10, 25.0), _evidence(20, 5.0)),
        (ExtremeNamedGearRequirement("Set 20", 5),),
    )

    result = service.search(_catalog())

    assert result.best_exact_flat_delta == 30.0
    assert result.best_exact_flat_delta < service._constraint_bonus


def test_missing_required_named_set_fails_closed() -> None:
    service = _service(
        (_evidence(10, 100.0), _evidence(20, 10.0)),
        (ExtremeNamedGearRequirement("Not A Set", 5),),
    )

    result = service.search(_catalog())

    assert result.winner_found is False
    assert result.base_search is None
    assert result.unresolved


def test_nonflat_required_objective_effect_fails_closed() -> None:
    service = _service(
        (_evidence(10, 100.0), _evidence(20, 10.0, operation=EffectOperation.ADD_PERCENT)),
        (ExtremeNamedGearRequirement("Set 20", 5),),
    )

    result = service.search(_catalog())

    assert result.winner_found is False
    assert result.base_search is None
    assert any("non-flat or unresolved" in item for item in result.unresolved)


def test_health_recovery_is_supported_by_shared_constrained_search() -> None:
    service = _service(
        (_evidence(10, 100.0), _evidence(20, 10.0)),
        (ExtremeNamedGearRequirement("Set 20", 5),),
    )

    result = service.search(_catalog())

    assert result.objective_key == "health_recovery"
    assert result.exact_flat_branch_proven is True
