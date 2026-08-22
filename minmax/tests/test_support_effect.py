import pytest

from minmax.effects import EffectUnit
from minmax.role import Role
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_effect_trigger import SupportEffectTrigger
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType


def test_simple_buff():
    """A simple self/ally buff, e.g. Major Brutality."""

    effect = SupportEffect(
        source="Major Brutality",
        name="Major Brutality",
        category=SupportEffectCategory.BUFF,
        effect_type="weapon_spell_damage",
        target_type=SupportTargetType.SELF,
        magnitude=20,
        unit=EffectUnit.PERCENT,
        duration=20,
    )

    assert effect.category == SupportEffectCategory.BUFF
    assert effect.target_type == SupportTargetType.SELF
    assert effect.magnitude == 20
    assert effect.unit == EffectUnit.PERCENT


def test_simple_debuff():
    """A simple debuff, e.g. Minor Vulnerability."""

    effect = SupportEffect(
        source="Minor Vulnerability",
        name="Minor Vulnerability",
        category=SupportEffectCategory.DEBUFF,
        effect_type="damage_taken",
        target_type=SupportTargetType.ENEMY,
        magnitude=5,
        unit=EffectUnit.PERCENT,
    )

    assert effect.category == SupportEffectCategory.DEBUFF
    assert effect.target_type == SupportTargetType.ENEMY


def test_target_enemy_debuff_contributes_to_group():
    """An enemy-targeted debuff should be considered a group contribution."""

    effect = SupportEffect(
        source="Crusher Enchant",
        name="Crusher",
        category=SupportEffectCategory.DEBUFF,
        effect_type="resistance_reduction",
        target_type=SupportTargetType.ENEMY,
        magnitude=2104,
        unit=EffectUnit.FLAT,
        resistance_reduction=2104,
    )

    assert effect.contributes_to_group() is True


def test_group_targeted_buff():
    """A group-wide buff, e.g. Major Courage from a Spell Power Cure set."""

    effect = SupportEffect(
        source="Spell Power Cure",
        name="Major Courage",
        category=SupportEffectCategory.BUFF,
        effect_type="weapon_spell_damage",
        target_type=SupportTargetType.GROUP,
        magnitude=430,
        unit=EffectUnit.FLAT,
        target_count=12,
        role_relevance=frozenset({Role.HEALER}),
    )

    assert effect.target_type == SupportTargetType.GROUP
    assert effect.target_count == 12
    assert Role.HEALER in effect.role_relevance


def test_status_effect_chilled():
    """A status effect such as Chilled."""

    effect = SupportEffect(
        source="Frost Staff",
        name="Chilled",
        category=SupportEffectCategory.STATUS,
        effect_type="status",
        target_type=SupportTargetType.ENEMY,
        applies_status="Chilled",
    )

    assert effect.category == SupportEffectCategory.STATUS
    assert effect.applies_status == "Chilled"


def test_damage_amplification_effect():
    effect = SupportEffect(
        source="Major Slayer",
        name="Major Slayer",
        category=SupportEffectCategory.BUFF,
        effect_type="damage_amplification",
        target_type=SupportTargetType.SELF,
        magnitude=10,
        unit=EffectUnit.PERCENT,
        damage_amplification=10,
    )

    assert effect.damage_amplification == 10


def test_resistance_reduction_effect():
    effect = SupportEffect(
        source="Major Breach",
        name="Major Breach",
        category=SupportEffectCategory.DEBUFF,
        effect_type="resistance_reduction",
        target_type=SupportTargetType.ENEMY,
        magnitude=5948,
        unit=EffectUnit.FLAT,
        resistance_reduction=5948,
    )

    assert effect.resistance_reduction == 5948
    assert effect.target_type == SupportTargetType.ENEMY


