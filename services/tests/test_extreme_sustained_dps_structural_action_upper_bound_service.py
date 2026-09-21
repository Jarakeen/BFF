from __future__ import annotations

from services.extreme_sustained_dps_structural_action_upper_bound_service import (
    ExtremeSustainedDPSAbsoluteActionDamageCeiling,
    ExtremeSustainedDPSDamageActionCountProof,
    ExtremeSustainedDPSStructuralActionUpperBoundService,
)


def test_complete_structural_proofs_produce_safe_dps_ceiling() -> None:
    result = ExtremeSustainedDPSStructuralActionUpperBoundService.evaluate(
        "branch:a",
        duration_seconds=20.0,
        action_count=ExtremeSustainedDPSDamageActionCountProof(
            maximum_damage_action_count=40,
            proven_safe=True,
            source="reviewed schedule family",
        ),
        action_damage=ExtremeSustainedDPSAbsoluteActionDamageCeiling(
            upper_bound_damage=1000.0,
            proven_safe=True,
            covers_periodic_and_triggered=True,
            source="absolute action dominance proof",
        ),
    )

    assert result.bound.proven_safe is True
    assert result.bound.upper_bound_dps == 2000.0
    assert result.unresolved == ()


def test_unproven_action_count_forces_bound_open() -> None:
    result = ExtremeSustainedDPSStructuralActionUpperBoundService.evaluate(
        "branch:b",
        duration_seconds=20.0,
        action_count=ExtremeSustainedDPSDamageActionCountProof(
            maximum_damage_action_count=40,
            proven_safe=False,
            source="heuristic",
        ),
        action_damage=ExtremeSustainedDPSAbsoluteActionDamageCeiling(
            upper_bound_damage=1000.0,
            proven_safe=True,
            covers_periodic_and_triggered=True,
            source="safe",
        ),
    )

    assert result.bound.proven_safe is False
    assert result.bound.upper_bound_dps is None
    assert any("not proven safe" in row for row in result.unresolved)


def test_action_ceiling_without_periodic_triggered_coverage_forces_open() -> None:
    result = ExtremeSustainedDPSStructuralActionUpperBoundService.evaluate(
        "branch:c",
        duration_seconds=10.0,
        action_count=ExtremeSustainedDPSDamageActionCountProof(
            maximum_damage_action_count=10,
            proven_safe=True,
            source="safe",
        ),
        action_damage=ExtremeSustainedDPSAbsoluteActionDamageCeiling(
            upper_bound_damage=500.0,
            proven_safe=True,
            covers_periodic_and_triggered=False,
            source="direct-only",
        ),
    )

    assert result.bound.proven_safe is False
    assert result.bound.upper_bound_dps is None
    assert any("periodic/triggered" in row for row in result.unresolved)


def test_missing_absolute_action_ceiling_forces_open() -> None:
    result = ExtremeSustainedDPSStructuralActionUpperBoundService.evaluate(
        "branch:d",
        duration_seconds=10.0,
        action_count=ExtremeSustainedDPSDamageActionCountProof(
            maximum_damage_action_count=10,
            proven_safe=True,
            source="safe",
        ),
        action_damage=ExtremeSustainedDPSAbsoluteActionDamageCeiling(
            upper_bound_damage=None,
            proven_safe=False,
            covers_periodic_and_triggered=False,
            source="missing",
        ),
    )

    assert result.bound.proven_safe is False
    assert result.bound.upper_bound_dps is None
    assert any("unavailable" in row for row in result.unresolved)
