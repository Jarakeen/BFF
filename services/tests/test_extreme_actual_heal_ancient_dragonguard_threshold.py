from minmax.gear_sets import GearSetBonus
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Ancient Dragonguard"
    return build


def test_ancient_dragonguard_requires_five_pieces_for_threshold_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION not in inactive.condition_context
    assert ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION in active.condition_context
    assert any("above 50% current Health" in item for item in active.evidence)


def test_ancient_dragonguard_exact_tooltip_maps_conditional_flat_power() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) Adds 8-300 Weapon and Spell Damage while your Health is above 50%. "
            "Adds 80-3460 Physical and Spell Resistance while your Health is 50% or less."
        ),
    )

    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(bonus)

    assert len(effects) == 2
    assert {effect.value for effect in effects} == {300.0}
    assert {effect.condition for effect in effects} == {
        ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION
    }


def test_ancient_dragonguard_exact_h1_blocker_is_reviewed_by_threshold_state() -> None:
    blocker = (
        "Ancient Dragonguard (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Adds 8-300 Weapon and Spell Damage while your Health is above 50%. "
        "Adds 80-3460 Physical and Spell Resistance while your Health is 50% or less."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Ancient Dragonguard",
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
