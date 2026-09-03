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
            CandidateConstraint(
                name="sustain",
                status=ConstraintStatus.PRESERVED,
                explanation="Phase 4 sustain result is unchanged.",
            ),
            CandidateConstraint(
                name="provider:force",
                status=ConstraintStatus.PRESERVED,
                explanation="Aggressive Horn remains available to the assigned provider.",
            ),
        ),
    )

    assert comparison.delta == 5.0
    assert comparison.is_rankable is True
    assert comparison.is_improvement is True


def test_unknown_sustain_blocks_ranking_even_with_positive_objective_delta():
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=110.0,
        constraints=(
            CandidateConstraint(
                name="sustain",
                status=ConstraintStatus.UNKNOWN,
                explanation="Candidate sustain has not been evaluated by Phase 4.",
            ),
        ),
    )

    assert comparison.delta == 10.0
    assert comparison.is_rankable is False
    assert comparison.is_improvement is False
    assert comparison.blocking_constraints[0].name == "sustain"


def test_lost_provider_responsibility_blocks_ranking():
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=120.0,
        constraints=(
            CandidateConstraint(
                name="provider:force",
                status=ConstraintStatus.WORSENED,
                explanation="Candidate removes Aggressive Horn from Magrat's build.",
            ),
        ),
    )

    assert comparison.is_rankable is False
    assert comparison.is_improvement is False


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
