from __future__ import annotations

from types import SimpleNamespace

from minmax.build_candidate_damage import ModeledDamagePotency
from minmax.dd_damage import DDDamageEvent
from minmax.evaluation_context import EvaluationContext
from minmax.rotation_plan import RotationPlan
from services.rotation_dd_action_damage_event_service import (
    RotationDDActionDamageProjection,
    RotationDDResolvedDamageEvent,
)
from services.rotation_dd_canonical_damage_service import RotationDDCanonicalDamageService
from services.rotation_dd_dot_runtime_service import RotationDDDotRuntimeProjection


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=10.0,
        actions=(),
    )


def _event(*, time_seconds: float, sequence: int, source_name: str) -> RotationDDResolvedDamageEvent:
    return RotationDDResolvedDamageEvent(
        time_seconds=time_seconds,
        sequence=sequence,
        source_name=source_name,
        coefficient_number=1,
        event=DDDamageEvent(
            base_value=100.0,
            damage_type="magical",
            can_crit=True,
        ),
    )


def test_direct_damage_uses_exact_time_sequence_context_resolver() -> None:
    front = SimpleNamespace(marker="front")
    back = SimpleNamespace(marker="back")
    resolver_calls: list[tuple[float, int]] = []
    evaluator_contexts: list[str] = []

    def context_resolver(time_seconds: float, sequence: int):
        resolver_calls.append((time_seconds, sequence))
        return front if sequence < 20 else back

    def evaluator(**kwargs) -> ModeledDamagePotency:
        evaluator_contexts.append(kwargs["context"].marker)
        value = 100.0 if kwargs["context"] is front else 200.0
        return ModeledDamagePotency(
            value=value,
            metric_name="canonical single-event expected damage",
        )

    projection = RotationDDCanonicalDamageService(damage_evaluator=evaluator).project(
        plan=_plan(),
        context=SimpleNamespace(marker="fallback"),
        evaluation_context=EvaluationContext(),
        action_projection=RotationDDActionDamageProjection(
            events=(
                _event(time_seconds=4.0, sequence=19, source_name="Before Swap"),
                _event(time_seconds=4.0, sequence=21, source_name="After Swap"),
            ),
            unresolved=(),
        ),
        direct_context_resolver=context_resolver,
    )

    assert resolver_calls == [(4.0, 19), (4.0, 21)]
    assert evaluator_contexts == ["front", "back"]
    assert projection.complete
    assert projection.total_damage == 300.0


def test_direct_context_resolver_failure_is_candidate_unresolved_not_crash() -> None:
    def context_resolver(_time_seconds: float, _sequence: int):
        raise ValueError("back-bar static context missing")

    def evaluator(**_kwargs) -> ModeledDamagePotency:
        raise AssertionError("unresolved context must not be evaluated")

    projection = RotationDDCanonicalDamageService(damage_evaluator=evaluator).project(
        plan=_plan(),
        context=object(),
        evaluation_context=EvaluationContext(),
        action_projection=RotationDDActionDamageProjection(
            events=(_event(time_seconds=4.0, sequence=21, source_name="Back Skill"),),
            unresolved=(),
        ),
        direct_context_resolver=context_resolver,
    )

    assert not projection.complete
    assert projection.total_damage is None
    assert projection.known_damage == 0.0
    assert projection.unresolved == (
        "Back Skill coefficient 1 at 4s: canonical direct-damage build context unavailable: back-bar static context missing",
    )


def test_bar_aware_direct_context_does_not_invent_dot_tick_context_policy() -> None:
    seen_contexts: list[object] = []
    fallback = object()

    def evaluator(**kwargs) -> ModeledDamagePotency:
        seen_contexts.append(kwargs["context"])
        return ModeledDamagePotency(
            value=50.0,
            metric_name="canonical single-event expected damage",
        )

    dot_event = _event(time_seconds=2.0, sequence=3, source_name="Burning Dot")
    projection = RotationDDCanonicalDamageService(damage_evaluator=evaluator).project(
        plan=_plan(),
        context=fallback,
        evaluation_context=EvaluationContext(),
        action_projection=RotationDDActionDamageProjection(events=(), unresolved=()),
        dot_projection=RotationDDDotRuntimeProjection(
            events=(dot_event,),
            unresolved=(),
        ),
        direct_context_resolver=lambda _time, _sequence: object(),
    )

    assert seen_contexts == [fallback]
    assert not projection.complete
    assert projection.total_damage is None
    assert projection.known_damage == 50.0
    assert projection.unresolved == (
        "bar-aware DoT damage context semantics are unresolved; direct-cast bar context cannot be reused as tick-time or snapshot evidence",
    )
