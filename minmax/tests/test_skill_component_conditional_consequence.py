from minmax.skill_component_condition import (
    SkillComponentCondition,
    SkillComponentConditionType,
)
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequenceType,
    extract_explicit_conditional_consequences,
)


def _condition(threshold: float = 0.25) -> SkillComponentCondition:
    return SkillComponentCondition(
        skill_rank_id=10,
        coefficient_number=2,
        condition_type=SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT,
        threshold=threshold,
        evidence=f"below {threshold * 100:g}% Health",
    )


def test_explicit_up_to_more_damage_becomes_damage_amplification():
    consequences = extract_explicit_conditional_consequences(
        skill_rank_id=10,
        coefficient_number=2,
        condition=_condition(1.0),
        component_text=(
            "Deal $2 Bleed Damage over 12 seconds, dealing up to 450% more damage "
            "to enemies under 100% Health."
        ),
        effect_kind="damage",
    )

    assert len(consequences) == 1
    consequence = consequences[0]
    assert consequence.consequence_type is SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE
    assert consequence.maximum_bonus_fraction == 4.5


def test_ordinal_execute_damage_amplification_preserves_maximum_bonus():
    consequences = extract_explicit_conditional_consequences(
        skill_rank_id=10,
        coefficient_number=2,
        condition=_condition(0.25),
        component_text="The second hit deals up to 125% more damage to enemies with less than 25% Health.",
        effect_kind="damage",
    )

    assert consequences[0].maximum_bonus_fraction == 1.25


def test_conditioned_secondary_damage_is_activation_not_amplification():
    consequences = extract_explicit_conditional_consequences(
        skill_rank_id=10,
        coefficient_number=2,
        condition=_condition(0.20),
        component_text=(
            "If the enemy falls to or below 20% Health, an explosion deals an additional $2 Shock Damage."
        ),
        effect_kind="damage",
    )

    assert consequences[0].consequence_type is SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT
    assert consequences[0].maximum_bonus_fraction is None


def test_conditioned_heal_is_activation():
    consequences = extract_explicit_conditional_consequences(
        skill_rank_id=10,
        coefficient_number=1,
        condition=_condition(0.50),
        component_text="While below 50% Health, heal you for $1 Health.",
        effect_kind="heal",
    )

    assert consequences[0].consequence_type is SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT


def test_unknown_effect_kind_does_not_promote_consequence():
    assert extract_explicit_conditional_consequences(
        skill_rank_id=10,
        coefficient_number=1,
        condition=_condition(0.50),
        component_text="Something changes while below 50% Health.",
        effect_kind=None,
    ) == ()
