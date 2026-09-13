from minmax.runtime_event import RuntimeEvent
from services.rotation_runtime_output_eligibility_service import (
    DETONATING_SIPHON_GEOMETRY_CONDITION,
    RotationRuntimeOutputEligibilityService,
)
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
        source="synthetic periodic event",
        sequence=int(time_seconds),
    )


def _window(entity_id: str, start: float, end: float, x: float, y: float):
    return RotationRuntimeSpatialPositionWindow(
        entity_id=entity_id,
        start_seconds=start,
        end_seconds=end,
        x=x,
        y=y,
    )


def test_explicit_spatial_evidence_can_drive_reviewed_siphon_output_condition() -> None:
    events = (_event(1.0), _event(2.0), _event(3.0))
    spatial = RotationRuntimeSpatialConditionContextService(
        position_windows=(
            _window("caster", 0.0, 4.0, 0.0, 0.0),
            _window("corpse", 0.0, 4.0, 10.0, 0.0),
            _window("target", 0.0, 1.5, 10.5, 0.0),
            _window("target", 1.5, 2.5, 5.0, 4.0),
            _window("target", 2.5, 4.0, 5.0, 0.5),
        ),
        rules=(
            RotationRuntimeSpatialConditionRule(
                condition=DETONATING_SIPHON_GEOMETRY_CONDITION,
                clauses=(
                    RotationRuntimeSpatialCircleClause(
                        center_entity_id="corpse",
                        target_entity_id="target",
                        maximum_distance=1.0,
                    ),
                    RotationRuntimeSpatialSegmentClause(
                        start_entity_id="caster",
                        end_entity_id="corpse",
                        target_entity_id="target",
                        half_width=1.0,
                    ),
                ),
                source=(
                    "synthetic test geometry only; dimensions are not promoted as ESO mechanics"
                ),
            ),
        ),
    )

    result = RotationRuntimeOutputEligibilityService().filter_events(
        skill_entity_id="detonating_siphon",
        coefficient_number=1,
        events=events,
        condition_context_resolver=spatial.resolve,
    )

    assert result.events == (events[0], events[2])
    assert result.resolved is True
    assert result.unresolved == ()


def test_missing_exact_time_spatial_evidence_keeps_siphon_output_unresolved() -> None:
    event = _event(2.0)
    spatial = RotationRuntimeSpatialConditionContextService(
        position_windows=(
            _window("caster", 0.0, 4.0, 0.0, 0.0),
            _window("corpse", 0.0, 4.0, 10.0, 0.0),
        ),
        rules=(
            RotationRuntimeSpatialConditionRule(
                condition=DETONATING_SIPHON_GEOMETRY_CONDITION,
                clauses=(
                    RotationRuntimeSpatialCircleClause(
                        center_entity_id="corpse",
                        target_entity_id="target",
                        maximum_distance=1.0,
                    ),
                    RotationRuntimeSpatialSegmentClause(
                        start_entity_id="caster",
                        end_entity_id="corpse",
                        target_entity_id="target",
                        half_width=1.0,
                    ),
                ),
                source="synthetic test geometry only",
            ),
        ),
    )

    result = RotationRuntimeOutputEligibilityService().filter_events(
        skill_entity_id="detonating_siphon",
        coefficient_number=1,
        events=(event,),
        condition_context_resolver=spatial.resolve,
    )

    assert result.events == ()
    assert result.resolved is False
    assert "at 2s" in result.unresolved[0]
    assert "authoritative ConditionContext" in result.unresolved[0]
