from minmax.combat_state import CombatState
from minmax.combat_state_input_resolver import CombatStateInputResolver
from minmax.gear_stat_inputs import GearCalculationInputs
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    SPELL_POWER_CURE_MAJOR_COURAGE_CONDITION,
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedPhase5ContextFactory,
)


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Spell Power Cure"
    return build


def test_spell_power_cure_requires_five_equipped_pieces_for_h1_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert SPELL_POWER_CURE_MAJOR_COURAGE_CONDITION not in inactive.condition_context
    assert SPELL_POWER_CURE_MAJOR_COURAGE_CONDITION in active.condition_context
    assert any("self-overheal" in item for item in active.evidence)


def test_spell_power_cure_witness_routes_through_canonical_major_courage() -> None:
    state = ExtremeResourceConditionedPhase5ContextFactory._combat_state_with_reviewed_gear_witnesses(
        CombatState(active_buffs=("Major Courage",)),
        frozenset({SPELL_POWER_CURE_MAJOR_COURAGE_CONDITION}),
    )

    assert state.in_combat is True
    assert state.active_buffs == ("Major Courage",)

    inputs = CombatStateInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(),
        combat_state=state,
    )
    weapon = sum(item.value for item in inputs.core.weapon_damage.flat)
    spell = sum(item.value for item in inputs.core.spell_damage.flat)

    assert weapon == 430.0
    assert spell == 430.0


def test_spell_power_cure_exact_h1_blocker_is_reviewed_after_witness_path() -> None:
    blocker = (
        "Spell Power Cure (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) When you overheal yourself or an ally, you give the target Major Courage "
        "for 5 seconds which increases their Weapon and Spell Damage by 430."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Spell Power Cure",
        category="Test",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)
