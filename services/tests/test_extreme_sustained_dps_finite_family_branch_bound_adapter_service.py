from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_finite_family_branch_bound_adapter_service import (
    ExtremeSustainedDPSFiniteFamilyBranchBoundAdapterService,
    ExtremeSustainedDPSFiniteFamilyBranchScopeProof,
)
from services.extreme_sustained_dps_pruning_service import ExtremeSustainedDPSBoundEvidence


def _result(*, omitted_scope=()):
    return SimpleNamespace(
        candidate_key="family:runtime",
        omitted_scope=tuple(omitted_scope),
        bound=ExtremeSustainedDPSBoundEvidence(
            candidate_key="family:runtime",
            upper_bound_dps=120.0,
            proven_safe=True,
            source="finite family",
            unresolved=(),
        ),
    )


def test_exact_branch_scope_promotes_local_family_ceiling() -> None:
    result = ExtremeSustainedDPSFiniteFamilyBranchBoundAdapterService.adapt(
        _result(omitted_scope=("encounter states remain open globally",)),
        scope=ExtremeSustainedDPSFiniteFamilyBranchScopeProof(
            branch_candidate_key="branch:runtime",
            family_candidate_key="family:runtime",
            denominator_matches_branch=True,
            excluded_omitted_scope=("encounter states remain open globally",),
            source="branch explicitly excludes encounter-state variants",
        ),
    )

    assert result.bound.proven_safe is True
    assert result.bound.upper_bound_dps == 120.0
    assert result.bound.candidate_key == "branch:runtime"


def test_missing_omitted_scope_exclusion_blocks_promotion() -> None:
    result = ExtremeSustainedDPSFiniteFamilyBranchBoundAdapterService.adapt(
        _result(omitted_scope=("continuous proc offset remains open",)),
        scope=ExtremeSustainedDPSFiniteFamilyBranchScopeProof(
            branch_candidate_key="branch:runtime",
            family_candidate_key="family:runtime",
            denominator_matches_branch=True,
        ),
    )

    assert result.bound.proven_safe is False
    assert result.bound.upper_bound_dps is None
    assert any("not explicitly excluded" in row for row in result.unresolved)


def test_branch_denominator_mismatch_blocks_promotion() -> None:
    result = ExtremeSustainedDPSFiniteFamilyBranchBoundAdapterService.adapt(
        _result(),
        scope=ExtremeSustainedDPSFiniteFamilyBranchScopeProof(
            branch_candidate_key="branch:wider",
            family_candidate_key="family:runtime",
            denominator_matches_branch=False,
        ),
    )

    assert result.bound.proven_safe is False
    assert any("not proven identical" in row for row in result.unresolved)


def test_family_identity_mismatch_blocks_promotion() -> None:
    result = ExtremeSustainedDPSFiniteFamilyBranchBoundAdapterService.adapt(
        _result(),
        scope=ExtremeSustainedDPSFiniteFamilyBranchScopeProof(
            branch_candidate_key="branch:runtime",
            family_candidate_key="family:other",
            denominator_matches_branch=True,
        ),
    )

    assert result.bound.proven_safe is False
    assert any("identity does not match" in row for row in result.unresolved)
