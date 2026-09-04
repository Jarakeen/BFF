from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from services.team_prescription_candidate_ranking import (
    PrescribedSlotCandidateEvidence,
    rank_prescribed_slot_candidates,
)


def _comparison(
    *,
    candidate_id: str,
    role: str,
    value: float,
    constraint_status: ConstraintStatus = ConstraintStatus.PRESERVED,
) -> BuildCandidateComparison:
    candidate = BuildCandidate.from_build(
        character_id=f"candidate:{candidate_id}",
        baseline_build_id="prescription-baseline",
        candidate_id=candidate_id,
        candidate_build=PlayerBuild(
            Name=candidate_id,
            BuildName=f"{candidate_id} Build",
            Role=role,
        ),
        changes=(),
        candidate_source="phase13:test-prescription",
    )
    return BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=value,
        constraints=(
            CandidateConstraint(
                name="hard constraint",
                status=constraint_status,
                explanation="structural test constraint",
            ),
        ),
    )


def test_higher_objective_role_mismatch_cannot_take_dd_slot() -> None:
    healer = PrescribedSlotCandidateEvidence(
        comparison=_comparison(candidate_id="healer", role="Healer", value=140.0),
    )
    dd = PrescribedSlotCandidateEvidence(
        comparison=_comparison(candidate_id="dd", role="DD", value=120.0),
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=(),
        candidates=(healer, dd),
    )

    assert ranking.recommended is dd
    assert ranking.rejected[0].candidate_id == "healer"
    assert "role mismatch" in ranking.rejected[0].reasons[0]


def test_provider_requirement_blocks_higher_objective_candidate_without_coverage() -> None:
    uncovered = PrescribedSlotCandidateEvidence(
        comparison=_comparison(candidate_id="raw-damage", role="DD", value=140.0),
    )
    provider = PrescribedSlotCandidateEvidence(
        comparison=_comparison(candidate_id="provider-dd", role="Support DD", value=125.0),
        provider_requirement_ids=("sunspire:coverage:required-provider",),
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=("sunspire:coverage:required-provider",),
        candidates=(uncovered, provider),
    )

    assert ranking.recommended is provider
    rejected = next(row for row in ranking.rejected if row.candidate_id == "raw-damage")
    assert "missing required provider evidence" in rejected.reasons[0]


def test_phase12_unrankable_candidate_remains_blocked_at_team_scale() -> None:
    blocked = PrescribedSlotCandidateEvidence(
        comparison=_comparison(
            candidate_id="unsafe",
            role="DD",
            value=160.0,
            constraint_status=ConstraintStatus.UNSATISFIED,
        ),
    )
    safe = PrescribedSlotCandidateEvidence(
        comparison=_comparison(candidate_id="safe", role="DD", value=120.0),
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=(),
        candidates=(blocked, safe),
    )

    assert ranking.recommended is safe
    rejected = next(row for row in ranking.rejected if row.candidate_id == "unsafe")
    assert "Phase 12 comparison is not rankable" in rejected.reasons


def test_equally_supported_top_candidates_remain_unresolved() -> None:
    first = PrescribedSlotCandidateEvidence(
        comparison=_comparison(candidate_id="alpha", role="DD", value=125.0),
    )
    second = PrescribedSlotCandidateEvidence(
        comparison=_comparison(candidate_id="beta", role="DD", value=125.0),
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=(),
        candidates=(first, second),
    )

    assert ranking.recommended is None
    assert {row.comparison.candidate.candidate_id for row in ranking.recommended_ties} == {
        "alpha",
        "beta",
    }
    assert "equally supported top candidates" in ranking.unresolved[0]
