from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    ARMOR_OF_THE_VEILED_HERITANCE_POWER_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Armor of the Veiled Heritance"
    return build


def test_veiled_heritance_requires_five_pieces_for_interrupt_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert ARMOR_OF_THE_VEILED_HERITANCE_POWER_CONDITION not in inactive.condition_context
    assert ARMOR_OF_THE_VEILED_HERITANCE_POWER_CONDITION in active.condition_context
    assert any("interrupt" in item.casefold() for item in active.evidence)


def test_veiled_heritance_maps_conditional_power_window_and_ignores_bash_rider() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) When you interrupt an enemy, you gain 12-516 Weapon and Spell Damage for "
            "15 seconds. Your Bash attacks deal 12-516 more damage."
        ),
    )

    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(bonus)

    assert {effect.stat for effect in effects} == {StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE}
    assert {effect.value for effect in effects} == {516.0}
    assert {effect.condition for effect in effects} == {
        ARMOR_OF_THE_VEILED_HERITANCE_POWER_CONDITION
    }


def test_veiled_heritance_h1_blocker_is_reviewed_by_interrupt_witness() -> None:
    blocker = (
        "Armor of the Veiled Heritance (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) When you interrupt an enemy, you gain 12-516 Weapon and Spell Damage for "
        "15 seconds. Your Bash attacks deal 12-516 more damage."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Armor of the Veiled Heritance",
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
