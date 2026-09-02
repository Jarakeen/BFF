import pytest

from minmax.skill_component_damage_scaling import (
    SkillComponentDamageScaling,
    SkillComponentDamageScalingType,
    extract_explicit_component_damage_scaling,
)


def test_extracts_accumulated_damage_scaling_with_explicit_cap():
    rows = extract_explicit_component_damage_scaling(
        skill_rank_id=10,
        coefficient_number=2,
        component_text=(
            "After the duration ends, the sunlight bursts, dealing $2 Magic Damage, "
            "which increases based on the amount of damage you dealt to them over the duration, up to 200%."
        ),
    )
    assert len(rows) == 1
    assert rows[0].scaling_type is SkillComponentDamageScalingType.ACCUMULATED_DAMAGE
    assert rows[0].max_bonus_fraction == 2.0
    assert rows[0].increment_fraction is None


def test_extracts_per_tick_increment_without_evaluating_tick_state():
    rows = extract_explicit_component_damage_scaling(
        skill_rank_id=20,
        coefficient_number=1,
        component_text=(
            "Enemies take $1 Magic Damage every 2 seconds for 20 seconds which increases by 12% per tick."
        ),
    )
    assert len(rows) == 1
    assert rows[0].scaling_type is SkillComponentDamageScalingType.PER_TICK_INCREMENT
    assert rows[0].increment_fraction == 0.12
    assert rows[0].max_bonus_fraction is None


def test_unrelated_damage_text_emits_no_scaling():
    assert extract_explicit_component_damage_scaling(
        skill_rank_id=30,
        coefficient_number=1,
        component_text="Deal $1 Flame Damage every 1 second for 10 seconds.",
    ) == ()


def test_scaling_shape_validation_is_type_specific():
    with pytest.raises(ValueError):
        SkillComponentDamageScaling(
            skill_rank_id=40,
            coefficient_number=1,
            scaling_type=SkillComponentDamageScalingType.ACCUMULATED_DAMAGE,
            evidence="increases based on damage",
            increment_fraction=0.10,
        )
