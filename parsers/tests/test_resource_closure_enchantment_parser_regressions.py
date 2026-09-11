from parsers.jewelry_glyph_parser import JewelryGlyphParser
from parsers.weapon_enchantment_parser import WeaponEnchantmentParser


def test_jewelry_parser_accepts_flame_resistance_wording():
    effects = JewelryGlyphParser._parse_effects("Adds 1800 Flame Resistance.")

    assert len(effects) == 1
    assert effects[0]["effect_type"] == "flame_resistance"


def test_weapon_parser_maps_oblivion_damage_and_target_max_health_scaling():
    effects = WeaponEnchantmentParser._parse_effects(
        "Oblivion Damage based on a portion of the enemy's Max Health.\n"
        "Deals 4875 Oblivion Damage."
    )

    damage = [row for row in effects if row["effect_type"] == "damage"]
    assert len(damage) == 1
    assert damage[0]["damage_type"] == "oblivion"
    assert damage[0]["scaling_type"] == "target_max_health"
