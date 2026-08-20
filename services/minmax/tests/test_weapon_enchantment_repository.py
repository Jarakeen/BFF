from pathlib import Path

from services.minmax.effects import EffectUnit
from services.minmax.weapon_enchantment_repository import (
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