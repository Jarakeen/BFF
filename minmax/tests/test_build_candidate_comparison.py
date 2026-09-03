from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild


def _candidate() -> BuildCandidate:
    return BuildCandidate.from_build(
        character_id="magrat-id",
        baseline_build_id="df-healer-id",
        candidate_id="candidate-1",
        candidate_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        changes=(),
        candidate_source="phase12:test",
    )


def test_positive_delta_is_improvement_when_all_constraints_are_preserved():
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.HEALING,
        baseline_value=100.0,
        candidate_value=105.0,
        constraints=(
            CandidateConstraint("sustain", ConstraintStatus.PRESERVED, "unchanged"),
        ),
    )
    assert comparison.is_improvement is True
    assert comparison.is_preferred is True


def test_constraint_repair_can_be_preferred_with_negative_objective_delta():
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.HEALING,
        baseline_value=100.0,
        candidate_value=95.0,
        constraints=(
            CandidateConstraint(
                "magicka sustain",
                ConstraintStatus.REPAIRED,
                "Candidate repairs failed baseline magicka sustain.",
            ),
        ),
    )
    assert comparison.delta == -5.0
    assert comparison.is_rankable is True
    assert comparison.is_improvement is False
    assert comparison.is_constraint_repair is True
    assert comparison.is_preferred is True


def test_unknown_sustain_blocks_ranking_even_with_positive_objective_delta():
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=110.0,
        constraints=(CandidateConstraint("sustain", ConstraintStatus.UNKNOWN, "unknown"),),
    )
    assert comparison.is_rankable is False
    assert comparison.is_preferred is False


def test_lost_provider_responsibility_blocks_ranking():
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=120.0,
        constraints=(
            CandidateConstraint("provider:force", ConstraintStatus.WORSENED, "lost duty"),
        ),
    )
    assert comparison.is_rankable is False


def test_missing_objective_measurement_is_not_rankable():
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.HEALING,
        baseline_value=100.0,
        candidate_value=None,
        constraints=(),
        unresolved=("candidate healing objective is unresolved",),
    )
    assert comparison.delta is None
    assert comparison.is_rankable is False
