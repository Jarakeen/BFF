import pytest

from minmax.coverage_classification import CoverageClassification
from services.encounter_provider_candidate import (
    ProviderCandidate,
    ProviderCandidateSet,
    ProviderCandidateStatus,
)
from services.encounter_provider_suitability import (
    EncounterProviderSuitabilityService,
    ProviderSuitabilityAssessment,
    ProviderSuitabilityDimension,
    ProviderSuitabilityEvidence,
    ProviderSuitabilityStatus,
)


def _candidate(member_id: str, status: ProviderCandidateStatus = ProviderCandidateStatus.VIABLE):
    return ProviderCandidate(
        requirement_id="req-1",
        encounter_id="enc-1",
        requirement_type="major_force",
        member_id=member_id,
        character_name=member_id,
        build_name=f"{member_id} build",
        status=status,
        evidence_sources=("phase10",),
    )


def _set(*candidates: ProviderCandidate) -> ProviderCandidateSet:
    return ProviderCandidateSet(
        requirement_id="req-1",
        encounter_id="enc-1",
        requirement_type="major_force",
        required_provider_count=1,
        coverage_classification=CoverageClassification.REDUNDANT,
        candidates=tuple(candidates),
    )


def _evidence(
    member_id: str,
    dimension: ProviderSuitabilityDimension,
    assessment: ProviderSuitabilityAssessment,
) -> ProviderSuitabilityEvidence:
    return ProviderSuitabilityEvidence(
        requirement_id="req-1",
        member_id=member_id,
        dimension=dimension,
        assessment=assessment,
        source="explicit test evidence",
    )


def test_suitability_keeps_unassessed_viable_candidates_visible():
    result = EncounterProviderSuitabilityService().assess(
        (_set(_candidate("a"), _candidate("b")),),
    )[0]

    assert [row.candidate.member_id for row in result.candidates] == ["a", "b"]
    assert [row.status for row in result.candidates] == [
        ProviderSuitabilityStatus.UNASSESSED,
        ProviderSuitabilityStatus.UNASSESSED,
    ]


def test_suitability_aggregates_supported_dimensions_without_ranking():
    result = EncounterProviderSuitabilityService().assess(
        (_set(_candidate("a"), _candidate("b")),),
        (
            _evidence("a", ProviderSuitabilityDimension.ROLE, ProviderSuitabilityAssessment.SATISFIED),
            _evidence("a", ProviderSuitabilityDimension.RANGE, ProviderSuitabilityAssessment.SATISFIED),
            _evidence("b", ProviderSuitabilityDimension.ROLE, ProviderSuitabilityAssessment.SATISFIED),
        ),
    )[0]

    assert [row.candidate.member_id for row in result.suitable] == ["a", "b"]
    assert result.unsuitable == ()
    assert result.unresolved == ()


def test_unsatisfied_dimension_makes_candidate_unsuitable():
    result = EncounterProviderSuitabilityService().assess(
        (_set(_candidate("a")),),
        (
            _evidence("a", ProviderSuitabilityDimension.ROLE, ProviderSuitabilityAssessment.SATISFIED),
            _evidence("a", ProviderSuitabilityDimension.RANGE, ProviderSuitabilityAssessment.UNSATISFIED),
        ),
    )[0].candidates[0]

    assert result.status == ProviderSuitabilityStatus.UNSUITABLE
    assert result.failed_dimensions == (ProviderSuitabilityDimension.RANGE,)


def test_unknown_dimension_preserves_unresolved_suitability():
    result = EncounterProviderSuitabilityService().assess(
        (_set(_candidate("a")),),
        (
            _evidence("a", ProviderSuitabilityDimension.ROLE, ProviderSuitabilityAssessment.SATISFIED),
            _evidence("a", ProviderSuitabilityDimension.UPTIME, ProviderSuitabilityAssessment.UNKNOWN),
        ),
    )[0].candidates[0]

    assert result.status == ProviderSuitabilityStatus.UNRESOLVED
    assert result.unresolved_dimensions == (ProviderSuitabilityDimension.UPTIME,)


def test_unsatisfied_takes_precedence_over_unknown():
    result = EncounterProviderSuitabilityService().assess(
        (_set(_candidate("a")),),
        (
            _evidence("a", ProviderSuitabilityDimension.UPTIME, ProviderSuitabilityAssessment.UNKNOWN),
            _evidence("a", ProviderSuitabilityDimension.RANGE, ProviderSuitabilityAssessment.UNSATISFIED),
        ),
    )[0].candidates[0]

    assert result.status == ProviderSuitabilityStatus.UNSUITABLE


def test_suitability_rejects_evidence_for_nonviable_phase10_candidate():
    candidate_set = _set(_candidate("a", ProviderCandidateStatus.UNRESOLVED))

    with pytest.raises(ValueError, match="only assess Phase 10 viable"):
        EncounterProviderSuitabilityService().assess(
            (candidate_set,),
            (_evidence("a", ProviderSuitabilityDimension.ROLE, ProviderSuitabilityAssessment.SATISFIED),),
        )


def test_suitability_rejects_unknown_candidate_identity():
    with pytest.raises(ValueError, match="not a provider candidate"):
        EncounterProviderSuitabilityService().assess(
            (_set(_candidate("a")),),
            (_evidence("missing", ProviderSuitabilityDimension.ROLE, ProviderSuitabilityAssessment.SATISFIED),),
        )


def test_suitability_rejects_conflicting_assessments_for_same_dimension():
    with pytest.raises(ValueError, match="conflicting suitability assessments"):
        EncounterProviderSuitabilityService().assess(
            (_set(_candidate("a")),),
            (
                _evidence("a", ProviderSuitabilityDimension.RANGE, ProviderSuitabilityAssessment.SATISFIED),
                _evidence("a", ProviderSuitabilityDimension.RANGE, ProviderSuitabilityAssessment.UNSATISFIED),
            ),
        )
