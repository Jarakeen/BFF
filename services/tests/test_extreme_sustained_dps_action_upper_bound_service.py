from __future__ import annotations

import pytest

from services.extreme_sustained_dps_action_upper_bound_service import (
    ExtremeSustainedDPSActionDominanceProof,
    ExtremeSustainedDPSActionUpperBoundService,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrence,
    RotationActionDamageOccurrenceEvidence,
)


def _occurrences(*, unresolved=()):
    return RotationActionDamageOccurrenceEvidence(
        action_time_seconds=2.0,
        action_sequence=4,
        occurrences=(
            RotationActionDamageOccurrence(
                time_seconds=2.0,
                sequence=4,
                damage_value=1000.0,
                source_name="Skill",
                coefficient_number=1,
            ),
            RotationActionDamageOccurrence(
                time_seconds=3.0,
                sequence=4,
                damage_value=500.0,
                source_name="Skill",
                coefficient_number=2,
                occurrence_index=0,
            ),
            RotationActionDamageOccurrence(
                time_seconds=4.0,
                sequence=4,
                damage_value=500.0,
                source_name="Skill",
                coefficient_number=2,
                occurrence_index=1,
            ),
        ),
        unresolved=tuple(unresolved),
    )


def _proof(*, dominated=("gear", "cp"), required=("gear", "cp"), multiplier=1.0, unresolved=()):
    return ExtremeSustainedDPSActionDominanceProof(
        candidate_key="candidate",
        dominated_axes=tuple(dominated),
        required_axes=tuple(required),
        optimistic_multiplier=multiplier,
        source="test proof",
        unresolved=tuple(unresolved),
    )


def test_complete_dominance_promotes_exact_consequence_to_safe_bound() -> None:
    result = ExtremeSustainedDPSActionUpperBoundService.from_occurrences(
        occurrence_evidence=_occurrences(),
        dominance=_proof(multiplier=1.25),
    )

    assert result.exact_damage == pytest.approx(2000.0)
    assert result.dominance_complete is True
    assert result.bound.proven_safe is True
    assert result.bound.covers_periodic_and_triggered is True
    assert result.bound.upper_bound_damage == pytest.approx(2500.0)


def test_missing_mutation_axis_keeps_action_fail_open() -> None:
    result = ExtremeSustainedDPSActionUpperBoundService.from_occurrences(
        occurrence_evidence=_occurrences(),
        dominance=_proof(dominated=("gear",), required=("gear", "cp")),
    )

    assert result.exact_damage == pytest.approx(2000.0)
    assert result.dominance_complete is False
    assert result.bound.proven_safe is False
    assert result.bound.upper_bound_damage is None
    assert any("cp" in row for row in result.bound.unresolved)


def test_unresolved_exact_occurrence_evidence_never_promotes() -> None:
    result = ExtremeSustainedDPSActionUpperBoundService.from_occurrences(
        occurrence_evidence=_occurrences(unresolved=("periodic cadence unresolved",)),
        dominance=_proof(),
    )

    assert result.exact_damage is None
    assert result.bound.proven_safe is False
    assert result.bound.covers_periodic_and_triggered is False
    assert result.bound.upper_bound_damage is None


def test_unresolved_dominance_proof_never_promotes() -> None:
    result = ExtremeSustainedDPSActionUpperBoundService.from_occurrences(
        occurrence_evidence=_occurrences(),
        dominance=_proof(unresolved=("CP ceiling unreviewed",)),
    )

    assert result.exact_damage == pytest.approx(2000.0)
    assert result.dominance_complete is False
    assert result.bound.proven_safe is False


def test_required_axes_are_case_insensitive() -> None:
    proof = _proof(
        dominated=("Gear", "Champion Points"),
        required=("gear", "champion points"),
    )

    assert proof.complete is True


@pytest.mark.parametrize("multiplier", (0.0, 0.5, float("inf"), float("nan")))
def test_invalid_optimistic_multiplier_fails_closed(multiplier: float) -> None:
    with pytest.raises(ValueError, match="multiplier"):
        _proof(multiplier=multiplier)
