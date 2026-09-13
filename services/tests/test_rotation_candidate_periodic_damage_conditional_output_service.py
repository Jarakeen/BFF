from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind
from minmax.runtime_event import RuntimeEvent
from services.rotation_candidate_periodic_damage_conditional_output_service import (
    RotationCandidatePeriodicDamageConditionalOutputService,
)
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    RotationPeriodicDamageRuntimeProjection,
    RotationPeriodicDamageRuntimeProjectionEntry,
)
from services.rotation_runtime_output_eligibility_service import (
    DETONATING_SIPHON_GEOMETRY_CONDITION,
)


class _ProjectionService:
    def __init__(self, projection):
        self.projection = projection
        self.calls = []

    def project(self, *, plan, semantics):
        self.calls.append((plan, semantics))
        return self.projection


def _action(name: str = "detonating_siphon") -> RotationAction:
    return RotationAction(
        0.0,
        0,
        RotationActionKind.SKILL,
        name=name,
        bar="front",
    )


def _event(time_seconds: float) -> RuntimeEvent:
    return RuntimeEvent(
        time_seconds=time_seconds,
        trigger="damage_dealt",
        source="periodic coefficient 1",
        sequence=int(time_seconds * 10),
    )


def _projection(
    *,
    name: str = "detonating_siphon",
    times=(1.0, 2.0, 3.0),
    evidence=(),
    unresolved=(),
):
    return RotationPeriodicDamageRuntimeProjection(
        entries=(
            RotationPeriodicDamageRuntimeProjectionEntry(
                action=_action(name),
                coefficient_number=1,
                events=tuple(_event(value) for value in times),
                active_end_time_seconds=20.0,
                evidence=tuple(evidence),
                unresolved=tuple(unresolved),
            ),
        ),
    )


def test_unreviewed_component_passes_scheduled_events_through_unchanged() -> None:
    projection = _projection(name="ordinary_periodic_skill")
    inner = _ProjectionService(projection)
    service = RotationCandidatePeriodicDamageConditionalOutputService(inner)
    plan = SimpleNamespace(name="plan")
    semantics = ()

    result = service.project(plan=plan, semantics=semantics)

    assert result == projection
    assert inner.calls == [(plan, semantics)]


def test_reviewed_conditional_component_fails_closed_without_runtime_context() -> None:
    service = RotationCandidatePeriodicDamageConditionalOutputService(
        _ProjectionService(_projection(times=(1.0, 2.0)))
    )

    result = service.project(plan=SimpleNamespace(), semantics=())
    entry = result.entries[0]

    assert entry.events == ()
    assert entry.unresolved == (
        "detonating_siphon coefficient 1 at 1s: runtime output eligibility requires authoritative ConditionContext for target_in_detonating_siphon_geometry",
        "detonating_siphon coefficient 1 at 2s: runtime output eligibility requires authoritative ConditionContext for target_in_detonating_siphon_geometry",
    )


def test_exact_event_context_can_stop_and_resume_conditional_output() -> None:
    contexts = {
        1.0: frozenset({DETONATING_SIPHON_GEOMETRY_CONDITION}),
        2.0: frozenset(),
        3.0: frozenset({DETONATING_SIPHON_GEOMETRY_CONDITION}),
    }
    calls = []

    def resolve(event):
        calls.append(float(event.time_seconds))
        return contexts[float(event.time_seconds)]

    service = RotationCandidatePeriodicDamageConditionalOutputService(
        _ProjectionService(_projection()),
        condition_context_resolver=resolve,
    )

    result = service.project(plan=SimpleNamespace(), semantics=())
    entry = result.entries[0]

    assert tuple(event.time_seconds for event in entry.events) == (1.0, 3.0)
    assert entry.unresolved == ()
    assert calls == [1.0, 2.0, 3.0]
    assert "required runtime output conditions: target_in_detonating_siphon_geometry" in entry.evidence


def test_existing_projection_evidence_and_unresolved_are_preserved() -> None:
    service = RotationCandidatePeriodicDamageConditionalOutputService(
        _ProjectionService(
            _projection(
                evidence=("scheduler evidence",),
                unresolved=("scheduler unresolved",),
                times=(1.0,),
            )
        )
    )

    result = service.project(plan=SimpleNamespace(), semantics=())
    entry = result.entries[0]

    assert entry.evidence[0] == "scheduler evidence"
    assert "required runtime output conditions: target_in_detonating_siphon_geometry" in entry.evidence
    assert entry.unresolved[0] == "scheduler unresolved"
    assert "runtime output eligibility requires authoritative ConditionContext" in entry.unresolved[1]


def test_missing_parent_skill_identity_fails_closed_before_rule_lookup() -> None:
    nameless_action = RotationAction(
        0.0,
        0,
        RotationActionKind.LIGHT_ATTACK,
        bar="front",
    )
    projection = RotationPeriodicDamageRuntimeProjection(
        entries=(
            RotationPeriodicDamageRuntimeProjectionEntry(
                action=nameless_action,
                coefficient_number=1,
                events=(_event(1.0),),
                active_end_time_seconds=20.0,
            ),
        ),
    )
    service = RotationCandidatePeriodicDamageConditionalOutputService(
        _ProjectionService(projection)
    )

    result = service.project(plan=SimpleNamespace(), semantics=())
    entry = result.entries[0]

    assert entry.events == ()
    assert entry.unresolved == (
        "periodic conditional output requires canonical parent skill identity",
    )
