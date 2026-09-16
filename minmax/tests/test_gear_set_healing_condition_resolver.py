from minmax.effects import EffectOperation, EffectUnit
from minmax.gear_set_healing_condition_resolver import GearSetHealingConditionResolver
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId


def test_back_alley_gourmand_maps_food_conditioned_critical_healing() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) While you have a food buff active, your Critical Damage and "
            "Critical Healing is increased by 13%."
        ),
    )

    effects = GearSetHealingConditionResolver().resolve(
        bonus,
        source="Back-Alley Gourmand (5)",
    )

    assert [
        (effect.stat, effect.value, effect.operation, effect.unit, effect.condition)
        for effect in effects
    ] == [
        (
            StatId.CRITICAL_DAMAGE,
            13.0,
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
            "food_buff_active",
        ),
        (
            StatId.CRITICAL_HEALING,
            13.0,
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
            "food_buff_active",
        ),
    ]


def test_triggered_dodge_critical_healing_maps_explicit_runtime_condition() -> None:
    bonus = GearSetBonus(
        id=2,
        set_id=2,
        piece_count=5,
        description=(
            "(5 items) Whenever you successfully Dodge, increase your Critical Damage "
            "and Critical Healing by 15% for 10 seconds."
        ),
    )

    effects = GearSetHealingConditionResolver().resolve(
        bonus,
        source="Senche's Bite (5)",
    )

    assert [
        (effect.stat, effect.value, effect.operation, effect.unit, effect.condition)
        for effect in effects
    ] == [
        (
            StatId.CRITICAL_DAMAGE,
            15.0,
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
            "successful_dodge_recent",
        ),
        (
            StatId.CRITICAL_HEALING,
            15.0,
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
            "successful_dodge_recent",
        ),
    ]
