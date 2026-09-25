from __future__ import annotations

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.extreme_sustained_dps_rotation_upper_bound_service import (
    ExtremeSustainedDPSActionUpperBound,
    ExtremeSustainedDPSRotationUpperBoundService,
)


def _action(time, sequence, kind, name="", *, bar=None):
    return RotationAction(
        time_seconds=float(time),
        sequence=int(sequence),
        kind=kind,
        name=name,
        bar=bar,
    )


def _plan():
    return RotationPlan(
        character_name="Tester",
        build_name="Ceiling",
        duration_seconds=10.0,
        actions=(
            _action(0.0, 0, RotationActionKind.SKILL, "Skill A"),
            _action(1.0, 1, RotationActionKind.LIGHT_ATTACK, "Light Attack"),
            _action(2.0, 2, RotationActionKind.BAR_SWAP, "Swap", bar="back"),
            _action(3.0, 3, RotationActionKind.SKILL, "Skill B"),
        ),
    )


def _bound(time, sequence, damage, *, safe=True, covers=True, unresolved=()):
    return ExtremeSustainedDPSActionUpperBound(
        time_seconds=time,
        sequence=sequence,
        upper_bound_damage=damage,
        proven_safe=safe,
        covers_periodic_and_triggered=covers,
        source="test",
        unresolved=tuple(unresolved),
    )


def test_complete_action_ceiling_set_produces_rotation_dps_upper_bound() -> None:
    result = ExtremeSustainedDPSRotationUpperBoundService.evaluate(
        _plan(),
        action_bounds=(
            _bound(0.0, 0, 1000.0),
            _bound(1.0, 1, 500.0),
            _bound(3.0, 3, 1500.0),
        ),
    )

    assert result.proven_safe is True
    assert result.damage_action_count == 3
    assert result.covered_action_count == 3
    assert result.upper_bound_damage == pytest.approx(3000.0)
    assert result.upper_bound_dps == pytest.approx(300.0)
    assert result.unresolved == ()


def test_non_damage_actions_do_not_require_damage_bounds() -> None:
    result = ExtremeSustainedDPSRotationUpperBoundService.evaluate(
        _plan(),
        action_bounds=(
            _bound(0.0, 0, 1000.0),
            _bound(1.0, 1, 500.0),
            _bound(3.0, 3, 1500.0),
        ),
    )

    assert result.damage_action_count == 3
    assert all("Swap" not in row for row in result.unresolved)


def test_missing_action_bound_withholds_whole_plan_ceiling() -> None:
    result = ExtremeSustainedDPSRotationUpperBoundService.evaluate(
        _plan(),
        action_bounds=(
            _bound(0.0, 0, 1000.0),
            _bound(1.0, 1, 500.0),
        ),
    )

    assert result.proven_safe is False
    assert result.upper_bound_damage is None
    assert result.upper_bound_dps is None
    assert any("Skill B" in row and "missing" in row for row in result.unresolved)


def test_unproven_action_bound_forces_whole_plan_ceiling_open() -> None:
    result = ExtremeSustainedDPSRotationUpperBoundService.evaluate(
        _plan(),
        action_bounds=(
            _bound(0.0, 0, 1000.0),
            _bound(1.0, 1, 500.0, safe=False),
            _bound(3.0, 3, 1500.0),
        ),
    )

    assert result.proven_safe is False
    assert result.upper_bound_dps is None
    assert any("not proven safe" in row for row in result.unresolved)


def test_action_ceiling_must_cover_periodic_and_triggered_damage() -> None:
    result = ExtremeSustainedDPSRotationUpperBoundService.evaluate(
        _plan(),
        action_bounds=(
            _bound(0.0, 0, 1000.0, covers=False),
            _bound(1.0, 1, 500.0),
            _bound(3.0, 3, 1500.0),
        ),
    )

    assert result.proven_safe is False
    assert any("periodic/triggered" in row for row in result.unresolved)


def test_extraneous_action_bound_withholds_proof() -> None:
    result = ExtremeSustainedDPSRotationUpperBoundService.evaluate(
        _plan(),
        action_bounds=(
            _bound(0.0, 0, 1000.0),
            _bound(1.0, 1, 500.0),
            _bound(3.0, 3, 1500.0),
            _bound(9.0, 9, 9999.0),
        ),
    )

    assert result.proven_safe is False
    assert result.upper_bound_dps is None
    assert any("does not match" in row for row in result.unresolved)


def test_duplicate_bound_coordinate_fails_closed() -> None:
    with pytest.raises(ValueError, match="duplicate sustained-DPS action upper bound"):
        ExtremeSustainedDPSRotationUpperBoundService.evaluate(
            _plan(),
            action_bounds=(
                _bound(0.0, 0, 1000.0),
                _bound(0.0, 0, 2000.0),
            ),
        )


def test_invalid_plan_duration_fails_closed() -> None:
    plan = RotationPlan(
        character_name="Tester",
        build_name="Bad",
        duration_seconds=0.0,
        actions=(),
    )
    with pytest.raises(ValueError, match="duration must be positive"):
        ExtremeSustainedDPSRotationUpperBoundService.evaluate(
            plan,
            action_bounds=(),
        )


def test_action_upper_bound_requires_strict_proof_flags() -> None:
    with pytest.raises(TypeError, match="proven_safe must be boolean"):
        _bound(0.0, 0, 100.0, safe="true")

    with pytest.raises(TypeError, match="covers_periodic_and_triggered must be boolean"):
        _bound(0.0, 0, 100.0, covers=1)


def test_action_upper_bound_cannot_claim_safe_without_damage_ceiling() -> None:
    with pytest.raises(
        ValueError,
        match="cannot be proven safe without numeric damage ceiling",
    ):
        _bound(0.0, 0, None, safe=True)


def test_action_upper_bound_rejects_boolean_sequence() -> None:
    with pytest.raises(TypeError, match="sequence must be an integer"):
        _bound(0.0, True, 100.0)


def test_rotation_upper_bound_rejects_inconsistent_direct_summary() -> None:
    from services.extreme_sustained_dps_rotation_upper_bound_service import (
        ExtremeSustainedDPSRotationUpperBound,
    )

    with pytest.raises(
        ValueError,
        match="covered_action_count cannot exceed damage_action_count",
    ):
        ExtremeSustainedDPSRotationUpperBound(
            duration_seconds=10.0,
            upper_bound_damage=None,
            upper_bound_dps=None,
            damage_action_count=1,
            covered_action_count=2,
            proven_safe=False,
            evidence=(),
            unresolved=("open",),
        )
