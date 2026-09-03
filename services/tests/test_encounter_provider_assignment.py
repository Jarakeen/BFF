from minmax.coverage_classification import CoverageClassification
from services.encounter_provider_assignment import (
    EncounterProviderAssignmentService,
    ProviderAssignmentStatus,
)
from services.encounter_provider_candidate import (
    ProviderCandidate,
    ProviderCandidateSet,
    ProviderCandidateStatus,
)


def _candidate(member_id: str, status: ProviderCandidateStatus) -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id="req-1",
        encounter_id="encounter-1",
        requirement_type="major_force",
        member_id=member_id,
        character_name=member_id,
        build_name=f"{member_id} build",
        status=status,
        evidence_sources=("explicit evidence",),
    )


def _set(
    candidates: tuple[ProviderCandidate, ...],
    required_provider_count: int = 1,
) -> ProviderCandidateSet:
    return ProviderCandidateSet(
        requirement_id="req-1",
        encounter_id="encounter-1",
        requirement_type="major_force",
        required_provider_count=required_provider_count,
        coverage_classification=CoverageClassification.COVERED,
        candidates=candidates,
    )


def test_assignment_chooses_provider_when_evidence_leaves_no_choice():
    candidate = _candidate("char-a", ProviderCandidateStatus.VIABLE)

    result = EncounterProviderAssignmentService().assign((_set((candidate,)),))[0]

    assert result.status == ProviderAssignmentStatus.ASSIGNED
    assert result.primary_providers == (candidate,)
    assert result.backup_providers == ()


def test_assignment_does_not_use_roster_order_to_break_redundant_tie():
    first = _candidate("char-a", ProviderCandidateStatus.VIABLE)
    second = _candidate("char-b", ProviderCandidateStatus.VIABLE)

    result = EncounterProviderAssignmentService().assign((_set((first, second)),))[0]

    assert result.status == ProviderAssignmentStatus.UNRESOLVED_SELECTION
    assert result.primary_providers == ()
    assert result.backup_providers == (first, second)
    assert "Roster order is not treated as a strategy rule" in result.explanation


def test_assignment_preserves_unknown_when_unresolved_candidate_can_fill_shortfall():
    viable = _candidate("char-a", ProviderCandidateStatus.VIABLE)
    unresolved = _candidate("char-b", ProviderCandidateStatus.UNRESOLVED)

    result = EncounterProviderAssignmentService().assign(
        (_set((viable, unresolved), required_provider_count=2),)
    )[0]

    assert result.status == ProviderAssignmentStatus.UNRESOLVED_CAPABILITY
    assert result.primary_providers == ()
    assert result.backup_providers == (viable,)
    assert result.unresolved_candidates == (unresolved,)


def test_assignment_keeps_conflicting_candidate_first_class():
    viable = _candidate("char-a", ProviderCandidateStatus.VIABLE)
    conflicting = _candidate("char-b", ProviderCandidateStatus.CONFLICTING)

    result = EncounterProviderAssignmentService().assign((_set((viable, conflicting)),))[0]

    assert result.status == ProviderAssignmentStatus.CONFLICT
    assert result.primary_providers == ()
    assert result.backup_providers == (viable,)
    assert result.conflicting_candidates == (conflicting,)


def test_assignment_reports_insufficient_only_after_candidates_are_fully_assessed():
    viable = _candidate("char-a", ProviderCandidateStatus.VIABLE)

    result = EncounterProviderAssignmentService().assign(
        (_set((viable,), required_provider_count=2),)
    )[0]

    assert result.status == ProviderAssignmentStatus.INSUFFICIENT
    assert result.primary_providers == ()
    assert result.backup_providers == (viable,)
