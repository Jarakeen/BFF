import pytest

from services.rotation_periodic_target_health_semantics_service import (
    PeriodicTargetHealthTimingPolicy,
    RotationPeriodicTargetHealthSemantics,
    RotationPeriodicTargetHealthSemanticsService,
)


def test_resolves_exact_skill_component_semantics() -> None:
    semantic = RotationPeriodicTargetHealthSemantics(
        skill_entity_id="execute_dot",
        coefficient_number=2,
        policy=PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK,
        source="reviewed test evidence",
    )
    service = RotationPeriodicTargetHealthSemanticsService((semantic,))

    result = service.resolve(skill_name="Execute Dot", coefficient_number=2)

    assert result is semantic
    assert result.policy is PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK


def test_missing_semantics_fail_closed_with_none() -> None:
    service = RotationPeriodicTargetHealthSemanticsService()

    assert service.resolve(skill_name="Execute Dot", coefficient_number=2) is None


def test_duplicate_semantics_fail_closed_with_none() -> None:
    first = RotationPeriodicTargetHealthSemantics(
        skill_entity_id="execute_dot",
        coefficient_number=2,
        policy=PeriodicTargetHealthTimingPolicy.SNAPSHOT_AT_CAST,
        source="source A",
    )
    second = RotationPeriodicTargetHealthSemantics(
        skill_entity_id="execute_dot",
        coefficient_number=2,
        policy=PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK,
        source="source B",
    )
    service = RotationPeriodicTargetHealthSemanticsService((first, second))

    assert service.resolve(skill_name="Execute Dot", coefficient_number=2) is None


def test_semantics_require_positive_component_and_source() -> None:
    with pytest.raises(ValueError):
        RotationPeriodicTargetHealthSemantics(
            skill_entity_id="execute_dot",
            coefficient_number=0,
            policy=PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK,
            source="reviewed",
        )
    with pytest.raises(ValueError):
        RotationPeriodicTargetHealthSemantics(
            skill_entity_id="execute_dot",
            coefficient_number=1,
            policy=PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK,
            source="",
        )
