from services.minmax.effects import EffectUnit
from services.minmax.rule_effects import RuleEffect


def test_infused_rule_effect():
    effect = RuleEffect(
        rule_type="enchantment_effect",
        value=30,
        source="Infused",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
        gear_type="Weapon",
        quality="Legendary",
    )

    assert effect.rule_type == "enchantment_effect"
    assert effect.value == 30
    assert effect.unit == EffectUnit.PERCENT
    assert effect.gear_type == "Weapon"
    assert effect.quality == "Legendary"


def test_jade_enchantment_effect_rule():
    effect = RuleEffect(
        rule_type="weapon_enchantment_effect",
        value=10,
        source="Jade",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
    )

    assert effect.rule_type == "weapon_enchantment_effect"
    assert effect.value == 10
    assert effect.target_system == "weapon_enchantment"


def test_harmony_scaling_rule():
    effect = RuleEffect(
        rule_type="synergy_resource_restore",
        value=868,
        source="Harmony",
        unit=EffectUnit.FLAT,
        material_name="Platinum",
        quality="Legendary",
        item_level=150,
    )

    assert effect.rule_type == "synergy_resource_restore"
    assert effect.value == 868
    assert effect.material_name == "Platinum"
    assert effect.quality == "Legendary"
    assert effect.item_level == 150