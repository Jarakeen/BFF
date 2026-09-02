from minmax.skill_component_stat_scaling import (
    SkillComponentScaledStat,
    SkillComponentStatScalingDriver,
    extract_explicit_component_stat_scaling,
)


def test_extracts_elder_dragon_missing_health_recovery_scaling():
    rows = extract_explicit_component_stat_scaling(
        skill_rank_id=5578,
        coefficient_number=1,
        component_text=(
            "Increases your Health Recovery by up to 350, based on your missing Health. "
            "Current amount: $1"
        ),
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.stat is SkillComponentScaledStat.HEALTH_RECOVERY
    assert row.scaling_driver is SkillComponentStatScalingDriver.MISSING_HEALTH
    assert row.maximum_bonus == 350.0


def test_current_amount_without_definition_is_not_promoted():
    assert extract_explicit_component_stat_scaling(
        skill_rank_id=1,
        coefficient_number=1,
        component_text="Current amount: $1",
    ) == ()


def test_wrong_current_amount_coefficient_is_not_promoted():
    assert extract_explicit_component_stat_scaling(
        skill_rank_id=1,
        coefficient_number=2,
        component_text=(
            "Increases your Health Recovery by up to 700, based on your missing Health. "
            "Current amount: $1"
        ),
    ) == ()
