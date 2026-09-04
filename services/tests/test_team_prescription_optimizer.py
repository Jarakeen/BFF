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
from services.team_prescription_candidate_ranking import PrescribedSlotCandidateEvidence
from services.team_prescription_optimizer import optimize_prescribed_roster_candidates


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


def _evidence(
    *,
    candidate_id: str,
    role: str = "DD",
    value: float = 120.0,
    eso_class: str = "Arcanist",
    provider_ids: tuple[str, ...] = (),
    status: ConstraintStatus = ConstraintStatus.PRESERVED,
) -> PrescribedSlotCandidateEvidence:
    build = PlayerBuild(
        Name=candidate_id,
        BuildName=f"{candidate_id} Build",
        Role=role,
        EsoClass=eso_class,
    )
    candidate = BuildCandidate.from_build(
        character_id=f"candidate:{candidate_id}",
        baseline_build_id="prescription-baseline",
        candidate_id=candidate_id,
        candidate_build=build,
        changes=(),
        candidate_source="phase13:test-prescription-optimizer",
    )
    comparison = BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=value,
        constraints=(
            CandidateConstraint(
                name="hard constraint",
                status=status,
                explanation="structural test constraint",
            ),
        ),
    )
    return PrescribedSlotCandidateEvidence(
        comparison=comparison,
        provider_requirement_ids=provider_ids,
    )


def test_optimizer_applies_unique_supported_winner_and_preserves_anchors() -> None:
    roster = _roster()
    result = optimize_prescribed_roster_candidates(
        roster=roster,
        candidate_pools={
            "DD 1": (
                _evidence(candidate_id="lower", value=115.0),
                _evidence(candidate_id="winner", value=130.0),
            ),
        },
    )

    assert result.applied_count == 1
    assert result.final_roster.assignments[0] == roster.assignments[0]
    assert result.final_roster.assignments[1] == roster.assignments[1]
    prescribed = result.final_roster.assignments[2]
    assert prescribed.player_name is None
    assert prescribed.source_build_name == "winner Build"
    assert prescribed.change_for(PrescriptionDimension.CLASS).prescribed_value == "Arcanist"
    assert prescribed.change_for(PrescriptionDimension.BUILD).prescribed_value == "winner Build"
    assert result.final_roster.assignments[3].unresolved


def test_optimizer_keeps_missing_candidate_pool_explicitly_unresolved() -> None:
    result = optimize_prescribed_roster_candidates(
        roster=_roster(),
        candidate_pools={},
    )

    assert result.applied_count == 0
    assert len(result.unresolved) == 2
    assert "no evaluated candidate pool" in result.unresolved[0]
    assert result.final_roster == result.original_roster


def test_optimizer_enforces_provider_requirement_before_objective_value() -> None:
    result = optimize_prescribed_roster_candidates(
        roster=_roster(),
        provider_requirements_by_slot={"DD 1": ("sunspire:provider",)},
        candidate_pools={
            "DD 1": (
                _evidence(candidate_id="raw-damage", value=150.0),
                _evidence(
                    candidate_id="provider",
                    value=125.0,
                    provider_ids=("sunspire:provider",),
                ),
            ),
        },
    )

    prescribed = result.final_roster.assignments[2]
    assert prescribed.source_build_name == "provider Build"
    assert result.slots[2].ranking is not None
    assert result.slots[2].ranking.recommended is not None


def test_optimizer_does_not_break_tie_or_apply_unrankable_candidate() -> None:
    result = optimize_prescribed_roster_candidates(
        roster=_roster(),
        candidate_pools={
            "DD 1": (
                _evidence(candidate_id="alpha", value=130.0),
                _evidence(candidate_id="beta", value=130.0),
            ),
            "DD 2": (
                _evidence(
                    candidate_id="unsafe",
                    value=160.0,
                    status=ConstraintStatus.UNSATISFIED,
                ),
            ),
        },
    )

    assert result.applied_count == 0
    assert result.final_roster.assignments[2].source_build_name is None
    assert result.final_roster.assignments[3].source_build_name is None
    assert "equally supported top candidates" in result.slots[2].unresolved[0]
    assert "no eligible Phase 12 candidate" in result.slots[3].unresolved[0]
