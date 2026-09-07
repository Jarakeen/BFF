from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_sets import GearSetBonus
from minmax.effects import EffectOperation, EffectUnit
from minmax.stat_ids import StatId


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


def test_singular_one_item_prefix_is_stripped():
    effects = GearSetEffectResolver().resolve(
        bonus("(1 item) Adds 3-129 Magicka Recovery", piece_count=1)
    )
    assert stats(effects) == [(StatId.MAGICKA_RECOVERY, 129.0)]


def test_perfected_items_prefix_is_stripped():
    effects = GearSetEffectResolver().resolve(
        bonus("(5 perfected items) Adds 15-657 Critical Chance", piece_count=5)
    )
    assert stats(effects) == [(StatId.CRITICAL_CHANCE, 657.0)]


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


def test_ability_specific_bonus_preserves_scope_condition():
    effects = GearSetEffectResolver().resolve(
        bonus("(5 items) Adds 9-400 Weapon and Spell Damage to your Flame Damage abilities.")
    )
    assert [(effect.stat, effect.value, effect.condition) for effect in effects] == [
        (StatId.WEAPON_DAMAGE, 400.0, "ability_scope:flame_damage"),
        (StatId.SPELL_DAMAGE, 400.0, "ability_scope:flame_damage"),
    ]


def test_resolves_archers_mind_conditional_bonus():
    effects = GearSetEffectResolver().resolve(
        bonus(
            "(5 items) Increases your Critical Damage and Healing by 8%. "
            "Increases your Critical Damage and Healing by an additional 16% "
            "when you are Sneaking or Invisible."
        )
    )

    assert [
        (
            effect.stat,
            effect.operation,
            effect.value,
            effect.condition,
        )
        for effect in effects
    ] == [
        (
            StatId.CRITICAL_DAMAGE,
            EffectOperation.ADD_PERCENT,
            8.0,
            None,
        ),
        (
            StatId.HEALING_DONE,
            EffectOperation.ADD_PERCENT,
            8.0,
            None,
        ),
        (
            StatId.CRITICAL_DAMAGE,
            EffectOperation.ADD_PERCENT,
            16.0,
            "sneaking_or_invisible",
        ),
        (
            StatId.HEALING_DONE,
            EffectOperation.ADD_PERCENT,
            16.0,
            "sneaking_or_invisible",
        ),
    ]


def test_damage_shield_condition_preserves_health_recovery_requirement():
    effects = GearSetEffectResolver().resolve(
        bonus(
            "(5 items) While you have a damage shield on you, your Health Recovery "
            "is increased by 25-1106."
        )
    )
    assert [(effect.stat, effect.value, effect.condition) for effect in effects] == [
        (StatId.HEALTH_RECOVERY, 1106.0, "damage_shield_active")
    ]


def test_destruction_staff_condition_preserves_equipment_requirement():
    effects = GearSetEffectResolver().resolve(
        bonus(
            "(5 items) While you have a Destruction Staff equipped, your Max Magicka "
            "is increased by 66-2840."
        )
    )
    assert [(effect.stat, effect.value, effect.condition) for effect in effects] == [
        (StatId.MAX_MAGICKA, 2840.0, "destruction_staff_equipped")
    ]


def test_peace_and_serenity_preserves_mutually_exclusive_movement_states():
    effects = GearSetEffectResolver().resolve(
        bonus(
            "(5 items) While you are standing still, you gain 10-465 Weapon and Spell Damage. "
            "While you are moving, you gain 4-203 Health, Magicka, and Stamina Recovery."
        )
    )
    assert [(effect.stat, effect.value, effect.condition) for effect in effects] == [
        (StatId.WEAPON_DAMAGE, 465.0, "standing_still"),
        (StatId.SPELL_DAMAGE, 465.0, "standing_still"),
        (StatId.HEALTH_RECOVERY, 203.0, "moving"),
        (StatId.MAGICKA_RECOVERY, 203.0, "moving"),
        (StatId.STAMINA_RECOVERY, 203.0, "moving"),
    ]


def test_telvanni_enforcer_preserves_bracing_state_split():
    effects = GearSetEffectResolver().resolve(
        bonus(
            "(5 items) While Bracing, increase your Magicka Recovery by 369. "
            "While you are not Bracing, increase your Stamina Recovery by 369."
        )
    )
    assert [(effect.stat, effect.value, effect.condition) for effect in effects] == [
        (StatId.MAGICKA_RECOVERY, 369.0, "bracing"),
        (StatId.STAMINA_RECOVERY, 369.0, "not_bracing"),
    ]


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
