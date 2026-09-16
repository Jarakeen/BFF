from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    ARMOR_OF_TRUTH_POWER_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Armor of Truth"
    return build


def test_armor_of_truth_requires_five_pieces_for_setup_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert ARMOR_OF_TRUTH_POWER_CONDITION not in inactive.condition_context
    assert ARMOR_OF_TRUTH_POWER_CONDITION in active.condition_context
    assert any("Off Balance" in item for item in active.evidence)


def test_armor_of_truth_maps_conditional_power_window() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) When you deal damage to an enemy who is Off Balance, your Weapon and "
            "Spell Damage are increased by 460 for 10 seconds."
        ),
    )

    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(bonus)

    assert {effect.stat for effect in effects} == {StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE}
    assert {effect.value for effect in effects} == {460.0}
    assert {effect.condition for effect in effects} == {ARMOR_OF_TRUTH_POWER_CONDITION}


def test_armor_of_truth_h1_blocker_is_reviewed_by_off_balance_damage_witness() -> None:
    blocker = (
        "Armor of Truth (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) When you deal damage to an enemy who is Off Balance, your Weapon and Spell "
        "Damage are increased by 460 for 10 seconds."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Armor of Truth",
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
