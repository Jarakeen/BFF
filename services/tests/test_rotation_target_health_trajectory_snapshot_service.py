from __future__ import annotations

import pytest

from minmax.fight_damage_trajectory import (
    FightDamageTrajectoryProjection,
    RaidDamageSegment,
)
from services.rotation_target_health_trajectory_snapshot_service import (
    RotationTargetHealthTrajectorySnapshotService,
)


def _trajectory(*segments: RaidDamageSegment) -> FightDamageTrajectoryProjection:
    return FightDamageTrajectoryProjection(
        maximum_health=10000.0,
        segments=tuple(segments),
        thresholds=(),
    )


def test_constant_open_ended_trajectory_resolves_exact_health() -> None:
    service = RotationTargetHealthTrajectorySnapshotService(
        trajectory=_trajectory(RaidDamageSegment(0.0, None, 1000.0, "explicit")),
        target_identity="boss",
    )

    snapshot = service.snapshot_at(2.5)

    assert snapshot is not None
    target = snapshot.target("boss")
    assert target is not None
    assert target.current_health == pytest.approx(7500.0)
    assert target.maximum_health == pytest.approx(10000.0)
    assert target.health_fraction() == pytest.approx(0.75)


def test_piecewise_trajectory_integrates_only_supplied_segments() -> None:
    service = RotationTargetHealthTrajectorySnapshotService(
        trajectory=_trajectory(
            RaidDamageSegment(0.0, 5.0, 1000.0, "phase one"),
            RaidDamageSegment(5.0, None, 500.0, "phase two"),
        ),
        target_identity="boss",
    )

    at_boundary = service.snapshot_at(5.0)
    after_boundary = service.snapshot_at(6.0)

    assert at_boundary is not None
    assert after_boundary is not None
    assert at_boundary.target("boss").current_health == pytest.approx(5000.0)  # type: ignore[union-attr]
    assert after_boundary.target("boss").current_health == pytest.approx(4500.0)  # type: ignore[union-attr]


def test_finite_trajectory_fails_closed_after_evidence_ends() -> None:
    service = RotationTargetHealthTrajectorySnapshotService(
        trajectory=_trajectory(RaidDamageSegment(0.0, 5.0, 1000.0, "finite")),
        target_identity="boss",
    )

    assert service.snapshot_at(5.0) is not None
    assert service.snapshot_at(5.0001) is None


def test_health_clamps_at_zero_for_explicit_open_ended_damage() -> None:
    service = RotationTargetHealthTrajectorySnapshotService(
        trajectory=_trajectory(RaidDamageSegment(0.0, None, 1000.0, "explicit")),
        target_identity="boss",
    )

    snapshot = service.snapshot_at(20.0)

    assert snapshot is not None
    assert snapshot.target("boss").current_health == pytest.approx(0.0)  # type: ignore[union-attr]


def test_empty_trajectory_has_no_snapshot_evidence() -> None:
    service = RotationTargetHealthTrajectorySnapshotService(
        trajectory=_trajectory(),
        target_identity="boss",
    )

    assert service.snapshot_at(0.0) is None
