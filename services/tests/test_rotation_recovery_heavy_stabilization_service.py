from types import SimpleNamespace

from minmax.healer_recovery_heavy_pressure import HealerRecoveryHeavyPressure
from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_recovery_heavy_stabilization_service import (
    RotationRecoveryHeavyStabilizationService,
)


def _plan(*heavy_times: float) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=tuple(
            RotationAction(
                time_seconds=time_seconds,
                sequence=0,
                kind=RotationActionKind.HEAVY_ATTACK,
                name="Heavy Attack",
                bar="front",
            )
            for time_seconds in heavy_times
        ),
    )


def _plan_with_skill(*, skill_name: str, skill_time: float = 5.0) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.HEAVY_ATTACK,
                name="Heavy Attack",
                bar="front",
            ),
            RotationAction(
                time_seconds=skill_time,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name=skill_name,
                bar="front",
            ),
        ),
    )


class _ReplayService:
    def __init__(self) -> None:
        self.replays = []

    def replay(self, *, build, plan, resource, restoration_resolver):
        signature = tuple(
            action.time_seconds
            for action in plan.actions
            if action.kind is RotationActionKind.HEAVY_ATTACK
        )
        self.replays.append(signature)
        restored = 4000 if 2.0 in signature else 0
        timeline = ResourceTimelineResult(
            resource=resource,
            starting_amount=2500,
            ending_amount=2500 + restored,
            events=(),
        )
        projection = SimpleNamespace(run=SimpleNamespace(timeline=timeline))
        return SimpleNamespace(
            initial_projection=projection,
            final_projection=projection,
            restoration_events=(),
            steps=(),
        )

    @staticmethod
    def pressure_resolver(
        *,
        replay,
        maximum_amount,
        trigger_fraction,
        reserve_assessment_resolver=None,
    ):
        current = replay.final_projection.run.timeline.ending_amount

        def resolve(context):
            fraction = current / maximum_amount
            return HealerRecoveryHeavyPressure(
                resource=ResourceType.MAGICKA,
                time_seconds=context.time_seconds,
                current_amount=current,
                maximum_amount=maximum_amount,
                resource_fraction=fraction,
                trigger_fraction=trigger_fraction,
                reserve_shortfall=0,
                recommended=fraction <= trigger_fraction,
                reason="test pressure",
            )

        return resolve


class _ShortfallReplayService(_ReplayService):
    def replay(self, *, build, plan, resource, restoration_resolver):
        signature = tuple(
            action.time_seconds
            for action in plan.actions
            if action.kind is RotationActionKind.HEAVY_ATTACK
        )
        self.replays.append(signature)
        timeline = SimpleNamespace(
            resource=resource,
            starting_amount=2500,
            ending_amount=0,
            events=(),
            total_shortfall=500,
        )
        projection = SimpleNamespace(run=SimpleNamespace(timeline=timeline))
        return SimpleNamespace(
            initial_projection=projection,
            final_projection=projection,
            restoration_events=(),
            steps=(),
        )


def test_stabilizer_regenerates_until_full_schedule_state_is_unchanged() -> None:
    replay = _ReplayService()
    service = RotationRecoveryHeavyStabilizationService(replay_service=replay)
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    calls = []

    def generate(pressure_resolver):
        calls.append(pressure_resolver)
        if pressure_resolver is None:
            return _plan(2.0, 10.0)
        context = SimpleNamespace(time_seconds=10.0)
        pressure = pressure_resolver(context)
        return _plan(2.0) if not pressure.recommended else _plan(2.0, 10.0)

    result = service.stabilize(
        build=build,
        generate=generate,
        resource=ResourceType.MAGICKA,
        maximum_amount=10000,
        trigger_fraction=0.30,
        restoration_resolver=lambda heavy: ResourceRestorationEvent(
            time_seconds=heavy.time_seconds + 1.8,
            resource=ResourceType.MAGICKA,
            amount=4000,
            source="verified test heavy restore",
        ),
        max_iterations=5,
    )

    assert result.converged is True
    assert result.termination_reason == "stable_fixed_point"
    assert result.tracked_hard_obligations_satisfied is True
    assert [item.heavy_signature for item in result.iterations] == [
        ((2.0, 0, "front", "Heavy Attack"), (10.0, 0, "front", "Heavy Attack")),
        ((2.0, 0, "front", "Heavy Attack"),),
        ((2.0, 0, "front", "Heavy Attack"),),
    ]
    assert len(calls) == 3
    assert replay.replays == [(2.0, 10.0), (2.0,), (2.0,)]


