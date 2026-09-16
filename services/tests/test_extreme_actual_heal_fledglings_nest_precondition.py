from minmax.combat_state import CombatState
from minmax.combat_state_input_resolver import CombatStateInputResolver
from minmax.gear_stat_inputs import GearCalculationInputs
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    FLEDGLINGS_NEST_MINOR_COURAGE_CONDITION,
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedPhase5ContextFactory,
)


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Fledgling's Nest"
    return build


def test_fledglings_nest_requires_five_equipped_pieces_for_h1_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert FLEDGLINGS_NEST_MINOR_COURAGE_CONDITION not in inactive.condition_context
    assert FLEDGLINGS_NEST_MINOR_COURAGE_CONDITION in active.condition_context
    assert any("Gryphon Nest" in item for item in active.evidence)


def test_fledglings_nest_witness_routes_through_canonical_minor_courage() -> None:
    state = ExtremeResourceConditionedPhase5ContextFactory._combat_state_with_reviewed_gear_witnesses(
        CombatState(active_buffs=("Minor Courage",)),
        frozenset({FLEDGLINGS_NEST_MINOR_COURAGE_CONDITION}),
    )

    # CombatState is the canonical named-buff dedup boundary.
    assert state.in_combat is True
    assert state.active_buffs == ("Minor Courage",)

    inputs = CombatStateInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(),
        combat_state=state,
    )
    weapon = sum(item.value for item in inputs.core.weapon_damage.flat)
    spell = sum(item.value for item in inputs.core.spell_damage.flat)

    assert weapon == 215.0
    assert spell == 215.0


def test_fledglings_nest_exact_h1_blocker_is_reviewed_only_after_witness_path() -> None:
    blocker = (
        "Fledgling's Nest (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) While in combat, casting an ability that leaves an effect on the ground "
        "creates an 8 meter Gryphon Nest for 10 seconds. You and group members inside the "
        "Nest gain 168 Magicka and Stamina Recovery. The first time you or a group member "
        "leaves the Nest, they gain Minor Courage for 10 seconds, increasing their Weapon "
        "and Spell Damage by 215. This effect can occur once every 10 seconds."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Fledgling's Nest",
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
