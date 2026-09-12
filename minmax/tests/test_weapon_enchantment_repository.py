from pathlib import Path

import minmax.weapon_enchantment_repository as weapon_enchantment_module
from minmax.effects import EffectUnit
from minmax.weapon_enchantment_repository import (
    WeaponEnchantmentRepository,
)


DB_PATH = Path("data/eso.db")


def test_frost_enchantment():
    repository = WeaponEnchantmentRepository(DB_PATH)

    effects = repository.get_effects(5365)

    assert len(effects) == 1

    effect = effects[0]

    assert effect.effect_type == "damage"
    assert effect.value == 2534
    assert effect.damage_type == "frost"
    assert effect.unit == EffectUnit.FLAT
    assert effect.duration_value is None


def test_crushing_enchantment():
    repository = WeaponEnchantmentRepository(DB_PATH)

    effects = repository.get_effects(26845)

    assert len(effects) == 1

    effect = effects[0]

    assert effect.effect_type == (
        "physical_spell_resistance_reduction"
    )
    assert effect.value == 1622
    assert effect.target == "target"
    assert effect.duration_value == 5
    assert effect.duration_unit == "seconds"


def test_absorb_health_has_two_effects():
    repository = WeaponEnchantmentRepository(DB_PATH)

    effects = repository.get_effects(43573)

    assert len(effects) == 2

    damage = next(
        effect
        for effect in effects
        if effect.effect_type == "damage"
    )

    restore = next(
        effect
        for effect in effects
        if effect.effect_type == "health_restore"
    )

    assert damage.value == 1900
    assert damage.damage_type == "magic"

    assert restore.value == 861
    assert restore.damage_type is None


def test_weapon_enchantment_preserves_scaling_type():
    repository = WeaponEnchantmentRepository(DB_PATH)

    effects = repository.get_effects(5365)

    assert len(effects) == 1
    assert effects[0].scaling_type is None


def test_weapon_enchantment_effects_are_cached_and_returned_as_copies(monkeypatch):
    original_connect = weapon_enchantment_module.sqlite3.connect
    connect_count = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(weapon_enchantment_module.sqlite3, "connect", counting_connect)
    repository = WeaponEnchantmentRepository(DB_PATH)

    first = repository.get_effects(5365)
    second = repository.get_effects(5365)

    assert first == second
    assert first is not second
    assert connect_count == 1

    first.clear()
    assert repository.get_effects(5365) == second
    assert connect_count == 1


def test_weapon_enchantment_lookup_caches_are_instance_scoped(monkeypatch):
    original_connect = weapon_enchantment_module.sqlite3.connect
    connect_count = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(weapon_enchantment_module.sqlite3, "connect", counting_connect)
    repository = WeaponEnchantmentRepository(DB_PATH)

    first_items = repository.list_items()
    second_items = repository.list_items()
    first_label = repository.find_item_ids_by_label(" Crushing ")
    second_label = repository.find_item_ids_by_label("crushing")
    first_description = repository.get_description(5365)
    second_description = repository.get_description(5365)

    assert first_items == second_items
    assert first_label == second_label
    assert first_description == second_description
    assert connect_count == 3

    fresh_repository = WeaponEnchantmentRepository(DB_PATH)
    assert fresh_repository.list_items() == first_items
    assert connect_count == 4
