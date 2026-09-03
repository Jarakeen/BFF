from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_comparison import BuildCandidateComparison, CandidateConstraint, ConstraintStatus
from minmax.build_candidate_evaluator import rank_candidate_comparisons
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild


def _comparison(candidate_id: str, delta: float) -> BuildCandidateComparison:
    candidate = BuildCandidate.from_build(
        character_id="magrat",
        baseline_build_id="df-healer",
        candidate_id=candidate_id,
        candidate_build=PlayerBuild(BuildName="DF Healer"),
        changes=(),
        candidate_source="test",
    )
    return BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.HEALING,
        baseline_value=100.0,
        candidate_value=100.0 + delta,
        constraints=(
            CandidateConstraint(
                name="magicka sustain",
                status=ConstraintStatus.REPAIRED,
                explanation="Candidate repairs failed baseline magicka sustain.",
            ),
        ),
    )


def test_ranking_recommends_least_objective_cost_constraint_repair() -> None:
    mage = _comparison("df-healer:mundus:mage", -4.0)
    atronach = _comparison("df-healer:mundus:atronach", -10.0)

    result = rank_candidate_comparisons((atronach, mage))

    assert result.ranked == (mage, atronach)
    assert result.recommended is mage
    assert result.recommended.is_constraint_repair
    assert not result.recommended.is_improvement
