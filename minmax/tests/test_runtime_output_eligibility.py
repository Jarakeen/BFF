import pytest

from minmax.runtime_output_eligibility import (
    RuntimeOutputEligibilityRule,
    evaluate_runtime_output_eligibility,
)


def test_missing_condition_context_fails_closed_as_unresolved() -> None:
    rule = RuntimeOutputEligibilityRule(
        required_conditions=("target_in_effect_geometry",),
        source="reviewed mechanic",
    )

    result = evaluate_runtime_output_eligibility(rule, None)

    assert result.eligible is False
    assert result.resolved is False
    assert result.reasons == ("condition_context_required",)
    assert result.missing_conditions == ("target_in_effect_geometry",)


def test_known_empty_context_is_resolved_ineligible() -> None:
    rule = RuntimeOutputEligibilityRule(
        required_conditions=("target_in_effect_geometry",),
        source="reviewed mechanic",
    )

    result = evaluate_runtime_output_eligibility(rule, frozenset())

    assert result.eligible is False
    assert result.resolved is True
    assert result.reasons == ("condition_unsatisfied",)
    assert result.missing_conditions == ("target_in_effect_geometry",)


def test_all_required_conditions_use_and_semantics() -> None:
    rule = RuntimeOutputEligibilityRule(
        required_conditions=("condition_a", "condition_b"),
        source="reviewed mechanic",
    )

    partial = evaluate_runtime_output_eligibility(rule, frozenset({"condition_a"}))
    complete = evaluate_runtime_output_eligibility(
        rule,
        frozenset({"condition_a", "condition_b", "irrelevant_condition"}),
    )

    assert partial.eligible is False
    assert partial.resolved is True
    assert partial.missing_conditions == ("condition_b",)
    assert complete.eligible is True
    assert complete.resolved is True
    assert complete.missing_conditions == ()
    assert complete.reasons == ()


def test_rule_normalizes_duplicate_condition_names_and_requires_provenance() -> None:
    rule = RuntimeOutputEligibilityRule(
        required_conditions=(" condition_a ", "condition_a", "condition_b"),
        source=" reviewed source ",
    )

    assert rule.required_conditions == ("condition_a", "condition_b")
    assert rule.source == "reviewed source"

    with pytest.raises(ValueError):
        RuntimeOutputEligibilityRule(required_conditions=(), source="reviewed")
    with pytest.raises(ValueError):
        RuntimeOutputEligibilityRule(required_conditions=("condition",), source="")
