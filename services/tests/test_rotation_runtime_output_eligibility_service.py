import json

import pytest

from minmax.runtime_event import RuntimeEvent
from minmax.runtime_output_eligibility import RuntimeOutputEligibilityRule
from services.rotation_runtime_output_eligibility_service import (
    DETONATING_SIPHON_GEOMETRY_CONDITION,
    RotationRuntimeOutputConditionRegistryService,
    RotationRuntimeOutputConditionRule,
    RotationRuntimeOutputEligibilityService,
)


def _event(time_seconds: float) -> RuntimeEvent:
    return RuntimeEvent(
        time_seconds=time_seconds,
        trigger="damage_dealt",
        source="test",
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


def test_unreviewed_component_event_filter_passes_every_event_through() -> None:
    events = (_event(1.0), _event(2.0))

    result = RotationRuntimeOutputEligibilityService().filter_events(
        skill_entity_id="stampede",
        coefficient_number=2,
        events=events,
    )

    assert result.events == events
    assert result.resolved is True
    assert result.unresolved == ()


def test_reviewed_conditional_events_require_exact_event_context() -> None:
    events = (_event(1.0), _event(2.0), _event(3.0))

    def context_for(event: RuntimeEvent):
        if event.time_seconds == 1.0:
            return frozenset({DETONATING_SIPHON_GEOMETRY_CONDITION})
        if event.time_seconds == 2.0:
            return frozenset()
        return None

    result = RotationRuntimeOutputEligibilityService().filter_events(
        skill_entity_id="detonating_siphon",
        coefficient_number=1,
        events=events,
        condition_context_resolver=context_for,
    )

    assert result.events == (events[0],)
    assert result.resolved is False
    assert len(result.unresolved) == 1
    assert "at 3s" in result.unresolved[0]
    assert "authoritative ConditionContext" in result.unresolved[0]


def test_reviewed_conditional_event_filter_without_resolver_fails_closed() -> None:
    events = (_event(4.0),)

    result = RotationRuntimeOutputEligibilityService().filter_events(
        skill_entity_id="detonating_siphon",
        coefficient_number=1,
        events=events,
    )

    assert result.events == ()
    assert result.resolved is False
    assert "at 4s" in result.unresolved[0]


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


def test_registry_loads_reviewed_rules_and_canonicalizes_identity(tmp_path) -> None:
    path = tmp_path / "runtime_conditions.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "skill_entity_id": "Example Skill",
                        "coefficient_number": 2,
                        "required_conditions": ["condition_a"],
                        "source": "reviewed fixture",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rules = RotationRuntimeOutputConditionRegistryService(path).load()

    assert len(rules) == 1
    assert rules[0].skill_entity_id == "example_skill"
    assert rules[0].coefficient_number == 2
    assert rules[0].eligibility.required_conditions == ("condition_a",)
    assert rules[0].eligibility.source == "reviewed fixture"


def test_registry_rejects_duplicate_component_rules(tmp_path) -> None:
    path = tmp_path / "runtime_conditions.json"
    row = {
        "skill_entity_id": "Example Skill",
        "coefficient_number": 2,
        "required_conditions": ["condition_a"],
        "source": "reviewed fixture",
    }
    path.write_text(
        json.dumps({"schema_version": 1, "entries": [row, row]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate runtime output condition registry rule"):
        RotationRuntimeOutputConditionRegistryService(path).load()
