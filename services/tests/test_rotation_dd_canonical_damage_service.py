from __future__ import annotations

from minmax.build_candidate_damage import ModeledDamagePotency
from minmax.dd_damage import DDDamageEvent
from minmax.evaluation_context import EvaluationContext
from minmax.rotation_plan import RotationPlan
from services.rotation_dd_action_damage_event_service import (
    RotationDDActionDamageProjection,
    RotationDDResolvedDamageEvent,
)
from services.rotation_dd_canonical_damage_service import RotationDDCanonicalDamageService


def _plan(duration: float = 10.0) -> RotationPlan:
    return RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=duration,
        actions=(),
    )


def _event(
    *,
    time_seconds: float,
    sequence: int,
    source_name: str = "Direct Skill",
    coefficient_number: int = 1,
    base_value: float = 1000.0,
) -> RotationDDResolvedDamageEvent:
    return RotationDDResolvedDamageEvent(
        time_seconds=time_seconds,
        sequence=sequence,
        source_name=source_name,
        coefficient_number=coefficient_number,
        event=DDDamageEvent(
            base_value=base_value,
            damage_type="magical",
            can_crit=True,
        ),
    )


def _evaluation_context() -> EvaluationContext:
    return EvaluationContext(fight_duration=10.0, target_resistance=18200.0)


def test_projects_canonical_event_values_into_rotation_total_and_dps() -> None:
    seen: list[float] = []

    def evaluator(**kwargs) -> ModeledDamagePotency:
        event = kwargs["event"]
        seen.append(event.base_value)
        return ModeledDamagePotency(
            value=event.base_value * 2.0,
            metric_name="canonical single-event expected damage",
        )

    projection = RotationDDCanonicalDamageService(
        damage_evaluator=evaluator
    ).project(
        plan=_plan(),
        context=object(),
        evaluation_context=_evaluation_context(),
        action_projection=RotationDDActionDamageProjection(
            events=(
                _event(time_seconds=1.0, sequence=1, base_value=1000.0),
                _event(
                    time_seconds=2.0,
                    sequence=2,
                    source_name="Second Skill",
                    base_value=1500.0,
                ),
            ),
            unresolved=(),
        ),
    )

    assert seen == [1000.0, 1500.0]
    assert projection.complete
    assert projection.known_damage == 5000.0
    assert projection.total_damage == 5000.0
    assert projection.projected_dps == 500.0
    assert len(projection.damage_projection.instances) == 2


def test_preserves_source_breakdown_from_resolved_instances() -> None:
    def evaluator(**kwargs) -> ModeledDamagePotency:
        return ModeledDamagePotency(
            value=100.0,
            metric_name="canonical single-event expected damage",
        )

    projection = RotationDDCanonicalDamageService(damage_evaluator=evaluator).project(
        plan=_plan(),
        context=object(),
        evaluation_context=_evaluation_context(),
        action_projection=RotationDDActionDamageProjection(
            events=(
                _event(time_seconds=1.0, sequence=1, source_name="A"),
                _event(time_seconds=2.0, sequence=2, source_name="A"),
                _event(time_seconds=3.0, sequence=3, source_name="B"),
            ),
            unresolved=(),
        ),
    )

    by_source = {item.source_name: item for item in projection.damage_projection.by_source}
    assert by_source["A"].known_damage == 200.0
    assert by_source["A"].instance_count == 2
    assert by_source["B"].known_damage == 100.0
    assert by_source["B"].instance_count == 1


def test_action_projection_unresolved_blocks_complete_total_but_keeps_known_damage() -> None:
    def evaluator(**kwargs) -> ModeledDamagePotency:
        return ModeledDamagePotency(
            value=250.0,
            metric_name="canonical single-event expected damage",
        )

    projection = RotationDDCanonicalDamageService(damage_evaluator=evaluator).project(
        plan=_plan(),
        context=object(),
        evaluation_context=_evaluation_context(),
        action_projection=RotationDDActionDamageProjection(
            events=(_event(time_seconds=1.0, sequence=1),),
            unresolved=("DoT tick schedule is not canonically resolved",),
        ),
    )

    assert projection.known_damage == 250.0
    assert projection.total_damage is None
    assert projection.projected_dps is None
    assert not projection.complete
    assert projection.unresolved == (
        "DoT tick schedule is not canonically resolved",
    )


