from minmax.gear_set_resource_condition_resolver import GearSetResourceConditionResolver
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId


def _bonus(description: str) -> GearSetBonus:
    return GearSetBonus(id=1, set_id=1, piece_count=5, description=description)


def _rows(description: str):
    effects = GearSetResourceConditionResolver().resolve(_bonus(description))
    return [(effect.stat, effect.value, effect.condition) for effect in effects]


def test_green_pact_food_condition_maps_health_and_recovery() -> None:
    assert _rows(
        "(5 items) While you have a food buff active, your Max Health is increased by "
        "58-2500 and Health Recovery by 8-356."
    ) == [
        (StatId.MAX_HEALTH, 2500.0, "food_buff_active"),
        (StatId.HEALTH_RECOVERY, 356.0, "food_buff_active"),
    ]


def test_bright_throat_drink_condition_maps_magicka_and_recovery() -> None:
    assert _rows(
        "(5 items) While you have a drink buff active, your Max Magicka is increased by "
        "46-2000 and Magicka Recovery by 3-133."
    ) == [
        (StatId.MAX_MAGICKA, 2000.0, "drink_buff_active"),
        (StatId.MAGICKA_RECOVERY, 133.0, "drink_buff_active"),
    ]


def test_bone_pirate_drink_condition_maps_stamina_and_recovery() -> None:
    assert _rows(
        "(5 items) While you have a drink buff active, your Max Stamina is increased by "
        "46-2000 and Stamina Recovery by 3-133."
    ) == [
        (StatId.MAX_STAMINA, 2000.0, "drink_buff_active"),
        (StatId.STAMINA_RECOVERY, 133.0, "drink_buff_active"),
    ]


def test_necropotence_pet_condition_maps_max_magicka() -> None:
    assert _rows(
        "(5 items) While you have a pet active, your Max Magicka is increased by 72-3132."
    ) == [
        (StatId.MAX_MAGICKA, 3132.0, "pet_active"),
    ]


def test_ebon_self_group_aura_maps_max_health_for_wearer() -> None:
    assert _rows(
        "(5 items) Increases Max Health by 23-1000 for you and up to 11 other group members "
        "within 28 meters of you. This bonus persists through death."
    ) == [
        (StatId.MAX_HEALTH, 1000.0, None),
    ]


def test_xoryn_self_group_aura_maps_both_resources_for_wearer() -> None:
    assert _rows(
        "(5 items) Increases Max Magicka and Max Stamina by 1667 for you and up to 11 other "
        "group members within 28 meters of you. This bonus persists through death."
    ) == [
        (StatId.MAX_MAGICKA, 1667.0, None),
        (StatId.MAX_STAMINA, 1667.0, None),
    ]


def test_unreviewed_triggered_resource_proc_stays_unresolved_here() -> None:
    assert _rows(
        "(5 items) When you take damage, restore 2000 Magicka. This effect can occur once every 5 seconds."
    ) == []
