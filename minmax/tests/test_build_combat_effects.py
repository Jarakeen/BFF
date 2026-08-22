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
    
def test_damage_modifiers_are_separated_from_damage():
    effects = BuildCombatEffects(
        effects=(
            CombatEffect(
                effect_type="damage",
                value=1000,
                source="Damage",
                unit=EffectUnit.FLAT,
            ),
            CombatEffect(
                effect_type="flame_damage_done",
                value=0.05,
                source="Flame Modifier",
                unit=EffectUnit.PERCENT,
            ),
            CombatEffect(
                effect_type="direct_damage_done",
                value=0.10,
                source="Direct Modifier",
                unit=EffectUnit.PERCENT,
            ),
        )
    )

    assert len(effects.damage) == 1
    assert effects.damage[0].effect_type == "damage"

    assert len(effects.damage_modifiers) == 2
    assert {
        effect.effect_type
        for effect in effects.damage_modifiers
    } == {
        "flame_damage_done",
        "direct_damage_done",
    }


def test_healing_modifiers_are_separated_from_healing():
    effects = BuildCombatEffects(
        effects=(
            CombatEffect(
                effect_type="health_restore",
                value=1000,
                source="Healing",
                unit=EffectUnit.FLAT,
            ),
            CombatEffect(
                effect_type="healing_done",
                value=0.10,
                source="Healing Modifier",
                unit=EffectUnit.PERCENT,
            ),
        )
    )

    assert len(effects.healing) == 1
    assert effects.healing[0].effect_type == "health_restore"

    assert len(effects.healing_modifiers) == 1
    assert effects.healing_modifiers[0].effect_type == "healing_done"