def test_conditional_triggered_effect_structure():
    """
    Represents a Frost -> Chilled -> Brittle chain structurally, without
    resolving the proc.
    """

    frost_effect = SupportEffect(
        source="Frost Staff Heavy Attack",
        name="Frost Damage",
        category=SupportEffectCategory.OTHER,
        effect_type="damage",
        target_type=SupportTargetType.ENEMY,
        trigger=SupportEffectTrigger(
            trigger="on_direct_damage",
            chance=1.0,
            resulting_status="Chilled",
        ),
    )

    chilled_status = SupportEffect(
        source="Chilled",
        name="Chilled",
        category=SupportEffectCategory.STATUS,
        effect_type="status",
        target_type=SupportTargetType.ENEMY,
        applies_status="Chilled",
        trigger=SupportEffectTrigger(
            trigger="on_chilled_reapplied",
            chance=1.0,
            condition="target_is_chilled",
            resulting_status="Brittle",
        ),
    )

    brittle_status = SupportEffect(
        source="Brittle",
        name="Brittle",
        category=SupportEffectCategory.DEBUFF,
        effect_type="critical_damage_taken",
        target_type=SupportTargetType.ENEMY,
        requires_status="Chilled",
        applies_status="Brittle",
    )

    assert frost_effect.trigger.resulting_status == "Chilled"
    assert chilled_status.trigger.condition == "target_is_chilled"
    assert chilled_status.trigger.resulting_status == "Brittle"
    assert brittle_status.requires_status == "Chilled"


def test_trigger_rejects_invalid_chance():
    with pytest.raises(ValueError):
        SupportEffectTrigger(
            trigger="on_direct_damage",
            chance=1.5,
        )


def test_coverage_target_count():
    effect = SupportEffect(
        source="Barrier",
        name="Barrier",
        category=SupportEffectCategory.BUFF,
        effect_type="shield",
        target_type=SupportTargetType.GROUP,
        target_count=6,
    )

    assert effect.target_count == 6


def test_negative_target_count_is_rejected():
    with pytest.raises(ValueError):
        SupportEffect(
            source="Broken",
            name="Broken",
            category=SupportEffectCategory.BUFF,
            effect_type="shield",
            target_type=SupportTargetType.GROUP,
            target_count=-1,
        )


def test_duration_and_uptime():
    effect = SupportEffect(
        source="Major Berserk",
        name="Major Berserk",
        category=SupportEffectCategory.BUFF,
        effect_type="damage_amplification",
        target_type=SupportTargetType.SELF,
        duration=8,
        uptime=0.4,
    )

    assert effect.duration == 8
    assert effect.uptime == 0.4


def test_uptime_out_of_range_is_rejected():
    with pytest.raises(ValueError):
        SupportEffect(
            source="Bad Effect",
            name="Bad Effect",
            category=SupportEffectCategory.BUFF,
            effect_type="damage_amplification",
            target_type=SupportTargetType.SELF,
            uptime=1.5,
        )


def test_stacking_and_exclusivity():
    major_brutality = SupportEffect(
        source="Major Brutality",
        name="Major Brutality",
        category=SupportEffectCategory.BUFF,
        effect_type="weapon_spell_damage",
        target_type=SupportTargetType.SELF,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group="major_brutality",
    )

    minor_brutality = SupportEffect(
        source="Minor Brutality",
        name="Minor Brutality",
        category=SupportEffectCategory.BUFF,
        effect_type="weapon_spell_damage",
        target_type=SupportTargetType.SELF,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group="minor_brutality",
    )

    penetration_stack = SupportEffect(
        source="Crusher Enchant",
        name="Crusher",
        category=SupportEffectCategory.DEBUFF,
        effect_type="resistance_reduction",
        target_type=SupportTargetType.ENEMY,
        stacking=StackingBehavior.STACKS,
    )

    assert major_brutality.exclusivity_group != minor_brutality.exclusivity_group
    assert penetration_stack.stacking == StackingBehavior.STACKS


def test_self_only_effect_does_not_contribute_to_group():
    effect = SupportEffect(
        source="Personal Stat",
        name="Personal Stat",
        category=SupportEffectCategory.BUFF,
        effect_type="weapon_spell_damage",
        target_type=SupportTargetType.SELF,
    )

    assert effect.contributes_to_group() is False


def test_zero_uptime_effect_does_not_contribute_to_group():
    effect = SupportEffect(
        source="Never Procs",
        name="Never Procs",
        category=SupportEffectCategory.BUFF,
        effect_type="weapon_spell_damage",
        target_type=SupportTargetType.GROUP,
        uptime=0.0,
    )

    assert effect.contributes_to_group() is False
