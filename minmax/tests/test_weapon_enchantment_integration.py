from pathlib import Path

from minmax.combat_calculation import calculate_combat_effect
from minmax.combat_context import CombatContext
from minmax.combat_contribution import calculate_combat_contribution
from minmax.weapon_enchantment_effect_service import (
    WeaponEnchantmentEffectService,
)
from minmax.weapon_enchantment_repository import (
    WeaponEnchantmentRepository,
)
from minmax.rule_repository import RuleRepository


DB_PATH = Path("data/eso.db")

FROST_ENCHANTMENT_ID = 5365
CRUSHING_ENCHANTMENT_ID = 26845
ABSORB_HEALTH_ENCHANTMENT_ID = 43573


def service():
    return WeaponEnchantmentEffectService(
        enchantment_repository=WeaponEnchantmentRepository(DB_PATH),
        rule_repository=RuleRepository(DB_PATH),
    )


def resolve_effect_to_contribution(effect):
    result = calculate_combat_effect(effect)

    return calculate_combat_contribution(result)

def test_frost_enchantment_flows_into_damage_contribution():
    effects = service().resolve_effects(
        FROST_ENCHANTMENT_ID,
    )

    assert len(effects) == 1

    contribution = resolve_effect_to_contribution(effects[0])

    assert contribution.effect_type == "damage"
    assert contribution.effective_value == 2534
    assert contribution.source == "Glyph of Frost"


def test_crushing_enchantment_flows_into_target_debuff():
    effects = service().resolve_effects(
        CRUSHING_ENCHANTMENT_ID,
    )

    assert len(effects) == 1

    effect = effects[0]

    assert effect.effect_type == (
        "physical_spell_resistance_reduction"
    )
    assert effect.target == "target"
    assert effect.duration_value == 5
    assert effect.duration_unit == "seconds"

    contribution = resolve_effect_to_contribution(effect)

    assert (
        contribution.effect_type
        == "physical_spell_resistance_reduction"
    )
    assert contribution.effective_value == 1622
    assert contribution.source == "Glyph of Crushing"


def test_absorb_health_produces_separate_damage_and_healing_contributions():
    effects = service().resolve_effects(
        ABSORB_HEALTH_ENCHANTMENT_ID,
    )

    assert len(effects) == 2

    contributions = [
        resolve_effect_to_contribution(effect)
        for effect in effects
    ]

    damage = next(
        contribution
        for contribution in contributions
        if contribution.effect_type == "damage"
    )

    healing = next(
        contribution
        for contribution in contributions
        if contribution.effect_type == "health_restore"
    )

    assert damage.effective_value == 1900
    assert healing.effective_value == 861

    assert damage.source == "Glyph of Absorb Health"
    assert healing.source == "Glyph of Absorb Health"
    