from services.minmax.gear_set_effect_resolver import GearSetEffectResolver
from services.minmax.gear_sets import GearSetBonus
from services.minmax.effects import EffectOperation, EffectUnit
from services.minmax.stat_ids import StatId


def bonus(description: str, piece_count: int = 2) -> GearSetBonus:
    return GearSetBonus(
        id=1,
        set_id=19,
        piece_count=piece_count,
        description=description,
    )


def stats(effects):
    return [(effect.stat, effect.value) for effect in effects]


def test_maximum_health_range_uses_max_by_default():
    effects = GearSetEffectResolver().resolve(
        bonus("(2 items) Adds 28-1206 Maximum Health")
    )
    assert stats(effects) == [(StatId.MAX_HEALTH, 1206.0)]


def test_range_can_use_min_value():
    effects = GearSetEffectResolver().resolve(
        bonus("(2 items) Adds 28-1206 Maximum Health"),
        use_max_value=False,
    )
    assert stats(effects) == [(StatId.MAX_HEALTH, 28.0)]


def test_eso_color_markup_is_stripped():
    effects = GearSetEffectResolver().resolve(
        bonus(
            "(5 items) When you take damage under "
            "|cffffff35|r% Health"
        )
    )
    assert effects == []


def test_weapon_and_spell_damage_creates_two_effects():
    effects = GearSetEffectResolver().resolve(
        bonus("(3 items) Adds 3-129 Weapon and Spell Damage")
    )
    assert stats(effects) == [
        (StatId.WEAPON_DAMAGE, 129.0),
        (StatId.SPELL_DAMAGE, 129.0),
    ]


def test_armor_creates_two_resistance_effects():
    effects = GearSetEffectResolver().resolve(
        bonus("(3 items) Adds 34-1487 Armor")
    )
    assert stats(effects) == [
        (StatId.PHYSICAL_RESISTANCE, 1487.0),
        (StatId.SPELL_RESISTANCE, 1487.0),
    ]


def test_offensive_penetration_creates_two_effects():
    effects = GearSetEffectResolver().resolve(
        bonus("(3 items) Adds 34-1487 Offensive Penetration")
    )
    assert stats(effects) == [
        (StatId.PHYSICAL_PENETRATION, 1487.0),
        (StatId.SPELL_PENETRATION, 1487.0),
    ]


def test_critical_chance_uses_new_stat():
    effects = GearSetEffectResolver().resolve(
        bonus("(3 items) Adds 15-657 Critical Chance")
    )
    assert stats(effects) == [(StatId.CRITICAL_CHANCE, 657.0)]


def test_critical_resistance_uses_new_stat():
    effects = GearSetEffectResolver().resolve(
        bonus("(3 items) Adds 34-1487 Critical Resistance")
    )
    assert stats(effects) == [(StatId.CRITICAL_RESISTANCE, 1487.0)]


def test_healing_done_percent():
    effects = GearSetEffectResolver().resolve(
        bonus("(5 items) Adds 5% Healing Done")
    )
    assert stats(effects) == [(StatId.HEALING_DONE, 5.0)]
    assert effects[0].operation == EffectOperation.ADD_PERCENT
    assert effects[0].unit == EffectUnit.PERCENT


def test_healing_taken_percent():
    effects = GearSetEffectResolver().resolve(
        bonus("(3 items) Adds 4% Healing Taken")
    )
    assert stats(effects) == [(StatId.HEALING_TAKEN, 4.0)]
    assert effects[0].operation == EffectOperation.ADD_PERCENT


def test_healing_received_phrase_maps_to_healing_taken():
    effects = GearSetEffectResolver().resolve(
        bonus("(5 items) Increases your healing received by 10%.")
    )
    assert stats(effects) == [(StatId.HEALING_TAKEN, 10.0)]
    assert effects[0].operation == EffectOperation.ADD_PERCENT


def test_rejects_ability_specific_bonus():
    effects = GearSetEffectResolver().resolve(
        bonus("(5 items) Adds 9-400 Weapon and Spell Damage to your Flame Damage abilities.")
    )
    assert effects == []


def test_rejects_conditional_bonus():
    effects = GearSetEffectResolver().resolve(
        bonus(
            "(5 items) Increases your Critical Damage and Healing by 8%. "
            "Increases your Critical Damage and Healing by an additional 16% "
            "when you are Sneaking or Invisible."
        )
    )
    assert effects == []


def test_rejects_tradeoff_bonus():
    effects = GearSetEffectResolver().resolve(
        bonus(
            "(5 items) Increases damage done by 16% but decreases "
            "Critical Damage done by 50%."
        )
    )
    assert effects == []


def test_rejects_triggered_bonus():
    effects = GearSetEffectResolver().resolve(
        bonus(
            "(5 items) When you take damage, you have a 25% chance "
            "to restore 46-2012 Magicka. This effect can occur once every 4 seconds."
        )
    )
    assert effects == []


def test_source_can_be_supplied_explicitly():
    effects = GearSetEffectResolver().resolve(
        bonus("(2 items) Adds 3-129 Magicka Recovery"),
        source="Vestments of the Warlock (2)",
    )
    assert effects[0].source == "Vestments of the Warlock (2)"
