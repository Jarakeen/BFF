from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_generated_search_evidence_adapter_service import (
    ExtremeSustainedDPSGeneratedSearchEvidenceAdapterService,
)
from services.extreme_sustained_dps_rotation_upper_bound_service import (
    ExtremeSustainedDPSRotationUpperBound,
)


def test_rotation_upper_bound_adapts_without_strengthening_proof() -> None:
    source = ExtremeSustainedDPSRotationUpperBound(
        duration_seconds=10.0,
        upper_bound_damage=1500.0,
        upper_bound_dps=150.0,
        damage_action_count=3,
        covered_action_count=3,
        proven_safe=True,
        evidence=("proof",),
        unresolved=(),
    )

    result = ExtremeSustainedDPSGeneratedSearchEvidenceAdapterService.branch_bound(
        "candidate:a",
        source,
    )

    assert result.candidate_key == "candidate:a"
    assert result.upper_bound_dps == 150.0
    assert result.proven_safe is True
    assert result.unresolved == ()


def test_unproven_rotation_bound_stays_unproven() -> None:
    source = ExtremeSustainedDPSRotationUpperBound(
        duration_seconds=10.0,
        upper_bound_damage=None,
        upper_bound_dps=None,
        damage_action_count=3,
        covered_action_count=2,
        proven_safe=False,
        evidence=(),
        unresolved=("missing action bound",),
    )

    result = ExtremeSustainedDPSGeneratedSearchEvidenceAdapterService.branch_bound(
        "candidate:b",
        source,
    )

    assert result.upper_bound_dps is None
    assert result.proven_safe is False
    assert result.unresolved == ("missing action bound",)


def test_runtime_result_adapts_exact_leaf_without_inventing_score() -> None:
    record = SimpleNamespace(modeled_dps=123.5, duration_seconds=20.0)
    source = SimpleNamespace(
        record=record,
        mechanic_complete=True,
        evidence=("simulated",),
        unresolved=(),
    )

    result = ExtremeSustainedDPSGeneratedSearchEvidenceAdapterService.exact_leaf(
        "leaf:1",
        source,
    )

    assert result.candidate_key == "leaf:1"
    assert result.modeled_dps == 123.5
    assert result.duration_seconds == 20.0
    assert result.mechanic_complete is True


def test_runtime_result_without_record_stays_unresolved_for_search() -> None:
    source = SimpleNamespace(
        record=None,
        mechanic_complete=False,
        evidence=(),
        unresolved=("damage incomplete",),
    )

    result = ExtremeSustainedDPSGeneratedSearchEvidenceAdapterService.exact_leaf(
        "leaf:2",
        source,
    )

    assert result.modeled_dps is None
    assert result.duration_seconds is None
    assert result.mechanic_complete is False
    assert result.unresolved == ("damage incomplete",)
