import pytest
from minmax.combat_effect_classifier import (
    CombatEffectCategory,
    classify_combat_effect,
)
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit


def test_damage_is_classified_as_damage():
    effect = CombatEffect(
        effect_type="damage",
        value=2534,
        source="Glyph of Frost",
        unit=EffectUnit.FLAT,
        damage_type="frost",
    )

    assert (
        classify_combat_effect(effect)
        == CombatEffectCategory.DAMAGE
    )


def test_health_restore_is_classified_as_healing():
    effect = CombatEffect(
        effect_type="health_restore",
        value=861,
        source="Glyph of Absorb Health",
        unit=EffectUnit.FLAT,
    )

    assert (
        classify_combat_effect(effect)
        == CombatEffectCategory.HEALING
    )


def test_resistance_reduction_is_target_debuff():
    effect = CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=1622,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target="target",
        duration_value=5,
        duration_unit="seconds",
    )

    assert (
        classify_combat_effect(effect)
        == CombatEffectCategory.TARGET_DEBUFF
    )


def test_unknown_effect_is_other():
    effect = CombatEffect(
        effect_type="future_effect",
        value=100,
        source="Future Effect",
        unit=EffectUnit.FLAT,
    )

    assert (
        classify_combat_effect(effect)
        == CombatEffectCategory.OTHER
    )
    
@pytest.mark.parametrize(
    "effect_type",
    [
        "damage_done",
        "direct_damage_done",
        "flame_damage_done",
        "single_target_damage_done",
        "damage_amplification",
    ],
)
def test_damage_modifier_effects_are_classified_as_damage_modifiers(
    effect_type,
):
    effect = CombatEffect(
        effect_type=effect_type,
        value=0.05,
        source="Test",
    )

    assert (
        classify_combat_effect(effect)
        == CombatEffectCategory.DAMAGE_MODIFIER
    )


def test_healing_done_is_a_healing_modifier():
    effect = CombatEffect(
        effect_type="healing_done",
        value=0.10,
        source="Test",
    )

    assert (
        classify_combat_effect(effect)
        == CombatEffectCategory.HEALING_MODIFIER
    )


def test_existing_damage_remains_damage():
    effect = CombatEffect(
        effect_type="damage",
        value=1000,
        source="Test",
    )

    assert classify_combat_effect(effect) == CombatEffectCategory.DAMAGE


def test_unknown_effect_remains_other():
    effect = CombatEffect(
        effect_type="future_effect",
        value=1.0,
        source="Test",
    )

    assert classify_combat_effect(effect) == CombatEffectCategory.OTHER    