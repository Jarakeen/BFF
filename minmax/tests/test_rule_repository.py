from pathlib import Path

import minmax.rule_repository as rule_repository_module
from minmax.rule_repository import RuleRepository


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


def test_status_effect_chance_rule_is_resolved_semantically_not_by_material_name():
    repository = RuleRepository(DB_PATH)

    rules = repository.get_weapon_trait_rules_by_effect_type("status_effect_chance")

    assert len(rules) == 1
    assert rules[0].rule_type == "status_effect_chance"
    assert rules[0].unit.value == "percent"
    assert rules[0].value > 0
    assert rules[0].source


def test_rule_repository_reuses_instance_scoped_reference_queries(monkeypatch):
    original_connect = rule_repository_module.sqlite3.connect
    connect_calls = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_calls
        connect_calls += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(rule_repository_module.sqlite3, "connect", counting_connect)

    repository = RuleRepository(DB_PATH)

    trait_names = repository.list_weapon_trait_names()
    assert trait_names
    assert connect_calls == 1
    assert repository.list_weapon_trait_names() == trait_names
    assert connect_calls == 1

    infused = repository.get_infused_effect(
        gear_type="Weapon",
        quality="Legendary",
    )
    assert connect_calls == 2
    assert repository.get_infused_effect(
        gear_type="Weapon",
        quality="Legendary",
    ) == infused
    assert connect_calls == 2

    rules = repository.get_weapon_trait_rules("Potent Nirncrux")
    assert connect_calls == 3
    assert repository.get_weapon_trait_rules("Potent Nirncrux") == rules
    assert connect_calls == 3

    status_rules = repository.get_weapon_trait_rules_by_effect_type("status_effect_chance")
    assert status_rules
    assert connect_calls == 4
    assert repository.get_weapon_trait_rules_by_effect_type("status_effect_chance") == status_rules
    assert connect_calls == 4

    fresh_repository = RuleRepository(DB_PATH)
    assert fresh_repository.list_weapon_trait_names() == trait_names
    assert connect_calls == 5
