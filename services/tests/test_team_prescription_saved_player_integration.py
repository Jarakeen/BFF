from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    TeamPrescriptionScope,
)
from services.team_prescription_candidate_ranking import PrescribedSlotCandidateEvidence
from services.team_prescription_candidate_source import (
    PrescribedObjectiveMeasurement,
    PrescribedOpenSlotCandidate,
    PrescribedOpenSlotCandidateEvidence,
)
from services.team_prescription_generator import generate_prescribed_roster_from_saved_builds
from services.team_prescription_optimizer import optimize_prescribed_roster_candidates


def _build(player: str, build_name: str, *, role: str = "DD") -> PlayerBuild:
    return PlayerBuild(
        Name=player,
        BuildName=build_name,
        Role=role,
        EsoClass="Arcanist" if role == "DD" else "Warden",
    )


def _evidence(
    candidate_id: str,
    player: str,
    build_name: str,
    value: float,
) -> PrescribedSlotCandidateEvidence:
    candidate = PrescribedOpenSlotCandidate.from_build(
        candidate_id=candidate_id,
        candidate_build=_build(player, build_name),
        candidate_source="saved-build-test",
        player_name=player,
    )
    measurement = PrescribedObjectiveMeasurement(
        objective=EvaluationObjective.DAMAGE,
        value=value,
        metric_name="canonical single-event expected damage",
        constraints=(
            CandidateConstraint(
                name="magicka sustain",
                status=ConstraintStatus.PRESERVED,
                explanation="test evidence",
            ),
        ),
    )
    return PrescribedSlotCandidateEvidence(
        open_slot=PrescribedOpenSlotCandidateEvidence(
            candidate=candidate,
            measurement=measurement,
        )
    )


def test_saved_anchor_generator_does_not_turn_multiple_builds_into_multiple_people() -> None:
    roster = generate_prescribed_roster_from_saved_builds(
        name="One Human, Several Builds",
        goal="Custom Goal",
        slot_labels=("DD 1", "DD 2"),
        builds=(
            _build("Keen", "Parse"),
            _build("Keen", "Support DD"),
        ),
        scope=TeamPrescriptionScope(),
    )

    assert roster.assignments[0].player_name == "Keen"
    assert roster.assignments[1].player_name is None
    assert len(roster.unresolved) == 1


def test_saved_player_candidate_becomes_real_roster_assignment() -> None:
    roster = PrescribedRoster(
        name="Saved Player Prescription",
        goal="Custom Goal",
        scope=TeamPrescriptionScope(),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=("DD 1: requires evidence",),
            ),
        ),
        unresolved=("DD 1: requires evidence",),
    )

    result = optimize_prescribed_roster_candidates(
        roster=roster,
        candidate_pools={"DD 1": (_evidence("keen", "Keen", "Parse", 150.0),)},
    )

    assignment = result.final_roster.assignments[0]
    assert result.applied_count == 1
    assert assignment.player_name == "Keen"
    assert assignment.source_build_name == "Parse"
    assert assignment.changes == ()
    assert result.final_roster.unresolved == ()


def test_optimizer_consumes_one_saved_player_only_once_across_slots() -> None:
    roster = PrescribedRoster(
        name="No Human Cloning",
        goal="Custom Goal",
        scope=TeamPrescriptionScope(),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=("DD 1: requires evidence",),
            ),
            PrescribedRosterAssignment(
                slot_name="DD 2",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=("DD 2: requires evidence",),
            ),
        ),
        unresolved=("DD 1: requires evidence", "DD 2: requires evidence"),
    )
    pool = (
        _evidence("keen-parse", "Keen", "Parse", 150.0),
        _evidence("keen-support", "Keen", "Support DD", 140.0),
        _evidence("rylo", "Rylo", "Parse", 120.0),
    )

    result = optimize_prescribed_roster_candidates(
        roster=roster,
        candidate_pools={"DD 1": pool, "DD 2": pool},
    )

    assert [row.player_name for row in result.final_roster.assignments] == ["Keen", "Rylo"]
    assert result.applied_count == 2
    assert result.final_roster.unresolved == ()
