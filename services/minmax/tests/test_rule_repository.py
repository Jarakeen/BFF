from pathlib import Path

from services.minmax.rule_repository import RuleRepository


DB_PATH = Path("data/eso.db")


def test_infused_legendary_weapon():
    repository = RuleRepository(DB_PATH)

    effect = repository.get_infused_effect(
        gear_type="Weapon",
        quality="Legendary",
    )

    assert effect.value == 30
    assert effect.unit.value == "percent"


def test_infused_legendary_armor():
    repository = RuleRepository(DB_PATH)

    effect = repository.get_infused_effect(
        gear_type="Armor",
        quality="Legendary",
    )

    assert effect.value == 25


def test_infused_legendary_jewelry():
    repository = RuleRepository(DB_PATH)

    effect = repository.get_infused_effect(
        gear_type="Jewelry",
        quality="Legendary",
    )

    assert effect.value == 60

def test_potent_nirncrux_does_not_return_as_enchantment_rule():
    repository = RuleRepository(DB_PATH)

    effects = repository.get_weapon_enchantment_rules(
        "Potent Nirncrux"
    )

    assert effects == []        