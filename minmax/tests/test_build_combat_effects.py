from minmax.build_combat_effects import BuildCombatEffects
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit


def test_build_combat_effects_starts_with_empty_effects():
    result = BuildCombatEffects(effects=())

    assert result.effects == ()
    assert result.damage == ()
    assert result.healing == ()
    assert result.target_debuffs == ()


def test_build_combat_effects_classifies_damage():
    damage = CombatEffect(
        effect_type="damage",
        value=2534,
        source="Glyph of Frost",
        unit=EffectUnit.FLAT,
        damage_type="frost",
    )

    result = BuildCombatEffects(
        effects=(damage,),
    )

    assert result.effects == (damage,)
    assert result.damage == (damage,)
    assert result.healing == ()
    assert result.target_debuffs == ()


def test_build_combat_effects_classifies_healing():
    healing = CombatEffect(
        effect_type="health_restore",
        value=861,
        source="Glyph of Absorb Health",
        unit=EffectUnit.FLAT,
    )

    result = BuildCombatEffects(
        effects=(healing,),
    )

    assert result.healing == (healing,)
    assert result.damage == ()


def test_build_combat_effects_classifies_target_debuff():
    debuff = CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=1622,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target="target",
        duration_value=5,
        duration_unit="seconds",
    )

    result = BuildCombatEffects(
        effects=(debuff,),
    )

    assert result.target_debuffs == (debuff,)
    assert result.damage == ()
    assert result.healing == ()


def test_build_combat_effects_preserves_all_effects():
    damage = CombatEffect(
        effect_type="damage",
        value=2534,
        source="Glyph of Frost",
        unit=EffectUnit.FLAT,
        damage_type="frost",
    )

    healing = CombatEffect(
        effect_type="health_restore",
        value=861,
        source="Glyph of Absorb Health",
        unit=EffectUnit.FLAT,
    )

    debuff = CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=1622,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target="target",
        duration_value=5,
        duration_unit="seconds",
    )

    result = BuildCombatEffects(
        effects=(damage, healing, debuff),
    )

    assert result.effects == (
        damage,
        healing,
        debuff,
    )

    assert result.damage == (damage,)
    assert result.healing == (healing,)
    assert result.target_debuffs == (debuff,)