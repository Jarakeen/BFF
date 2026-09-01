from minmax.skill_component_condition import (
    SkillComponentConditionType,
    extract_explicit_component_conditions,
)


def test_explicit_target_health_threshold_becomes_component_condition():
    conditions = extract_explicit_component_conditions(
        skill_rank_id=10,
        coefficient_number=2,
        component_text="Deals up to $2 Magic Damage when the enemy is below 25% Health.",
    )

    assert len(conditions) == 1
    condition = conditions[0]
    assert condition.skill_rank_id == 10
    assert condition.coefficient_number == 2
    assert condition.condition_type is SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT
    assert condition.threshold == 0.25
    assert "below 25% Health" in condition.evidence


def test_under_health_wording_is_supported():
    conditions = extract_explicit_component_conditions(
        skill_rank_id=11,
        coefficient_number=1,
        component_text="Deal $1 Magic Damage while the target is under 50% Health.",
    )

    assert len(conditions) == 1
    assert conditions[0].threshold == 0.5


def test_generic_if_wording_is_not_promoted_to_condition():
    assert extract_explicit_component_conditions(
        skill_rank_id=10,
        coefficient_number=1,
        component_text="If the effect ends, deal $1 Magic Damage.",
    ) == ()


def test_health_percentage_without_threshold_relation_is_not_promoted():
    assert extract_explicit_component_conditions(
        skill_rank_id=10,
        coefficient_number=1,
        component_text="Restore Health equal to 25% of the damage dealt.",
    ) == ()


def test_invalid_percentage_fails_closed():
    assert extract_explicit_component_conditions(
        skill_rank_id=10,
        coefficient_number=1,
        component_text="Deals more damage when the enemy is below 125% Health.",
    ) == ()


def test_condition_after_second_placeholder_belongs_only_to_second_component():
    text = "Deal $1 Magic Damage, then $2 Magic Damage when the enemy is below 20% Health."

    first = extract_explicit_component_conditions(
        skill_rank_id=10,
        coefficient_number=1,
        component_text=text,
    )
    second = extract_explicit_component_conditions(
        skill_rank_id=10,
        coefficient_number=2,
        component_text=text,
    )

    assert first == ()
    assert len(second) == 1
    assert second[0].threshold == 0.20


def test_condition_before_second_placeholder_does_not_leak_forward():
    text = "Deal $1 Magic Damage while the enemy is below 25% Health, then deal $2 Magic Damage."

    first = extract_explicit_component_conditions(
        skill_rank_id=10,
        coefficient_number=1,
        component_text=text,
    )
    second = extract_explicit_component_conditions(
        skill_rank_id=10,
        coefficient_number=2,
        component_text=text,
    )

    assert len(first) == 1
    assert first[0].threshold == 0.25
    assert second == ()
