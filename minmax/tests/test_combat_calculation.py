from minmax.combat_calculation import (
    calculate_combat_effect,
)
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit


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

def test_no_duration_has_full_uptime():
    effect = CombatEffect(
        effect_type="damage",
        value=2534,
        source="Glyph of Frost",
        unit=EffectUnit.FLAT,
    )

    result = calculate_combat_effect(
        effect,
        fight_duration=60,
    )

    assert result.uptime == 1.0


def test_duration_is_converted_to_uptime():
    effect = CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=1622,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target="target",
        duration_value=5,
        duration_unit="seconds",
    )

    result = calculate_combat_effect(
        effect,
        fight_duration=60,
    )

    assert result.uptime == 5 / 60


def test_duration_cannot_exceed_full_uptime():
    effect = CombatEffect(
        effect_type="damage",
        value=100,
        source="Long Effect",
        unit=EffectUnit.FLAT,
        duration_value=120,
        duration_unit="seconds",
    )

    result = calculate_combat_effect(
        effect,
        fight_duration=60,
    )

    assert result.uptime == 1.0


def test_unknown_fight_duration_preserves_full_effect_uptime():
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

    assert result.uptime == 1.0


def test_calculation_preserves_scaling_type():
    effect = CombatEffect(
        effect_type="damage",
        value=100,
        source="Scaled Effect",
        unit=EffectUnit.FLAT,
        scaling_type="weapon_damage",
    )

    result = calculate_combat_effect(effect)

    assert result.scaling_type == "weapon_damage"    

def test_no_cooldown_preserves_duration_based_uptime():
    effect = CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=1622,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target="target",
        duration_value=5,
        duration_unit="seconds",
    )

    result = calculate_combat_effect(
        effect,
        fight_duration=60,
    )

    assert result.uptime == 5 / 60
    assert result.maximum_uptime == 5 / 60
    assert result.expected_uptime == 5 / 60
    assert result.cooldown is None


def test_cooldown_produces_maximum_uptime():
    effect = CombatEffect(
        effect_type="damage",
        value=1000,
        source="Temporary Effect",
        unit=EffectUnit.FLAT,
        duration_value=5,
        duration_unit="seconds",
    )

    result = calculate_combat_effect(
        effect,
        cooldown=10,
    )

    assert result.cooldown == 10
    assert result.maximum_uptime == 0.5
    assert result.expected_uptime == 0.5
    assert result.uptime == 0.5


def test_activation_chance_reduces_expected_uptime():
    effect = CombatEffect(
        effect_type="damage",
        value=1000,
        source="Proc Effect",
        unit=EffectUnit.FLAT,
        duration_value=5,
        duration_unit="seconds",
    )

    result = calculate_combat_effect(
        effect,
        cooldown=10,
        activation_chance=0.5,
    )

    assert result.maximum_uptime == 0.5
    assert result.expected_uptime == 0.25
    assert result.uptime == 0.25


def test_zero_activation_chance_produces_zero_expected_uptime():
    effect = CombatEffect(
        effect_type="damage",
        value=1000,
        source="Proc Effect",
        unit=EffectUnit.FLAT,
        duration_value=5,
        duration_unit="seconds",
    )

    result = calculate_combat_effect(
        effect,
        cooldown=10,
        activation_chance=0.0,
    )

    assert result.maximum_uptime == 0.5
    assert result.expected_uptime == 0.0
    assert result.uptime == 0.0


def test_calculation_preserves_raw_effect_metadata():
    effect = CombatEffect(
        effect_type="damage",
        value=1000,
        source="Scaled Effect",
        unit=EffectUnit.FLAT,
        damage_type="frost",
        target="target",
        duration_value=5,
        duration_unit="seconds",
        scaling_type="weapon_damage",
    )

    result = calculate_combat_effect(
        effect,
        cooldown=10,
    )

    assert effect.value == 1000
    assert effect.duration_value == 5
    assert effect.scaling_type == "weapon_damage"

    assert result.value == 1000
    assert result.damage_type == "frost"
    assert result.target == "target"
    assert result.duration_value == 5
    assert result.scaling_type == "weapon_damage"    