def test_stabilizer_does_not_false_converge_when_non_heavy_schedule_changes() -> None:
    replay = _ReplayService()
    service = RotationRecoveryHeavyStabilizationService(replay_service=replay)
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    count = 0

    def generate(_pressure_resolver):
        nonlocal count
        count += 1
        if count == 1:
            return _plan_with_skill(skill_name="Combat Prayer")
        return _plan_with_skill(skill_name="Budding Seeds")

    result = service.stabilize(
        build=build,
        generate=generate,
        resource=ResourceType.MAGICKA,
        maximum_amount=10000,
        trigger_fraction=0.30,
        restoration_resolver=lambda heavy: None,
        max_iterations=4,
    )

    assert result.converged is True
    assert len(result.iterations) == 3
    assert [item.heavy_signature for item in result.iterations] == [
        ((2.0, 0, "front", "Heavy Attack"),),
        ((2.0, 0, "front", "Heavy Attack"),),
        ((2.0, 0, "front", "Heavy Attack"),),
    ]
    assert result.iterations[0].plan_signature != result.iterations[1].plan_signature
    assert result.iterations[1].plan_signature == result.iterations[2].plan_signature


def test_stabilizer_rechecks_hard_obligation_state_before_converging() -> None:
    replay = _ReplayService()
    service = RotationRecoveryHeavyStabilizationService(replay_service=replay)
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    obligation_checks = 0

    def resolve_obligations(_plan, _replay):
        nonlocal obligation_checks
        obligation_checks += 1
        return ("support_assignment_missing",) if obligation_checks == 1 else ()

    result = service.stabilize(
        build=build,
        generate=lambda _pressure_resolver: _plan(2.0),
        resource=ResourceType.MAGICKA,
        maximum_amount=10000,
        trigger_fraction=0.30,
        restoration_resolver=lambda heavy: None,
        hard_obligation_state_resolver=resolve_obligations,
        max_iterations=4,
    )

    assert result.converged is True
    assert result.termination_reason == "stable_fixed_point"
    assert result.tracked_hard_obligations_satisfied is True
    assert len(result.iterations) == 3
    assert result.iterations[0].hard_obligation_state == ("support_assignment_missing",)
    assert result.iterations[1].hard_obligation_state == ()
    assert result.iterations[2].hard_obligation_state == ()


def test_stabilizer_marks_stable_unresolved_obligation_as_no_legal_improvement() -> None:
    replay = _ReplayService()
    service = RotationRecoveryHeavyStabilizationService(replay_service=replay)
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")

    result = service.stabilize(
        build=build,
        generate=lambda _pressure_resolver: _plan(2.0),
        resource=ResourceType.MAGICKA,
        maximum_amount=10000,
        trigger_fraction=0.30,
        restoration_resolver=lambda heavy: None,
        hard_obligation_state_resolver=lambda _plan, _replay: (
            "mechanic|xalvakka_healing_prep|budding_seeds",
        ),
        max_iterations=4,
    )

    assert result.converged is True
    assert result.termination_reason == "stable_no_legal_improvement"
    assert result.tracked_hard_obligations_satisfied is False
    assert len(result.iterations) == 2


def test_stabilizer_marks_stable_resource_shortfall_as_no_legal_improvement() -> None:
    replay = _ShortfallReplayService()
    service = RotationRecoveryHeavyStabilizationService(replay_service=replay)
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")

    result = service.stabilize(
        build=build,
        generate=lambda _pressure_resolver: _plan(2.0),
        resource=ResourceType.MAGICKA,
        maximum_amount=10000,
        trigger_fraction=0.30,
        restoration_resolver=lambda heavy: None,
        max_iterations=4,
    )

    assert result.converged is True
    assert result.termination_reason == "stable_no_legal_improvement"
    assert result.tracked_hard_obligations_satisfied is False
    assert result.iterations[-1].total_shortfall == 500
    assert len(result.iterations) == 2


def test_stabilizer_stops_at_cap_when_heavy_schedule_oscillates() -> None:
    replay = _ReplayService()
    service = RotationRecoveryHeavyStabilizationService(replay_service=replay)
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    count = 0

    def generate(_pressure_resolver):
        nonlocal count
        count += 1
        return _plan(2.0) if count % 2 else _plan(2.0, 10.0)

    result = service.stabilize(
        build=build,
        generate=generate,
        resource=ResourceType.MAGICKA,
        maximum_amount=10000,
        trigger_fraction=0.30,
        restoration_resolver=lambda heavy: None,
        max_iterations=4,
    )

    assert result.converged is False
    assert result.termination_reason == "iteration_limit_reached"
    assert len(result.iterations) == 4
    assert [item.heavy_signature for item in result.iterations] == [
        ((2.0, 0, "front", "Heavy Attack"),),
        ((2.0, 0, "front", "Heavy Attack"), (10.0, 0, "front", "Heavy Attack")),
        ((2.0, 0, "front", "Heavy Attack"),),
        ((2.0, 0, "front", "Heavy Attack"), (10.0, 0, "front", "Heavy Attack")),
    ]
