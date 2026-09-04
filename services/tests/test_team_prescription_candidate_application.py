from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_candidate_application import (
    apply_ranked_candidate_to_prescribed_roster,
)
from services.team_prescription_candidate_ranking import (
    PrescribedSlotCandidateEvidence,
    rank_prescribed_slot_candidates,
)


def _comparison(*, candidate_id: str, value: float = 125.0) -> BuildCandidateComparison:
    build = PlayerBuild(
        Name="Prescription Candidate",
        BuildName="Provider DD",
        EsoClass="Arcanist",
        Race="Dark Elf",
        Role="Support DD",
    )
    build.Armor["Chest"]["Set"] = "Test Support Set"
    build.Necklace.Set = "Test Damage Set"
    candidate = BuildCandidate.from_build(
        character_id=f"candidate:{candidate_id}",
        baseline_build_id="prescription-baseline",
        candidate_id=candidate_id,
        candidate_build=build,
        changes=(),
        candidate_source="phase13:test-prescription-application",
    )
    return BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=value,
        constraints=(
            CandidateConstraint(
                name="hard constraint",
                status=ConstraintStatus.PRESERVED,
                explanation="structural test constraint",
            ),
        ),
    )


def _roster(scope: TeamPrescriptionScope) -> PrescribedRoster:
    return PrescribedRoster(
        name="Godslayer Prescription",
        goal="Godslayer",
        scope=scope,
        assignments=(
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=(
                    "DD 1: no compatible saved player is available; candidate/recruitment prescription is required",
                ),
            ),
        ),
        unresolved=(
            "DD 1: no compatible saved player is available; candidate/recruitment prescription is required",
        ),
    )


def test_recommended_candidate_populates_only_allowed_prescription_dimensions() -> None:
    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=("sunspire:coverage:test",),
        candidates=(
            PrescribedSlotCandidateEvidence(
                comparison=_comparison(candidate_id="provider-dd"),
                provider_requirement_ids=("sunspire:coverage:test",),
            ),
        ),
    )
    roster = _roster(
        TeamPrescriptionScope(
            dimensions=(
                PrescriptionDimension.CLASS,
                PrescriptionDimension.BUILD,
                PrescriptionDimension.GEAR,
            )
        )
    )

    result = apply_ranked_candidate_to_prescribed_roster(roster=roster, ranking=ranking)
    assignment = result.assignments[0]

    assert assignment.player_name is None
    assert assignment.source_build_name == "Provider DD"
    assert assignment.change_for(PrescriptionDimension.CLASS).prescribed_value == "Arcanist"
    assert assignment.change_for(PrescriptionDimension.BUILD).prescribed_value == "Provider DD"
    assert assignment.change_for(PrescriptionDimension.GEAR).prescribed_value == "Test Support Set + Test Damage Set"
    assert assignment.change_for(PrescriptionDimension.RACE) is None
    assert assignment.unresolved == ()
    assert result.unresolved == ()
    assert "sunspire:coverage:test" in assignment.changes[0].reason


def test_tied_ranking_keeps_slot_unresolved() -> None:
    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=(),
        candidates=(
            PrescribedSlotCandidateEvidence(comparison=_comparison(candidate_id="alpha")),
            PrescribedSlotCandidateEvidence(comparison=_comparison(candidate_id="beta")),
        ),
    )
    roster = _roster(TeamPrescriptionScope(dimensions=(PrescriptionDimension.CLASS,)))

    result = apply_ranked_candidate_to_prescribed_roster(roster=roster, ranking=ranking)

    assert result.assignments[0].changes == ()
    assert any("equally supported top candidates" in value for value in result.assignments[0].unresolved)


def test_application_refuses_to_replace_anchored_saved_player() -> None:
    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=(),
        candidates=(PrescribedSlotCandidateEvidence(comparison=_comparison(candidate_id="winner")),),
    )
    roster = PrescribedRoster(
        name="Anchored",
        goal="Godslayer",
        scope=TeamPrescriptionScope(dimensions=(PrescriptionDimension.CLASS,)),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name="Existing Player",
                source_build_name="Existing Build",
                prescribed_role="DD",
            ),
        ),
    )

    import pytest

    with pytest.raises(ValueError, match="cannot replace anchored saved player"):
        apply_ranked_candidate_to_prescribed_roster(roster=roster, ranking=ranking)
