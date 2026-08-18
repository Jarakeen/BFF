from services.minmax.combat_effects import CombatEffect
from services.minmax.effects import EffectUnit


def test_damage_combat_effect():
    effect = CombatEffect(
        effect_type="damage",
        value=2534,
        source="Glyph of Frost",
        unit=EffectUnit.FLAT,
        damage_type="frost",
    )

    assert effect.effect_type == "damage"
    assert effect.value == 2534
    assert effect.damage_type == "frost"
    assert effect.target is None


def test_temporary_resistance_reduction():
    effect = CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=1622,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target="target",
        duration_value=5,
        duration_unit="seconds",
    )

    assert effect.target == "target"
    assert effect.duration_value == 5
    assert effect.duration_unit == "seconds"