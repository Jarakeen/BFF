from services.minmax.combat_context import CombatContext
from services.minmax.combat_effect_evaluator import CombatEffectEvaluator
from services.minmax.combat_effects import CombatEffect
from services.minmax.effects import EffectUnit


def test_effect_without_target_is_applicable():
    effect = CombatEffect(
        effect_type="damage",
        value=2534,
        source="Glyph of Frost",
        unit=EffectUnit.FLAT,
    )

    context = CombatContext()

    assert CombatEffectEvaluator().is_applicable(
        effect,
        context,
    )


def test_effect_matching_target_is_applicable():
    effect = CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=1622,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target="target",
    )

    context = CombatContext(
        target="target",
    )

    assert CombatEffectEvaluator().is_applicable(
        effect,
        context,
    )


def test_effect_with_different_target_is_not_applicable():
    effect = CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=1622,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target="target",
    )

    context = CombatContext(
        target="self",
    )

    assert not CombatEffectEvaluator().is_applicable(
        effect,
        context,
    )


def test_conditional_effect_requires_active_condition():
    effect = CombatEffect(
        effect_type="damage",
        value=100,
        source="Conditional Effect",
        unit=EffectUnit.FLAT,
        condition="enemy_under_50_health",
    )

    context = CombatContext()

    assert not CombatEffectEvaluator().is_applicable(
        effect,
        context,
    )


def test_active_condition_makes_effect_applicable():
    effect = CombatEffect(
        effect_type="damage",
        value=100,
        source="Conditional Effect",
        unit=EffectUnit.FLAT,
        condition="enemy_under_50_health",
    )

    context = CombatContext(
        active_conditions={"enemy_under_50_health"},
    )

    assert CombatEffectEvaluator().is_applicable(
        effect,
        context,
    )


def test_target_and_condition_both_must_match():
    effect = CombatEffect(
        effect_type="damage",
        value=100,
        source="Conditional Effect",
        unit=EffectUnit.FLAT,
        target="target",
        condition="enemy_under_50_health",
    )

    matching_context = CombatContext(
        target="target",
        active_conditions={"enemy_under_50_health"},
    )

    wrong_target = CombatContext(
        target="self",
        active_conditions={"enemy_under_50_health"},
    )

    missing_condition = CombatContext(
        target="target",
    )

    evaluator = CombatEffectEvaluator()

    assert evaluator.is_applicable(
        effect,
        matching_context,
    )

    assert not evaluator.is_applicable(
        effect,
        wrong_target,
    )

    assert not evaluator.is_applicable(
        effect,
        missing_condition,
    )