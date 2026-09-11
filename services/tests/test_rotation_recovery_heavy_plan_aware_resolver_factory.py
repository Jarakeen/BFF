from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
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


class _ReplayService:
    def __init__(self) -> None:
        self.calls = []

    def replay(self, **kwargs):
        self.calls.append(kwargs)
        timeline = ResourceTimelineResult(
            resource=kwargs["resource"],
            starting_amount=5000,
            ending_amount=5000,
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
    def pressure_resolver(**_kwargs):
        return lambda _context: None


def test_factory_is_rebuilt_for_each_generated_plan() -> None:
    replay = _ReplayService()
    service = RotationRecoveryHeavyStabilizationService(replay_service=replay)
    generated = [_plan(2.0, 10.0), _plan(2.0), _plan(2.0)]
    factory_plans = []
    resolver_markers = []

    def generate(_pressure):
        return generated.pop(0)

    def factory(plan):
        factory_plans.append(plan)
        marker = tuple(action.time_seconds for action in plan.actions)

        def resolve(_action):
            return marker

        resolver_markers.append((marker, resolve))
        return resolve

    result = service.stabilize(
        build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        generate=generate,
        resource=ResourceType.MAGICKA,
        maximum_amount=10000,
        trigger_fraction=0.30,
        restoration_resolver_factory=factory,
        max_iterations=4,
    )

    assert result.converged is True
    assert [tuple(action.time_seconds for action in plan.actions) for plan in factory_plans] == [
        (2.0, 10.0),
        (2.0,),
        (2.0,),
    ]
    assert [call["restoration_resolver"] for call in replay.calls] == [
        resolver for _marker, resolver in resolver_markers
    ]


def test_static_resolver_remains_supported() -> None:
    replay = _ReplayService()
    service = RotationRecoveryHeavyStabilizationService(replay_service=replay)
    resolver = lambda _action: None

    result = service.stabilize(
        build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        generate=lambda _pressure: _plan(2.0),
        resource=ResourceType.MAGICKA,
        maximum_amount=10000,
        trigger_fraction=0.30,
        restoration_resolver=resolver,
        max_iterations=3,
    )

    assert result.converged is True
    assert all(call["restoration_resolver"] is resolver for call in replay.calls)


def test_both_resolver_sources_fail_closed() -> None:
    service = RotationRecoveryHeavyStabilizationService(replay_service=_ReplayService())

    with pytest.raises(ValueError, match="exactly one"):
        service.stabilize(
            build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
            generate=lambda _pressure: _plan(2.0),
            resource=ResourceType.MAGICKA,
            maximum_amount=10000,
            trigger_fraction=0.30,
            restoration_resolver=lambda _action: None,
            restoration_resolver_factory=lambda _plan: (lambda _action: None),
        )


def test_missing_resolver_source_fails_closed() -> None:
    service = RotationRecoveryHeavyStabilizationService(replay_service=_ReplayService())

    with pytest.raises(ValueError, match="exactly one"):
        service.stabilize(
            build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
            generate=lambda _pressure: _plan(2.0),
            resource=ResourceType.MAGICKA,
            maximum_amount=10000,
            trigger_fraction=0.30,
        )
