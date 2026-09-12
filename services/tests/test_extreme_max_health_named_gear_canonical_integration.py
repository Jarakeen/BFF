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


def _breakpoint(set_id: int) -> ExtremeGearSetBonusBreakpoints:
    return ExtremeGearSetBonusBreakpoints(
        set_id=set_id,
        name=f"Set {set_id}",
        max_equip_count=5,
        bonus_counts=(2,),
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


def _evidence(set_id: int, delta: float) -> ExtremeGearSetObjectiveBreakpointEvidence:
    effect = Effect(
        operation=EffectOperation.ADD,
        value=delta,
        source=f"Set {set_id}",
        stat=StatId.MAX_HEALTH,
    )
    candidate = ExtremeGearSetObjectiveCandidate(
        set_id=set_id,
        set_name=f"Set {set_id}",
        category="Trial",
        equipped_piece_count=2,
        objective_key="max_health",
        reviewed_delta=delta,
        source_effects=(effect,),
    )
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=f"Set {set_id}",
        piece_count=2,
        objective_key="max_health",
        status=ExtremeGearSetObjectiveRelevance.RELEVANT,
        reviewed_delta=delta,
        candidate=candidate,
    )


def _service() -> ExtremeObjectiveNamedGearSetCatalogRealizationService:
    ids = (10, 20, 30)
    return ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(
            sets=tuple(_breakpoint(set_id) for set_id in ids),
        ),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(
            sets=tuple(_eligibility(set_id) for set_id in ids),
        ),
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key="max_health",
            evidence=(
                _evidence(10, 1000.0),
                _evidence(20, 900.0),
                _evidence(30, 800.0),
            ),
        ),
    )


def _topology() -> ExtremeGearSetTopologyCatalog:
    return ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=(ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8),),
    )


def test_uncapped_max_health_build_uses_proven_candidate_frontier() -> None:
    result = _service().build(_topology())

    assert result.candidate_reduction_proven is True
    assert result.denominator_proven is True
    assert result.truncated is False
    assert result.assignments_realized == 1
    assert result.realization.topologies[0].realizations[0].set_ids == (10, 20)


def test_capped_max_health_build_preserves_explicit_truncation_path() -> None:
    result = _service().build(_topology(), max_assignments_per_topology=1)

    assert result.truncated is True
    assert result.denominator_proven is False
