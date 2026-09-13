import pytest

from minmax.runtime_output_eligibility import RuntimeOutputEligibilityRule
from services.rotation_runtime_output_eligibility_service import (
    DETONATING_SIPHON_GEOMETRY_CONDITION,
    RotationRuntimeOutputConditionRule,
    RotationRuntimeOutputEligibilityService,
)


def test_unreviewed_component_passes_through_without_condition_context() -> None:
    result = RotationRuntimeOutputEligibilityService().evaluate(
        skill_entity_id="stampede",
        coefficient_number=2,
        condition_context=None,
    )

    assert result.has_rule is False
    assert result.eligible is True
    assert result.resolved is True
    assert result.unresolved == ()


def test_detonating_siphon_fails_closed_without_geometry_context() -> None:
    result = RotationRuntimeOutputEligibilityService().evaluate(
        skill_entity_id="Detonating Siphon",
        coefficient_number=1,
        condition_context=None,
    )

    assert result.has_rule is True
    assert result.eligible is False
    assert result.resolved is False
    assert result.required_conditions == (DETONATING_SIPHON_GEOMETRY_CONDITION,)
    assert result.missing_conditions == (DETONATING_SIPHON_GEOMETRY_CONDITION,)
    assert "authoritative ConditionContext" in result.unresolved[0]


def test_detonating_siphon_known_outside_geometry_is_resolved_zero_eligibility() -> None:
    result = RotationRuntimeOutputEligibilityService().evaluate(
        skill_entity_id="detonating_siphon",
        coefficient_number=1,
        condition_context=frozenset(),
    )

    assert result.has_rule is True
    assert result.eligible is False
    assert result.resolved is True
    assert result.unresolved == ()
    assert result.missing_conditions == (DETONATING_SIPHON_GEOMETRY_CONDITION,)


def test_detonating_siphon_known_inside_geometry_is_eligible() -> None:
    result = RotationRuntimeOutputEligibilityService().evaluate(
        skill_entity_id="detonating_siphon",
        coefficient_number=1,
        condition_context=frozenset({DETONATING_SIPHON_GEOMETRY_CONDITION}),
    )

    assert result.has_rule is True
    assert result.eligible is True
    assert result.resolved is True
    assert result.missing_conditions == ()
    assert result.unresolved == ()


def test_custom_rules_are_canonicalized_and_duplicates_fail_closed_at_configuration() -> None:
    rule = RotationRuntimeOutputConditionRule(
        skill_entity_id="Example Skill",
        coefficient_number=2,
        eligibility=RuntimeOutputEligibilityRule(
            required_conditions=("condition_a",),
            source="test",
        ),
    )
    service = RotationRuntimeOutputEligibilityService((rule,))

    assert service.rule_for("example_skill", 2) == rule

    with pytest.raises(ValueError):
        RotationRuntimeOutputEligibilityService((rule, rule))
