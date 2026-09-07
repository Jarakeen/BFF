from __future__ import annotations

import pytest

from minmax.fight_damage_trajectory import RaidDamageSegment, project_health_threshold_times


def test_constant_dps_projects_health_threshold_times() -> None:
    projection = project_health_threshold_times(
        maximum_health=100_000_000,
        thresholds=(0.70, 0.40),
        segments=(RaidDamageSegment(0.0, None, 1_000_000.0, "test raid DPS"),),
    )

    assert [item.time_seconds for item in projection.thresholds] == pytest.approx([30.0, 60.0])
    assert all(item.resolved for item in projection.thresholds)


def test_piecewise_dps_accounts_for_changed_damage_rate() -> None:
    projection = project_health_threshold_times(
        maximum_health=100_000_000,
        thresholds=(0.70, 0.40),
        segments=(
            RaidDamageSegment(0.0, 20.0, 2_000_000.0, "opening burn"),
            RaidDamageSegment(20.0, None, 500_000.0, "mechanic pressure"),
        ),
    )

    assert projection.thresholds[0].time_seconds == pytest.approx(15.0)
    # 40m damage is dealt by 20s; another 20m at 0.5m/s takes 40s.
    assert projection.thresholds[1].time_seconds == pytest.approx(60.0)


def test_finite_trajectory_leaves_unreached_threshold_unresolved() -> None:
    projection = project_health_threshold_times(
        maximum_health=100_000_000,
        thresholds=(0.90, 0.40),
        segments=(RaidDamageSegment(0.0, 20.0, 1_000_000.0),),
    )

    assert projection.thresholds[0].resolved is True
    assert projection.thresholds[0].time_seconds == pytest.approx(10.0)
    assert projection.thresholds[1].resolved is False
    assert projection.thresholds[1].time_seconds is None
    assert "ends before" in projection.thresholds[1].reason


def test_trajectory_requires_contiguous_segments_from_pull() -> None:
    with pytest.raises(ValueError, match="begin at 0"):
        project_health_threshold_times(
            maximum_health=100.0,
            thresholds=(0.5,),
            segments=(RaidDamageSegment(2.0, None, 10.0),),
        )

    with pytest.raises(ValueError, match="contiguous"):
        project_health_threshold_times(
            maximum_health=100.0,
            thresholds=(0.5,),
            segments=(
                RaidDamageSegment(0.0, 2.0, 10.0),
                RaidDamageSegment(3.0, None, 10.0),
            ),
        )
