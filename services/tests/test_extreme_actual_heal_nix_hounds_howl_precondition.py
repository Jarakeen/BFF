from minmax.combat_state import CombatState
from minmax.combat_state_input_resolver import CombatStateInputResolver
from minmax.gear_stat_inputs import GearCalculationInputs
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    NIX_HOUNDS_HOWL_MAJOR_COURAGE_CONDITION,
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedPhase5ContextFactory,
)


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Nix-Hound's Howl"
    return build


def test_nix_hounds_howl_requires_five_pieces_for_major_courage_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert NIX_HOUNDS_HOWL_MAJOR_COURAGE_CONDITION not in inactive.condition_context
    assert NIX_HOUNDS_HOWL_MAJOR_COURAGE_CONDITION in active.condition_context
    assert any("fully-charged Heavy Attack" in item for item in active.evidence)


def test_nix_hounds_howl_routes_through_canonical_major_courage() -> None:
    state = ExtremeResourceConditionedPhase5ContextFactory._combat_state_with_reviewed_gear_witnesses(
        CombatState(active_buffs=("Major Courage",)),
        frozenset({NIX_HOUNDS_HOWL_MAJOR_COURAGE_CONDITION}),
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


def test_nix_hounds_howl_exact_h1_blocker_is_reviewed_by_heavy_attack_witness() -> None:
    blocker = (
        "Nix-Hound's Howl (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Completing a fully-charged Heavy Attack applies Major Cowardice to your "
        "target for 1 second per 1000 Weapon Damage you have, lowering their Weapon and Spell "
        "Damage by 430. You then gain Major Courage for the same duration, increasing your "
        "Weapon and Spell Damage by 430. This effect can occur once every 12 seconds."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Nix-Hound's Howl",
        category="Test",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)
