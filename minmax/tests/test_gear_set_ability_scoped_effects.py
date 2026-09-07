from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId


def bonus(description: str, piece_count: int = 5) -> GearSetBonus:
    return GearSetBonus(
        id=1,
        set_id=1,
        piece_count=piece_count,
        description=description,
    )


def projection(description: str, piece_count: int = 5):
    return GearSetEffectResolver().resolve(
        bonus(description, piece_count=piece_count),
        use_max_value=True,
        source="Scoped set bonus",
    )


def test_flame_damage_ability_scope_is_preserved():
    effects = projection(
        "(5 items) Adds 9-400 Weapon and Spell Damage to your Flame Damage abilities."
    )

    assert [(effect.stat, effect.value, effect.condition) for effect in effects] == [
        (StatId.WEAPON_DAMAGE, 400.0, "ability_scope:flame_damage"),
        (StatId.SPELL_DAMAGE, 400.0, "ability_scope:flame_damage"),
    ]


def test_weapon_skill_scope_is_preserved():
    effects = projection(
        "(5 items) Adds 13-600 Weapon and Spell Damage to your Dual Wield abilities."
    )

    assert [(effect.stat, effect.value, effect.condition) for effect in effects] == [
        (StatId.WEAPON_DAMAGE, 600.0, "ability_scope:dual_wield"),
        (StatId.SPELL_DAMAGE, 600.0, "ability_scope:dual_wield"),
    ]


def test_ranged_direct_damage_three_piece_scope_is_preserved():
    effects = projection(
        "(3 items) Adds 7-325 Weapon and Spell Damage to your ranged direct damage abilities.",
        piece_count=3,
    )

    assert [(effect.stat, effect.value, effect.condition) for effect in effects] == [
        (StatId.WEAPON_DAMAGE, 325.0, "ability_scope:ranged_direct_damage"),
        (StatId.SPELL_DAMAGE, 325.0, "ability_scope:ranged_direct_damage"),
    ]


def test_scoped_bonus_can_use_minimum_range_value():
    effects = GearSetEffectResolver().resolve(
        bonus("(5 items) Adds 13-600 Weapon and Spell Damage to your Two Handed abilities."),
        use_max_value=False,
        source="Scoped set bonus",
    )

    assert [(effect.stat, effect.value, effect.condition) for effect in effects] == [
        (StatId.WEAPON_DAMAGE, 13.0, "ability_scope:two_handed"),
        (StatId.SPELL_DAMAGE, 13.0, "ability_scope:two_handed"),
    ]


def test_triggered_or_tradeoff_text_is_not_partially_laundered_as_scope():
    effects = projection(
        "(5 items) Adds 13-600 Weapon and Spell Damage to your Dual Wield abilities. "
        "When you deal damage, restore 100 Stamina."
    )

    assert effects == []
