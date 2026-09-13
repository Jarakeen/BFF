import pytest

from minmax.runtime_event import RuntimeEvent
from services.rotation_runtime_spatial_condition_context_service import (
    RotationRuntimeSpatialCircleClause,
    RotationRuntimeSpatialConditionContextService,
    RotationRuntimeSpatialConditionRule,
    RotationRuntimeSpatialPositionWindow,
    RotationRuntimeSpatialSegmentClause,
)


def _event(time_seconds: float) -> RuntimeEvent:
    return RuntimeEvent(
        time_seconds=time_seconds,
        trigger="damage_dealt",
        source="spatial-test",
        sequence=int(time_seconds * 10),
    )


def _window(entity_id: str, start: float, end: float, x: float, y: float):
    return RotationRuntimeSpatialPositionWindow(
        entity_id=entity_id,
        start_seconds=start,
        end_seconds=end,
        x=x,
        y=y,
    )


def test_circle_condition_resolves_true_and_false_from_explicit_positions() -> None:
    service = RotationRuntimeSpatialConditionContextService(
        position_windows=(
            _window("center", 0.0, 2.0, 0.0, 0.0),
            _window("target", 0.0, 1.0, 2.0, 0.0),
            _window("target", 1.0, 2.0, 6.0, 0.0),
        ),
        rules=(
            RotationRuntimeSpatialConditionRule(
                condition="target_in_circle",
                clauses=(
                    RotationRuntimeSpatialCircleClause(
                        center_entity_id="center",
                        target_entity_id="target",
                        maximum_distance=3.0,
                    ),
                ),
                source="explicit test radius",
            ),
        ),
    )

    assert service.resolve(_event(0.5)) == frozenset({"target_in_circle"})
    assert service.resolve(_event(1.5)) == frozenset()


def test_segment_condition_uses_bounded_corridor_not_infinite_line() -> None:
    service = RotationRuntimeSpatialConditionContextService(
        position_windows=(
            _window("start", 0.0, 3.0, 0.0, 0.0),
            _window("end", 0.0, 3.0, 10.0, 0.0),
            _window("target", 0.0, 1.0, 5.0, 1.0),
            _window("target", 1.0, 2.0, 5.0, 3.0),
            _window("target", 2.0, 3.0, 12.0, 0.0),
        ),
        rules=(
            RotationRuntimeSpatialConditionRule(
                condition="target_in_corridor",
                clauses=(
                    RotationRuntimeSpatialSegmentClause(
                        start_entity_id="start",
                        end_entity_id="end",
                        target_entity_id="target",
                        half_width=1.5,
                    ),
                ),
                source="explicit test corridor width",
            ),
        ),
    )

    assert service.resolve(_event(0.5)) == frozenset({"target_in_corridor"})
    assert service.resolve(_event(1.5)) == frozenset()
    assert service.resolve(_event(2.5)) == frozenset()


def test_rule_uses_or_semantics_and_true_clause_can_resolve_other_unknown_clause() -> None:
    service = RotationRuntimeSpatialConditionContextService(
        position_windows=(
            _window("corpse", 0.0, 2.0, 0.0, 0.0),
            _window("target", 0.0, 2.0, 1.0, 0.0),
        ),
        rules=(
            RotationRuntimeSpatialConditionRule(
                condition="target_in_combined_geometry",
                clauses=(
                    RotationRuntimeSpatialCircleClause(
                        center_entity_id="corpse",
                        target_entity_id="target",
                        maximum_distance=2.0,
                    ),
                    RotationRuntimeSpatialSegmentClause(
                        start_entity_id="missing_caster",
                        end_entity_id="corpse",
                        target_entity_id="target",
                        half_width=1.0,
                    ),
                ),
                source="explicit OR geometry",
            ),
        ),
    )

    assert service.resolve(_event(1.0)) == frozenset({"target_in_combined_geometry"})


def test_missing_position_is_unknown_not_known_false_when_no_clause_proves_true() -> None:
    service = RotationRuntimeSpatialConditionContextService(
        position_windows=(
            _window("corpse", 0.0, 2.0, 0.0, 0.0),
        ),
        rules=(
            RotationRuntimeSpatialConditionRule(
                condition="target_in_circle",
                clauses=(
                    RotationRuntimeSpatialCircleClause(
                        center_entity_id="corpse",
                        target_entity_id="target",
                        maximum_distance=2.0,
                    ),
                ),
                source="explicit test radius",
            ),
        ),
    )

    assert service.resolve(_event(1.0)) is None


def test_condition_context_can_stop_and_resume_as_positions_change() -> None:
    service = RotationRuntimeSpatialConditionContextService(
        position_windows=(
            _window("center", 0.0, 3.0, 0.0, 0.0),
            _window("target", 0.0, 1.0, 1.0, 0.0),
            _window("target", 1.0, 2.0, 5.0, 0.0),
            _window("target", 2.0, 3.0, 1.0, 0.0),
        ),
        rules=(
            RotationRuntimeSpatialConditionRule(
                condition="target_in_circle",
                clauses=(
                    RotationRuntimeSpatialCircleClause(
                        center_entity_id="center",
                        target_entity_id="target",
                        maximum_distance=2.0,
                    ),
                ),
                source="explicit test radius",
            ),
        ),
    )

    assert service.resolve(_event(0.5)) == frozenset({"target_in_circle"})
    assert service.resolve(_event(1.5)) == frozenset()
    assert service.resolve(_event(2.5)) == frozenset({"target_in_circle"})


def test_resolver_factory_ignores_plan_identity_and_preserves_exact_event_resolution() -> None:
    service = RotationRuntimeSpatialConditionContextService(
        position_windows=(
            _window("center", 0.0, 2.0, 0.0, 0.0),
            _window("target", 0.0, 2.0, 1.0, 0.0),
        ),
        rules=(
            RotationRuntimeSpatialConditionRule(
                condition="target_in_circle",
                clauses=(
                    RotationRuntimeSpatialCircleClause(
                        center_entity_id="center",
                        target_entity_id="target",
                        maximum_distance=2.0,
                    ),
                ),
                source="explicit test radius",
            ),
        ),
    )

    resolver = service.resolver_factory()(object())
    assert resolver(_event(1.0)) == frozenset({"target_in_circle"})


def test_overlapping_position_windows_for_same_entity_are_rejected() -> None:
    with pytest.raises(ValueError, match="cannot overlap"):
        RotationRuntimeSpatialConditionContextService(
            position_windows=(
                _window("target", 0.0, 2.0, 0.0, 0.0),
                _window("target", 1.0, 3.0, 1.0, 0.0),
            ),
            rules=(
                RotationRuntimeSpatialConditionRule(
                    condition="target_in_circle",
                    clauses=(
                        RotationRuntimeSpatialCircleClause(
                            center_entity_id="target",
                            target_entity_id="target",
                            maximum_distance=0.0,
                        ),
                    ),
                    source="test",
                ),
            ),
        )


def test_duplicate_condition_rules_are_rejected() -> None:
    rule = RotationRuntimeSpatialConditionRule(
        condition="duplicate",
        clauses=(
            RotationRuntimeSpatialCircleClause(
                center_entity_id="a",
                target_entity_id="b",
                maximum_distance=1.0,
            ),
        ),
        source="test",
    )

    with pytest.raises(ValueError, match="duplicate"):
        RotationRuntimeSpatialConditionContextService(
            position_windows=(),
            rules=(rule, rule),
        )
