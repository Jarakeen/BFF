from __future__ import annotations

import pytest

from minmax.rotation_plan import RotationPlan
from services.rotation_dd_damage_projection_service import (
    RotationDDDamageInstance,
    RotationDDDamageProjectionService,
)


def _plan(duration: float = 10.0) -> RotationPlan:
    return RotationPlan(
        character_name="Parsecat",
        build_name="DD Parse",
        duration_seconds=duration,
        actions=(),
    )


def test_projection_sums_time_resolved_damage_and_reports_dps() -> None:
    result = RotationDDDamageProjectionService().project(
        plan=_plan(),
        instances=(
            RotationDDDamageInstance(
                time_seconds=0.0,
                source_name="Spammable",
                expected_damage=100_000.0,
                event_id="hit-1",
            ),
            RotationDDDamageInstance(
                time_seconds=5.0,
                source_name="Spammable",
                expected_damage=100_000.0,
                event_id="hit-2",
            ),
            RotationDDDamageInstance(
                time_seconds=7.0,
                source_name="DoT Tick",
                expected_damage=50_000.0,
                event_id="tick-1",
            ),
        ),
    )

    assert result.complete
    assert result.known_damage == pytest.approx(250_000.0)
    assert result.total_damage == pytest.approx(250_000.0)
    assert result.projected_dps == pytest.approx(25_000.0)
    assert tuple(item.source_name for item in result.by_source) == ("DoT Tick", "Spammable")
    assert result.by_source[1].known_damage == pytest.approx(200_000.0)
    assert result.by_source[1].instance_count == 2


def test_missing_damage_stays_unresolved_instead_of_becoming_zero() -> None:
    result = RotationDDDamageProjectionService().project(
        plan=_plan(),
        instances=(
            RotationDDDamageInstance(
                time_seconds=1.0,
                source_name="Known Hit",
                expected_damage=20_000.0,
            ),
            RotationDDDamageInstance(
                time_seconds=2.0,
                source_name="Mystery Proc",
                expected_damage=None,
            ),
        ),
    )

    assert not result.complete
    assert result.known_damage == pytest.approx(20_000.0)
    assert result.total_damage is None
    assert result.projected_dps is None
    assert any("Mystery Proc" in item for item in result.unresolved)


def test_explicit_unresolved_evidence_blocks_complete_total() -> None:
    result = RotationDDDamageProjectionService().project(
        plan=_plan(),
        instances=(
            RotationDDDamageInstance(
                time_seconds=1.0,
                source_name="Execute",
                expected_damage=50_000.0,
                unresolved=("execute target-health scaling is not resolved",),
            ),
        ),
    )

    assert result.known_damage == pytest.approx(50_000.0)
    assert result.total_damage is None
    assert result.unresolved == ("execute target-health scaling is not resolved",)


def test_zero_damage_is_known_zero_not_unresolved() -> None:
    result = RotationDDDamageProjectionService().project(
        plan=_plan(),
        instances=(
            RotationDDDamageInstance(
                time_seconds=1.0,
                source_name="Verified Zero",
                expected_damage=0.0,
            ),
        ),
    )

    assert result.complete
    assert result.total_damage == 0.0
    assert result.projected_dps == 0.0
    assert result.unresolved == ()


def test_damage_instance_after_horizon_is_rejected() -> None:
    with pytest.raises(ValueError, match="after rotation plan duration"):
        RotationDDDamageProjectionService().project(
            plan=_plan(),
            instances=(
                RotationDDDamageInstance(
                    time_seconds=10.1,
                    source_name="Late Tick",
                    expected_damage=1.0,
                ),
            ),
        )


def test_duplicate_explicit_event_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate DD damage event_id"):
        RotationDDDamageProjectionService().project(
            plan=_plan(),
            instances=(
                RotationDDDamageInstance(
                    time_seconds=1.0,
                    source_name="Hit",
                    expected_damage=10.0,
                    event_id="same",
                ),
                RotationDDDamageInstance(
                    time_seconds=2.0,
                    source_name="Hit",
                    expected_damage=10.0,
                    event_id="SAME",
                ),
            ),
        )


def test_nonpositive_plan_duration_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive plan duration"):
        RotationDDDamageProjectionService().project(
            plan=_plan(0.0),
            instances=(),
        )


def test_instance_requires_nonnegative_finite_damage_when_known() -> None:
    with pytest.raises(ValueError, match="expected_damage"):
        RotationDDDamageInstance(
            time_seconds=1.0,
            source_name="Bad Hit",
            expected_damage=-1.0,
        )


def test_source_breakdown_counts_unresolved_instances_without_inventing_damage() -> None:
    result = RotationDDDamageProjectionService().project(
        plan=_plan(),
        instances=(
            RotationDDDamageInstance(
                time_seconds=1.0,
                source_name="DoT",
                expected_damage=5_000.0,
            ),
            RotationDDDamageInstance(
                time_seconds=2.0,
                source_name="dot",
                expected_damage=None,
            ),
        ),
    )

    assert len(result.by_source) == 1
    assert result.by_source[0].source_name == "DoT"
    assert result.by_source[0].known_damage == pytest.approx(5_000.0)
    assert result.by_source[0].instance_count == 2
