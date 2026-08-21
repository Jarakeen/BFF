from pathlib import Path

from minmax.rule_repository import RuleRepository


DB_PATH = Path("data/eso.db")


def test_jade_returns_weapon_enchantment_rules():
    repository = RuleRepository(DB_PATH)

    effects = repository.get_weapon_trait_rules("Jade")

    assert len(effects) == 2

    effect_types = {
        effect.rule_type
        for effect in effects
    }

    assert "weapon_enchantment_effect" in effect_types
    assert "enchantment_cooldown_reduction" in effect_types


def test_jade_enchantment_effect_value():
    repository = RuleRepository(DB_PATH)

    effects = repository.get_weapon_trait_rules("Jade")

    effect = next(
        effect
        for effect in effects
        if effect.rule_type == "weapon_enchantment_effect"
    )

    assert effect.value == 10
    assert effect.unit.value == "percent"


def test_jade_cooldown_reduction_value():
    repository = RuleRepository(DB_PATH)

    effects = repository.get_weapon_trait_rules("Jade")

    effect = next(
        effect
        for effect in effects
        if effect.rule_type == "enchantment_cooldown_reduction"
    )

    assert effect.value == 50
    assert effect.unit.value == "percent"