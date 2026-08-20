from services.minmax.combat_calculation import (
    calculate_combat_effect,
)
from services.minmax.combat_effects import CombatEffect
from services.minmax.effects import EffectUnit


def test_damage_effect_preserves_value_and_type():
    effect = CombatEffect(
        effect_type="damage",
        value=2534,
        source="Glyph of Frost",
        unit=EffectUnit.FLAT,
        damage_type="frost",
    )

    result = calculate_combat_effect(effect)

    assert result.effect_type == "damage"
    assert result.value == 2534
    assert result.source == "Glyph of Frost"
    assert result.damage_type == "frost"


def test_target_effect_preserves_target():
    effect = CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=1622,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target="target",
        duration_value=5,
        duration_unit="seconds",
    )

    result = calculate_combat_effect(effect)

    assert result.effect_type == (
        "physical_spell_resistance_reduction"
    )
    assert result.value == 1622
    assert result.target == "target"


def test_duration_is_preserved():
    effect = CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=1622,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target="target",
        duration_value=5,
        duration_unit="seconds",
    )

    result = calculate_combat_effect(effect)

    assert result.duration_value == 5
    assert result.duration_unit == "seconds"


def test_health_restore_is_preserved():
    effect = CombatEffect(
        effect_type="health_restore",
        value=861,
        source="Glyph of Absorb Health",
        unit=EffectUnit.FLAT,
    )

    result = calculate_combat_effect(effect)

    assert result.effect_type == "health_restore"
    assert result.value == 861
    assert result.source == "Glyph of Absorb Health"
    