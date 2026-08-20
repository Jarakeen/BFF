from services.minmax.combat_effect_classifier import (
    CombatEffectCategory,
    classify_combat_effect,
)
from services.minmax.combat_effects import CombatEffect
from services.minmax.effects import EffectUnit


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