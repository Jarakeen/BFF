from minmax.build_candidate_damage import ModeledDamagePotency
from minmax.dd_damage import DDDamageEvent
from minmax.evaluation_context import EvaluationContext
from minmax.rotation_plan import RotationPlan
from services.rotation_dd_action_damage_event_service import (
    RotationDDActionDamageProjection,
    RotationDDDotComponentSeed,
)
from services.rotation_dd_canonical_damage_service import RotationDDCanonicalDamageService
from services.rotation_dd_dot_runtime_service import (
    RotationDDDotRuntimeEvidence,
    RotationDDDotRuntimeService,
)


def _plan():
    return RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=10.0,
        actions=(),
    )


def _seed():
    return RotationDDDotComponentSeed(
        cast_time_seconds=0.0,
        sequence=1,
        source_name="Burning Dot",
        coefficient_number=2,
        event=DDDamageEvent(
            base_value=100.0,
            damage_type="flame",
            can_crit=True,
            is_dot=True,
        ),
    )


def _evaluator(**kwargs):
    event = kwargs["event"]
    return ModeledDamagePotency(
        value=event.base_value * 2.0,
        metric_name="canonical single-event expected damage",
    )


def test_unscheduled_dot_seed_blocks_complete_rotation_damage():
    projection = RotationDDCanonicalDamageService(
        damage_evaluator=_evaluator
    ).project(
        plan=_plan(),
        context=object(),
        evaluation_context=EvaluationContext(target_resistance=18200.0),
        action_projection=RotationDDActionDamageProjection(
            events=(), unresolved=(), dot_components=(_seed(),)
        ),
    )
    assert not projection.complete
    assert projection.total_damage is None
    assert projection.unresolved == (
        "Burning Dot coefficient 2 at 0s: DoT runtime projection unavailable",
    )


def test_scheduled_dot_ticks_join_canonical_rotation_damage_total():
    action_projection = RotationDDActionDamageProjection(
        events=(), unresolved=(), dot_components=(_seed(),)
    )
    dot_projection = RotationDDDotRuntimeService().project(
        seeds=action_projection.dot_components,
        evidence=(
            RotationDDDotRuntimeEvidence(
                source_name="Burning Dot",
                coefficient_number=2,
                duration_seconds=3.0,
                tick_interval_seconds=1.0,
                first_tick_offset_seconds=1.0,
            ),
        ),
        horizon_seconds=10.0,
    )
    projection = RotationDDCanonicalDamageService(
        damage_evaluator=_evaluator
    ).project(
        plan=_plan(),
        context=object(),
        evaluation_context=EvaluationContext(target_resistance=18200.0),
        action_projection=action_projection,
        dot_projection=dot_projection,
    )
    assert projection.complete
    assert projection.total_damage == 600.0
    assert projection.projected_dps == 60.0
    assert [item.time_seconds for item in projection.damage_projection.instances] == [1.0, 2.0, 3.0]


def test_runtime_unresolved_still_blocks_total_even_if_some_dot_ticks_are_known():
    action_projection = RotationDDActionDamageProjection(
        events=(), unresolved=(), dot_components=(_seed(),)
    )
    dot_projection = RotationDDDotRuntimeService().project(
        seeds=action_projection.dot_components,
        evidence=(),
        horizon_seconds=10.0,
    )
    projection = RotationDDCanonicalDamageService(
        damage_evaluator=_evaluator
    ).project(
        plan=_plan(),
        context=object(),
        evaluation_context=EvaluationContext(),
        action_projection=action_projection,
        dot_projection=dot_projection,
    )
    assert projection.total_damage is None
    assert projection.unresolved == (
        "Burning Dot coefficient 2: DoT runtime evidence unavailable",
    )
