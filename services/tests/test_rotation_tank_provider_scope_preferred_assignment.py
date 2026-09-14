import pytest

from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.encounter_provider_candidate import (
    ProviderCandidate,
    ProviderCandidateStatus,
)
from services.rotation_tank_provider_scope_service import _apply_preferred_assignments


def _candidate(member_id):
    return ProviderCandidate(
        requirement_id="xalvakka:tank:boss_taunt",
        encounter_id="xalvakka",
        requirement_type="taunt",
        member_id=member_id,
        character_name=member_id,
        build_name=f"{member_id} build",
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("canonical taunt",),
    )


def _ambiguous_assignment():
    a = _candidate("tank-a")
    b = _candidate("tank-b")
    return ProviderAssignment(
        requirement_id="xalvakka:tank:boss_taunt",
        encounter_id="xalvakka",
        requirement_type="taunt",
        status=ProviderAssignmentStatus.UNRESOLVED_SELECTION,
        primary_providers=(),
        backup_providers=(a, b),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="two proven viable Tanks",
    )


def test_reviewed_lane_preference_resolves_only_provider_selection_ambiguity():
    result = _apply_preferred_assignments(
        (_ambiguous_assignment(),),
        {"xalvakka:tank:boss_taunt": "tank-a"},
    )[0]

    assert result.status is ProviderAssignmentStatus.ASSIGNED
    assert [row.member_id for row in result.primary_providers] == ["tank-a"]
    assert [row.member_id for row in result.backup_providers] == ["tank-b"]
    assert "reviewed encounter Tank responsibility lane" in result.explanation.casefold().replace("tank", "Tank", 1).casefold()


def test_reviewed_lane_preference_cannot_select_nonviable_member():
    with pytest.raises(ValueError, match="not exactly one proven viable provider"):
        _apply_preferred_assignments(
            (_ambiguous_assignment(),),
            {"xalvakka:tank:boss_taunt": "tank-c"},
        )


def test_reviewed_lane_preference_cannot_override_unresolved_capability():
    assignment = _ambiguous_assignment()
    assignment = ProviderAssignment(
        requirement_id=assignment.requirement_id,
        encounter_id=assignment.encounter_id,
        requirement_type=assignment.requirement_type,
        status=ProviderAssignmentStatus.UNRESOLVED_CAPABILITY,
        primary_providers=(),
        backup_providers=assignment.backup_providers[:1],
        unresolved_candidates=assignment.backup_providers[1:],
        conflicting_candidates=(),
        explanation="capability unresolved",
    )

    with pytest.raises(ValueError, match="cannot override provider state"):
        _apply_preferred_assignments(
            (assignment,),
            {"xalvakka:tank:boss_taunt": "tank-a"},
        )
