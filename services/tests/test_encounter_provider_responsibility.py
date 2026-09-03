import pytest

from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.encounter_provider_candidate import (
    ProviderCandidate,
    ProviderCandidateStatus,
)
from services.encounter_provider_responsibility import (
    EncounterProviderResponsibilityService,
    ProviderResponsibilityConflictEvidence,
)


def _candidate(requirement_id: str, member_id: str) -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id=requirement_id,
        encounter_id="enc-1",
        requirement_type=requirement_id,
        member_id=member_id,
        character_name=member_id,
        build_name=f"{member_id} build",
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("phase10",),
    )


def _assignment(
    requirement_id: str,
    member_id: str,
    status: ProviderAssignmentStatus = ProviderAssignmentStatus.ASSIGNED,
) -> ProviderAssignment:
    candidate = _candidate(requirement_id, member_id)
    return ProviderAssignment(
        requirement_id=requirement_id,
        encounter_id="enc-1",
        requirement_type=requirement_id,
        status=status,
        primary_providers=(candidate,) if status == ProviderAssignmentStatus.ASSIGNED else (),
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="test assignment",
    )


def _evidence(member_id: str = "char-a") -> ProviderResponsibilityConflictEvidence:
    return ProviderResponsibilityConflictEvidence(
        encounter_id="enc-1",
        member_id=member_id,
        first_requirement_id="req-a",
        second_requirement_id="req-b",
        source="explicit encounter timing evidence",
        explanation="requirements overlap and cannot be performed by the same member",
    )


def test_same_member_on_two_assignments_is_not_inferred_as_conflict_without_evidence():
    assignments = (
        _assignment("req-a", "char-a"),
        _assignment("req-b", "char-a"),
    )

    result = EncounterProviderResponsibilityService().audit(assignments)

    assert result.is_conflict_free is True
    assert result.conflicts == ()


def test_explicit_double_duty_evidence_reports_conflict_for_same_primary_member():
    assignments = (
        _assignment("req-a", "char-a"),
        _assignment("req-b", "char-a"),
    )

    result = EncounterProviderResponsibilityService().audit(assignments, (_evidence(),))

    assert result.is_conflict_free is False
    assert len(result.conflicts) == 1
    assert result.conflicts[0].member_id == "char-a"
    assert result.conflicts[0].requirement_ids == ("req-a", "req-b")
    assert result.conflicts[0].evidence == (_evidence(),)


def test_explicit_restriction_does_not_conflict_when_requirements_have_different_primaries():
    assignments = (
        _assignment("req-a", "char-a"),
        _assignment("req-b", "char-b"),
    )

    result = EncounterProviderResponsibilityService().audit(assignments, (_evidence(),))

    assert result.is_conflict_free is True


def test_unresolved_assignment_is_not_reported_as_actual_double_duty():
    assignments = (
        _assignment("req-a", "char-a"),
        _assignment("req-b", "char-a", ProviderAssignmentStatus.UNRESOLVED_SELECTION),
    )

    result = EncounterProviderResponsibilityService().audit(assignments, (_evidence(),))

    assert result.is_conflict_free is True


def test_responsibility_evidence_rejects_unknown_requirement_identity():
    assignments = (_assignment("req-a", "char-a"),)

    with pytest.raises(ValueError, match="without an assignment"):
        EncounterProviderResponsibilityService().audit(assignments, (_evidence(),))
