from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.encounter_provider_candidate import ProviderCandidate, ProviderCandidateStatus
from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    TeamPrescriptionScope,
)
from services.team_prescription_provider_coverage import (
    project_provider_coverage_into_prescription,
)


def _candidate(name: str, requirement_id: str = "sunspire:war_horn") -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id=requirement_id,
        encounter_id="sunspire",
        requirement_type="war_horn",
        member_id=name.casefold().replace(" ", "-"),
        character_name=name,
        build_name=f"{name} Build",
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("test",),
    )


def _roster() -> PrescribedRoster:
    return PrescribedRoster(
        name="Godslayer Prescribed Roster",
        goal="Godslayer",
        scope=TeamPrescriptionScope(),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Main Tank",
                player_name="Necro Tank",
                source_build_name="Tank Build",
                prescribed_role="Tank",
            ),
            PrescribedRosterAssignment(
                slot_name="Healer 1",
                player_name="Warden Healer",
                source_build_name="Heal Build",
                prescribed_role="Healer",
            ),
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=("DD 1 requires a prescription",),
            ),
        ),
        unresolved=("DD 1 requires a prescription",),
    )


def test_assigned_provider_on_saved_anchor_is_recorded_as_satisfied() -> None:
    provider = _candidate("Warden Healer")
    assignment = ProviderAssignment(
        requirement_id=provider.requirement_id,
        encounter_id="sunspire",
        requirement_type="war_horn",
        status=ProviderAssignmentStatus.ASSIGNED,
        primary_providers=(provider,),
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="unique provider",
    )

    result = project_provider_coverage_into_prescription(
        roster=_roster(),
        provider_assignments=(assignment,),
    )

    assert result.satisfied_requirement_ids == ("sunspire:war_horn",)
    assert result.unresolved_requirement_ids == ()
    assert any("assigned to Warden Healer" in line for line in result.roster.assumptions)


def test_insufficient_provider_requirement_remains_hard_unresolved_constraint() -> None:
    assignment = ProviderAssignment(
        requirement_id="sunspire:major_vulnerability",
        encounter_id="sunspire",
        requirement_type="major_vulnerability",
        status=ProviderAssignmentStatus.INSUFFICIENT,
        primary_providers=(),
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="No proven provider is available.",
    )

    result = project_provider_coverage_into_prescription(
        roster=_roster(),
        provider_assignments=(assignment,),
    )

    assert result.satisfied_requirement_ids == ()
    assert result.unresolved_requirement_ids == ("sunspire:major_vulnerability",)
    assert any(
        "sunspire:major_vulnerability" in line and "insufficient" in line
        for line in result.roster.unresolved
    )


def test_unresolved_selection_does_not_choose_provider_by_roster_order() -> None:
    first = _candidate("Necro Tank")
    second = _candidate("Warden Healer")
    assignment = ProviderAssignment(
        requirement_id=first.requirement_id,
        encounter_id="sunspire",
        requirement_type="war_horn",
        status=ProviderAssignmentStatus.UNRESOLVED_SELECTION,
        primary_providers=(),
        backup_providers=(first, second),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="Two viable providers remain and no suitability rule distinguishes them.",
    )

    result = project_provider_coverage_into_prescription(
        roster=_roster(),
        provider_assignments=(assignment,),
    )

    assert result.satisfied_requirement_ids == ()
    assert result.unresolved_requirement_ids == ("sunspire:war_horn",)
    assert not any("assigned to Necro Tank" in line for line in result.roster.assumptions)


def test_assigned_provider_missing_from_prescription_anchor_is_not_treated_as_satisfied() -> None:
    provider = _candidate("External Player")
    assignment = ProviderAssignment(
        requirement_id=provider.requirement_id,
        encounter_id="sunspire",
        requirement_type="war_horn",
        status=ProviderAssignmentStatus.ASSIGNED,
        primary_providers=(provider,),
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="assigned elsewhere",
    )

    result = project_provider_coverage_into_prescription(
        roster=_roster(),
        provider_assignments=(assignment,),
    )

    assert result.satisfied_requirement_ids == ()
    assert result.unresolved_requirement_ids == ("sunspire:war_horn",)
    assert any("not present as saved-player anchors" in line for line in result.roster.unresolved)
