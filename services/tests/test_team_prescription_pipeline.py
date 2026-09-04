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
from services.team_prescription_candidate_pool import PrescribedCandidatePoolInput
from services.team_prescription_pipeline import run_team_prescription_candidate_pipeline


def _comparison(
    *,
    candidate_id: str,
    value: float,
    provider_ids: tuple[str, ...] = (),
) -> PrescribedCandidatePoolInput:
    build = PlayerBuild(
        Name=candidate_id,
        BuildName=f"{candidate_id} Build",
        Role="DD",
        EsoClass="Arcanist",
    )
    candidate = BuildCandidate.from_build(
        character_id=f"candidate:{candidate_id}",
        baseline_build_id="baseline",
        candidate_id=candidate_id,
        candidate_build=build,
        changes=(),
        candidate_source="phase13:test-pipeline",
    )
    comparison = BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=value,
        constraints=(
            CandidateConstraint(
                name="hard",
                status=ConstraintStatus.PRESERVED,
                explanation="structural test",
            ),
        ),
    )
    return PrescribedCandidatePoolInput(
        slot_name="DD 1",
        comparison=comparison,
        provider_requirement_ids=provider_ids,
    )


def _roster() -> PrescribedRoster:
    return PrescribedRoster(
        name="Godslayer Prescribed Roster",
        goal="Godslayer",
        scope=TeamPrescriptionScope(
            dimensions=(PrescriptionDimension.CLASS, PrescriptionDimension.BUILD)
        ),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Main Tank",
                player_name="Susan",
                source_build_name="Necro Tank",
                prescribed_role="Tank",
            ),
            PrescribedRosterAssignment(
                slot_name="Healer 1",
                player_name="Magrat",
                source_build_name="DF Healer",
                prescribed_role="Healer",
            ),
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=("DD 1: requires an evidence-backed candidate",),
            ),
            PrescribedRosterAssignment(
                slot_name="DD 2",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=("DD 2: requires an evidence-backed candidate",),
            ),
        ),
        unresolved=(
            "DD 1: requires an evidence-backed candidate",
            "DD 2: requires an evidence-backed candidate",
        ),
    )


def test_pipeline_groups_ranks_and_applies_supported_candidate_end_to_end() -> None:
    result = run_team_prescription_candidate_pipeline(
        roster=_roster(),
        candidate_inputs=(
            _comparison(candidate_id="raw-damage", value=150.0),
            _comparison(
                candidate_id="provider-dd",
                value=125.0,
                provider_ids=("sunspire:provider",),
            ),
        ),
        provider_requirements_by_slot={"DD 1": ("sunspire:provider",)},
    )

    assert result.optimization.applied_count == 1
    assert result.final_roster.assignments[0].player_name == "Susan"
    assert result.final_roster.assignments[1].player_name == "Magrat"
    prescribed = result.final_roster.assignments[2]
    assert prescribed.player_name is None
    assert prescribed.source_build_name == "provider-dd Build"
    assert prescribed.change_for(PrescriptionDimension.CLASS).prescribed_value == "Arcanist"
    assert prescribed.change_for(PrescriptionDimension.BUILD).prescribed_value == "provider-dd Build"
    assert result.final_roster.assignments[3].source_build_name is None
    assert any("DD 2" in message for message in result.unresolved)