def test_evaluator_unresolved_becomes_candidate_damage_unresolved() -> None:
    def evaluator(**kwargs) -> ModeledDamagePotency:
        return ModeledDamagePotency(
            value=None,
            metric_name="canonical single-event expected damage",
            unresolved=("target resistance evidence unavailable",),
        )

    projection = RotationDDCanonicalDamageService(damage_evaluator=evaluator).project(
        plan=_plan(),
        context=object(),
        evaluation_context=_evaluation_context(),
        action_projection=RotationDDActionDamageProjection(
            events=(_event(time_seconds=4.0, sequence=7, source_name="Skill X"),),
            unresolved=(),
        ),
    )

    assert projection.total_damage is None
    assert projection.known_damage == 0.0
    assert any(
        "Skill X coefficient 1 at 4s: target resistance evidence unavailable" in item
        for item in projection.unresolved
    )


def test_missing_value_without_reason_fails_closed() -> None:
    def evaluator(**kwargs) -> ModeledDamagePotency:
        return ModeledDamagePotency(
            value=None,
            metric_name="canonical single-event expected damage",
        )

    projection = RotationDDCanonicalDamageService(damage_evaluator=evaluator).project(
        plan=_plan(),
        context=object(),
        evaluation_context=_evaluation_context(),
        action_projection=RotationDDActionDamageProjection(
            events=(_event(time_seconds=1.0, sequence=1),),
            unresolved=(),
        ),
    )

    assert projection.total_damage is None
    assert projection.unresolved == (
        "Direct Skill coefficient 1 at 1s: canonical damage value unavailable",
    )


def test_zero_damage_is_known_zero_not_unresolved() -> None:
    def evaluator(**kwargs) -> ModeledDamagePotency:
        return ModeledDamagePotency(
            value=0.0,
            metric_name="canonical single-event expected damage",
        )

    projection = RotationDDCanonicalDamageService(damage_evaluator=evaluator).project(
        plan=_plan(),
        context=object(),
        evaluation_context=_evaluation_context(),
        action_projection=RotationDDActionDamageProjection(
            events=(_event(time_seconds=1.0, sequence=1),),
            unresolved=(),
        ),
    )

    assert projection.complete
    assert projection.total_damage == 0.0
    assert projection.projected_dps == 0.0
    assert projection.unresolved == ()


def test_event_ids_remain_unique_when_sequence_is_reused_at_different_times() -> None:
    def evaluator(**kwargs) -> ModeledDamagePotency:
        return ModeledDamagePotency(
            value=10.0,
            metric_name="canonical single-event expected damage",
        )

    projection = RotationDDCanonicalDamageService(damage_evaluator=evaluator).project(
        plan=_plan(),
        context=object(),
        evaluation_context=_evaluation_context(),
        action_projection=RotationDDActionDamageProjection(
            events=(
                _event(time_seconds=1.0, sequence=1),
                _event(time_seconds=2.0, sequence=1),
            ),
            unresolved=(),
        ),
    )

    ids = tuple(item.event_id for item in projection.damage_projection.instances)
    assert len(ids) == len(set(ids)) == 2


def test_empty_resolved_action_projection_is_known_zero_damage() -> None:
    def evaluator(**kwargs) -> ModeledDamagePotency:
        raise AssertionError("no events should be evaluated")

    projection = RotationDDCanonicalDamageService(damage_evaluator=evaluator).project(
        plan=_plan(),
        context=object(),
        evaluation_context=_evaluation_context(),
        action_projection=RotationDDActionDamageProjection(events=(), unresolved=()),
    )

    assert projection.complete
    assert projection.total_damage == 0.0
    assert projection.projected_dps == 0.0
