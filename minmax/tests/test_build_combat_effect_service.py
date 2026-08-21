from pathlib import Path
import pytest


from minmax.build import Build
from minmax.build_combat_effect_service import (
    BuildCombatEffectService,
)
from minmax.rule_repository import RuleRepository
from minmax.weapon_enchantment_effect_service import (
    WeaponEnchantmentEffectService,
)
from minmax.weapon_enchantment_repository import (
    WeaponEnchantmentRepository,
)


DB_PATH = Path("data/eso.db")

FROST_ENCHANTMENT_ID = 5365
ABSORB_HEALTH_ENCHANTMENT_ID = 43573


def service() -> BuildCombatEffectService:
    enchantment_repository = WeaponEnchantmentRepository(DB_PATH)
    rule_repository = RuleRepository(DB_PATH)

    weapon_service = WeaponEnchantmentEffectService(
        enchantment_repository=enchantment_repository,
        rule_repository=rule_repository,
    )

    return BuildCombatEffectService(
        weapon_enchantment_service=weapon_service,
    )


def test_empty_build_has_no_combat_effects():
    build = Build()

    effects = service().resolve_effects(build)

    assert effects == []


def test_weapon_without_enchantment_has_no_combat_effects():
    build = Build()

    build.add_weapon(
        trait="Infused",
        quality="Legendary",
    )

    effects = service().resolve_effects(build)

    assert effects == []


def test_frost_enchantment_resolves_from_build_weapon():
    build = Build()

    build.add_weapon(
        enchantment_item_id=FROST_ENCHANTMENT_ID,
    )

    effects = service().resolve_effects(build)

    assert len(effects) == 1

    effect = effects[0]

    assert effect.effect_type == "damage"
    assert effect.value == 2534
    assert effect.damage_type == "frost"


def test_infused_weapon_modifies_enchantment():
    build = Build()

    build.add_weapon(
        enchantment_item_id=FROST_ENCHANTMENT_ID,
        trait="Infused",
        quality="Legendary",
    )

    effects = service().resolve_effects(build)

    assert len(effects) == 1
    assert effects[0].value == pytest.approx(3294.2)


def test_jade_weapon_modifies_enchantment():
    build = Build()

    build.add_weapon(
        enchantment_item_id=FROST_ENCHANTMENT_ID,
        trait="Jade",
        quality="Legendary",
    )

    effects = service().resolve_effects(build)

    assert len(effects) == 1
    assert effects[0].value == pytest.approx(2787.4)


def test_multiple_weapons_contribute_effects():
    build = Build()

    build.add_weapon(
        enchantment_item_id=FROST_ENCHANTMENT_ID,
    )

    build.add_weapon(
        enchantment_item_id=ABSORB_HEALTH_ENCHANTMENT_ID,
    )

    effects = service().resolve_effects(build)

    assert len(effects) == 3

    damage_effects = [
        effect
        for effect in effects
        if effect.effect_type == "damage"
    ]

    restore_effects = [
        effect
        for effect in effects
        if effect.effect_type == "health_restore"
    ]

    assert len(damage_effects) == 2
    assert len(restore_effects) == 1


def test_weapon_effect_preserves_metadata():
    build = Build()

    # Crushing enchantment.
    build.add_weapon(
        enchantment_item_id=26845,
    )

    effects = service().resolve_effects(build)

    assert len(effects) == 1

    effect = effects[0]

    assert effect.effect_type == (
        "physical_spell_resistance_reduction"
    )
    assert effect.target == "target"
    assert effect.duration_value == 5
    assert effect.duration_unit == "seconds"

def test_build_weapon_can_resolve_minimum_enchantment_value():
    build = Build()

    build.add_weapon(
        enchantment_item_id=FROST_ENCHANTMENT_ID,
    )

    effects = service().resolve_effects(
        build,
        use_max_value=False,
    )

    assert len(effects) == 1

    effect = effects[0]

    assert effect.effect_type == "damage"
    assert effect.value == 107
    assert effect.damage_type == "frost"    