from minmax.effects import EffectOperation, EffectUnit
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from services.extreme_gear_set_resource_effect_resolver import (
    ExtremeGearSetResourceEffectResolver,
)


def _bonus(description: str) -> GearSetBonus:
    return GearSetBonus(id=1, set_id=1, piece_count=5, description=description)


def _rows(description: str):
    return [
        (effect.stat, effect.value, effect.condition, effect.operation, effect.unit)
        for effect in ExtremeGearSetResourceEffectResolver().resolve(_bonus(description))
    ]


def test_ebon_armory_maps_persistent_max_health():
    rows = _rows(
        "(5 items) Increases Max Health by 23-1000 for you and up to 11 other group members "
        "within 28 meters of you. This bonus persists through death."
    )
    assert rows == [
        (StatId.MAX_HEALTH, 1000.0, None, EffectOperation.ADD, EffectUnit.FLAT)
    ]


def test_xoryn_maps_both_max_resources():
    rows = _rows(
        "(5 items) Increases Max Magicka and Max Stamina by 1667 for you and up to 11 other "
        "group members within 28 meters of you. This bonus persists through death."
    )
    assert [(stat, value, condition) for stat, value, condition, _op, _unit in rows] == [
        (StatId.MAX_MAGICKA, 1667.0, None),
        (StatId.MAX_STAMINA, 1667.0, None),
    ]


def test_food_and_drink_conditions_are_preserved():
    green = _rows(
        "(5 items) While you have a food buff active, your Max Health is increased by 58-2500 "
        "and Health Recovery by 8-356."
    )
    bright = _rows(
        "(5 items) While you have a drink buff active, your Max Magicka is increased by 46-2000 "
        "and Magicka Recovery by 3-133."
    )
    bone = _rows(
        "(5 items) While you have a drink buff active, your Max Stamina is increased by 46-2000 "
        "and Stamina Recovery by 3-133."
    )

    assert (StatId.MAX_HEALTH, 2500.0, "food_buff_active") in [row[:3] for row in green]
    assert (StatId.MAX_MAGICKA, 2000.0, "drink_buff_active") in [row[:3] for row in bright]
    assert (StatId.MAX_STAMINA, 2000.0, "drink_buff_active") in [row[:3] for row in bone]


def test_necropotence_and_shapeshifter_keep_state_conditions():
    necro = _rows(
        "(5 items) While you have a pet active, your Max Magicka is increased by 72-3132."
    )
    chain = _rows(
        "(1 item) Reduce the cost of your Transformation Ultimate and Werewolf abilities by 15%. "
        "While transformed, increase your Maximum Health, Stamina, and Magicka by 1707."
    )

    assert [row[:3] for row in necro] == [
        (StatId.MAX_MAGICKA, 3132.0, "pet_active")
    ]
    assert set(row[:3] for row in chain) == {
        (StatId.MAX_HEALTH, 1707.0, "transformed"),
        (StatId.MAX_STAMINA, 1707.0, "transformed"),
        (StatId.MAX_MAGICKA, 1707.0, "transformed"),
    }


def test_armor_master_preserves_percentage_semantics():
    rows = _rows(
        "(5 items) While you have an Armor ability slotted, your Max Health is increased by 5%. "
        "When you use an Armor ability while in combat, your Physical and Spell Resistance is "
        "increased by 138-5940 for 10 seconds."
    )
    assert rows == [
        (
            StatId.MAX_HEALTH,
            5.0,
            "armor_ability_slotted",
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        )
    ]


def test_death_dealers_fete_maps_explicit_maximum_stack_state():
    rows = _rows(
        "(1 item) Gain a persistent stack of Escalating Fete every 2 seconds you are in combat, "
        "up to 30 stacks max. Each stack of Escalating Fete increases your Maximum Stamina, "
        "Health, and Magicka by 88. You lose a stack of Escalating Fete every 4 seconds you are "
        "out of combat."
    )

    assert set(row[:3] for row in rows) == {
        (StatId.MAX_HEALTH, 2640.0, "escalating_fete_stacks:30"),
        (StatId.MAX_MAGICKA, 2640.0, "escalating_fete_stacks:30"),
        (StatId.MAX_STAMINA, 2640.0, "escalating_fete_stacks:30"),
    }


def test_prowlers_talisman_maps_only_resource_stack_branch():
    rows = _rows(
        "(1 item) While Battle Spirit is inactive, bracing while crouching turns you invisible for 10 seconds. "
        "This can occur once every 45 seconds. Increase your chances of successfully Pickpocketing by 5%. "
        "On dealing Critical Damage, increase your Max Magicka and Max Stamina for 10 seconds, up to 1900 at 10 stacks. "
        "On dealing non-Critical Damage, increase your Health, Magicka, and Stamina Recovery for 10 seconds, up to 160 at 10 stacks. "
        "Either effect can occur up to once every 1 second. Talisman upgrades: 0"
    )

    assert set(row[:3] for row in rows) == {
        (StatId.MAX_MAGICKA, 1900.0, "prowlers_talisman_critical_stacks:10"),
        (StatId.MAX_STAMINA, 1900.0, "prowlers_talisman_critical_stacks:10"),
    }


def test_thrassian_stranglers_maps_negative_max_health_stack_state():
    rows = _rows(
        "(1 item) Killing an enemy grants you a stack of Sload's Call for 1 hour, up to a maximum of 50 stacks. "
        "Each stack increases your Weapon and Spell Damage by 23, reduces your Maximum Health by120, and reduces "
        "effectiveness of your damage shields by 1%. Sload's Call is lost if you remove Thrassian Stranglers, "
        "go invisible, or crouch."
    )

    assert rows == [
        (
            StatId.MAX_HEALTH,
            -6000.0,
            "sloads_call_stacks:50",
            EffectOperation.ADD,
            EffectUnit.FLAT,
        )
    ]
