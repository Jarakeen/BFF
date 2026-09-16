from minmax.combat_state import CombatState
from minmax.combat_state_input_resolver import CombatStateInputResolver
from minmax.gear_stat_inputs import GearCalculationInputs
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    NAGA_SHAMAN_MINOR_MENDING_CONDITION,
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedPhase5ContextFactory,
)


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Naga Shaman"
    return build


def test_naga_shaman_requires_five_pieces_for_minor_mending_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert NAGA_SHAMAN_MINOR_MENDING_CONDITION not in inactive.condition_context
    assert NAGA_SHAMAN_MINOR_MENDING_CONDITION in active.condition_context
    assert any("damage shield" in item for item in active.evidence)


def test_naga_shaman_routes_through_canonical_minor_mending_without_stacking() -> None:
    state = ExtremeResourceConditionedPhase5ContextFactory._combat_state_with_reviewed_gear_witnesses(
        CombatState(active_buffs=("Minor Mending",)),
        frozenset({NAGA_SHAMAN_MINOR_MENDING_CONDITION}),
    )

    assert state.in_combat is True
    assert state.active_buffs == ("Minor Mending",)

    inputs = CombatStateInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(),
        combat_state=state,
    )
    healing_done = sum(item.value for item in inputs.core.healing_done.additive)

    assert healing_done == 0.08


def test_naga_shaman_exact_h1_blocker_is_reviewed_by_self_shield_witness() -> None:
    blocker = (
        "Naga Shaman (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) When you apply a damage shield to yourself or an ally, you gain Minor "
        "Mending and Minor Vitality for 6 seconds, increasing your healing done by 8% and "
        "healing received and damage shield strength by 6%. This effect can occur once every "
        "6 seconds."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Naga Shaman",
        category="Test",
        equipped_piece_count=5,
        objective_key="healing_done",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)
