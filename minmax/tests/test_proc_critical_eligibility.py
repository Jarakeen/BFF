from minmax.proc_critical_eligibility import (
    ProcDamageKind,
    ProcScalingKind,
    resolve_proc_critical_eligibility,
)


def test_offensive_stat_scaled_proc_is_crit_eligible():
    result = resolve_proc_critical_eligibility(
        scaling_kind=ProcScalingKind.OFFENSIVE_STATS,
    )

    assert result.can_crit is True


def test_max_health_scaled_proc_cannot_crit():
    result = resolve_proc_critical_eligibility(
        scaling_kind=ProcScalingKind.MAX_HEALTH,
    )

    assert result.can_crit is False


def test_escalating_modifier_proc_cannot_crit():
    result = resolve_proc_critical_eligibility(
        scaling_kind=ProcScalingKind.ESCALATING_MODIFIER,
    )

    assert result.can_crit is False


def test_oblivion_damage_cannot_crit_regardless_of_scaling_bucket():
    result = resolve_proc_critical_eligibility(
        scaling_kind=ProcScalingKind.OFFENSIVE_STATS,
        damage_kind=ProcDamageKind.OBLIVION,
    )

    assert result.can_crit is False


def test_flat_or_unresolved_proc_stays_unknown():
    result = resolve_proc_critical_eligibility(
        scaling_kind=ProcScalingKind.FLAT_OR_UNRESOLVED,
    )

    assert result.can_crit is None
