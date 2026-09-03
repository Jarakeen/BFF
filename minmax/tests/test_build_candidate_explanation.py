from minmax.build_candidate import BuildCandidate, BuildChange
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.build_candidate_explanation import (
    BuildCandidateExplanation,
    CandidateRecommendationReason,
)
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild


def _candidate() -> BuildCandidate:
    return BuildCandidate.from_build(
        character_id="magrat-id",
        baseline_build_id="df-healer-id",
        candidate_id="mundus:the-thief",
        candidate_build=PlayerBuild(
            Name="Magrat",
            BuildName="DF Healer",
            Mundus="The Thief",
        ),
        changes=(
            BuildChange.from_values(
                path="Mundus",
                before="The Ritual",
                after="The Thief",
                source="canonical:mundus",
            ),
        ),
        candidate_source="phase12:mundus",
    )


def test_explanation_preserves_exact_changed_inputs_and_objective_measurements() -> None:
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=112.5,
        constraints=(
            CandidateConstraint(
                "magicka sustain",
                ConstraintStatus.PRESERVED,
                "Candidate preserves modeled magicka sustain.",
            ),
        ),
        evidence=("baseline: canonical damage", "candidate: canonical damage"),
    )

    explanation = BuildCandidateExplanation.from_comparison(comparison)

    assert explanation.candidate_id == "mundus:the-thief"
    assert explanation.candidate_source == "phase12:mundus"
    assert explanation.objective_name == EvaluationObjective.DAMAGE.value
    assert explanation.baseline_value == 100.0
    assert explanation.candidate_value == 112.5
    assert explanation.delta == 12.5
    assert explanation.changes[0].path == "Mundus"
    assert explanation.changes[0].before == "The Ritual"
    assert explanation.changes[0].after == "The Thief"
    assert explanation.changes[0].source == "canonical:mundus"
    assert explanation.evidence == (
        "baseline: canonical damage",
        "candidate: canonical damage",
    )


def test_positive_objective_with_preserved_constraints_is_explained_as_improvement() -> None:
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=110.0,
        constraints=(
            CandidateConstraint("raid capability", ConstraintStatus.PRESERVED, "preserved"),
            CandidateConstraint(
                "provider responsibilities",
                ConstraintStatus.PRESERVED,
                "assigned duties preserved",
            ),
        ),
    )

    explanation = BuildCandidateExplanation.from_comparison(comparison)

    assert explanation.is_rankable is True
    assert explanation.is_preferred is True
    assert explanation.recommendation_reason is CandidateRecommendationReason.OBJECTIVE_IMPROVEMENT


def test_constraint_repair_reason_is_preserved_even_when_objective_declines() -> None:
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=95.0,
        constraints=(
            CandidateConstraint(
                "magicka sustain",
                ConstraintStatus.REPAIRED,
                "Candidate repairs failed baseline sustain.",
            ),
        ),
    )

    explanation = BuildCandidateExplanation.from_comparison(comparison)

    assert explanation.delta == -5.0
    assert explanation.is_preferred is True
    assert explanation.recommendation_reason is CandidateRecommendationReason.HARD_CONSTRAINT_REPAIR


def test_higher_objective_with_lost_provider_duty_is_explained_as_blocked() -> None:
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=125.0,
        constraints=(
            CandidateConstraint(
                "provider responsibilities",
                ConstraintStatus.WORSENED,
                "Candidate loses an assigned provider duty.",
            ),
        ),
    )

    explanation = BuildCandidateExplanation.from_comparison(comparison)

    assert explanation.delta == 25.0
    assert explanation.is_rankable is False
    assert explanation.is_preferred is False
    assert explanation.recommendation_reason is CandidateRecommendationReason.BLOCKED
    assert explanation.constraints[0].status is ConstraintStatus.WORSENED


def test_unresolved_objective_is_never_explained_as_a_recommendation() -> None:
    comparison = BuildCandidateComparison(
        candidate=_candidate(),
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=None,
        constraints=(
            CandidateConstraint("magicka sustain", ConstraintStatus.PRESERVED, "preserved"),
        ),
        unresolved=("candidate objective coverage is unresolved",),
    )

    explanation = BuildCandidateExplanation.from_comparison(comparison)

    assert explanation.delta is None
    assert explanation.is_rankable is False
    assert explanation.is_preferred is False
    assert explanation.unresolved == ("candidate objective coverage is unresolved",)
    assert explanation.recommendation_reason is CandidateRecommendationReason.UNRESOLVED
