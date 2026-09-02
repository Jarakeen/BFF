from minmax.skill_component_role import (
    SkillComponentRoleType,
    extract_explicit_component_roles,
)


def test_extracts_same_ability_additional_damage_role():
    roles = extract_explicit_component_roles(
        skill_rank_id=10,
        coefficient_number=2,
        component_text="The trap deals $1 Bleed Damage, an additional $2 Bleed Damage over 20 seconds.",
        effect_kind="damage",
    )
    assert len(roles) == 1
    assert roles[0].role_type is SkillComponentRoleType.ADDITIONAL_DAMAGE


def test_single_coefficient_triggered_additional_damage_is_not_phase6_role():
    roles = extract_explicit_component_roles(
        skill_rank_id=11,
        coefficient_number=1,
        component_text="Your next Light Attack deals an additional $1 Physical Damage.",
        effect_kind="damage",
    )
    assert roles == ()


def test_extracts_additional_heal_role():
    roles = extract_explicit_component_roles(
        skill_rank_id=12,
        coefficient_number=3,
        component_text="You also heal a nearby ally for $3 Health.",
        effect_kind="heal",
    )
    assert len(roles) == 1
    assert roles[0].role_type is SkillComponentRoleType.ADDITIONAL_HEAL


def test_plain_component_has_no_secondary_role():
    assert extract_explicit_component_roles(
        skill_rank_id=13,
        coefficient_number=1,
        component_text="Deal $1 Flame Damage.",
        effect_kind="damage",
    ) == ()
