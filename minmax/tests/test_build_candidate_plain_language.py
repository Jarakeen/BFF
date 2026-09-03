from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus
from minmax.build_candidate_plain_language import (
    constraint_plain_english,
    recommendation_reason_plain_english,
)


def _constraint(name: str, status: ConstraintStatus) -> CandidateConstraint:
    return CandidateConstraint(name=name, status=status, explanation="technical evidence")


def test_sustain_repair_is_explained_without_optimizer_jargon() -> None:
    text = constraint_plain_english(
        _constraint("magicka sustain", ConstraintStatus.REPAIRED)
    )

    assert "fixes the resource problem" in text
    assert "repaired" not in text.casefold()


def test_unsatisfied_sustain_says_candidate_cannot_be_recommended() -> None:
    text = constraint_plain_english(
        _constraint("magicka sustain", ConstraintStatus.UNSATISFIED)
    )

    assert "runs out" in text
    assert "cannot be recommended" in text


def test_capability_preservation_names_user_visible_build_value() -> None:
    text = constraint_plain_english(
        _constraint("capability_coverage", ConstraintStatus.PRESERVED)
    )

    assert "buffs, debuffs" in text
    assert "current build provides" in text


def test_provider_failure_explains_assigned_raid_job() -> None:
    text = constraint_plain_english(
        _constraint("provider_responsibility", ConstraintStatus.WORSENED)
    )

    assert "assigned raid job" in text
    assert "blocked" in text


def test_unknown_provider_result_refuses_to_guess() -> None:
    text = constraint_plain_english(
        _constraint("provider_responsibility", ConstraintStatus.UNKNOWN)
    )

    assert "cannot prove" in text
    assert "will not guess" in text


def test_constraint_repair_reason_explains_zero_delta_recommendation() -> None:
    text = recommendation_reason_plain_english(
        is_constraint_repair=True,
        delta=0.0,
    )

    assert "fixes a required problem" in text
    assert "without a higher modeled score" in text


def test_positive_objective_reason_requires_passing_checks() -> None:
    text = recommendation_reason_plain_english(
        is_constraint_repair=False,
        delta=12.5,
    )

    assert "passes the required checks" in text
    assert "improves the modeled result" in text
