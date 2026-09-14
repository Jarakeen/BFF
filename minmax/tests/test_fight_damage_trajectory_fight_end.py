from minmax.fight_damage_trajectory import (
    RaidDamageSegment,
    project_fight_end_time,
    project_health_threshold_times,
)


def test_fight_end_reuses_open_ended_explicit_raid_damage_trajectory() -> None:
    trajectory = project_health_threshold_times(
        maximum_health=100_000_000.0,
        thresholds=(0.70,),
        segments=(RaidDamageSegment(0.0, None, 2_000_000.0),),
    )

    result = project_fight_end_time(trajectory)

    assert result.resolved is True
    assert result.time_seconds == 50.0
    assert result.damage_required == 100_000_000.0
    assert "explicit piecewise raid DPS trajectory" in result.reason


def test_fight_end_reuses_piecewise_damage_without_extending_final_rate() -> None:
    trajectory = project_health_threshold_times(
        maximum_health=100_000_000.0,
        thresholds=(0.70,),
        segments=(
            RaidDamageSegment(0.0, 10.0, 1_000_000.0),
            RaidDamageSegment(10.0, None, 3_000_000.0),
        ),
    )

    result = project_fight_end_time(trajectory)

    assert result.resolved is True
    assert result.time_seconds == 40.0


def test_fight_end_stays_unresolved_when_finite_evidence_ends_before_kill() -> None:
    trajectory = project_health_threshold_times(
        maximum_health=100_000_000.0,
        thresholds=(0.90,),
        segments=(RaidDamageSegment(0.0, 20.0, 2_000_000.0),),
    )

    result = project_fight_end_time(trajectory)

    assert result.resolved is False
    assert result.time_seconds is None
    assert "before encounter Health reaches zero" in result.reason


def test_threshold_projection_and_fight_end_share_same_piecewise_clock() -> None:
    trajectory = project_health_threshold_times(
        maximum_health=100_000_000.0,
        thresholds=(0.70, 0.40),
        segments=(
            RaidDamageSegment(0.0, 10.0, 1_000_000.0),
            RaidDamageSegment(10.0, None, 2_000_000.0),
        ),
    )

    assert tuple(point.time_seconds for point in trajectory.thresholds) == (20.0, 35.0)
    assert project_fight_end_time(trajectory).time_seconds == 55.0
