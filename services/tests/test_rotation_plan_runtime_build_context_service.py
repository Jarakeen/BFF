from types import SimpleNamespace

from minmax.combat_state import CombatState
from services.rotation_plan_runtime_build_context_service import (
    RotationPlanRuntimeBuildContextService,
)
from services.rotation_plan_runtime_combat_state_service import (
    RotationPlanRuntimeCombatStateResult,
)


class _StaticContextService:
    def __init__(self, *, context=None, unresolved=()) -> None:
        self.context = context
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, build, *, bars, combat_state):
        self.calls.append(
            {
                "build": build,
                "bars": bars,
                "combat_state": combat_state,
            }
        )
        context = self.context
        return SimpleNamespace(
            resolved=context is not None and not self.unresolved,
            unresolved=self.unresolved,
            context_for=lambda bar: context if bar == bars[0] else None,
        )


def test_rebuilds_exact_active_bar_context_from_runtime_combat_state() -> None:
    build = object()
    runtime_state = CombatState(
        in_combat=True,
        active_buffs=("Major Sorcery",),
        game_update="U51",
    )
    rebuilt_context = object()
    static = _StaticContextService(context=rebuilt_context)
    service = RotationPlanRuntimeBuildContextService(static_context_service=static)
    calls = []

    def runtime_resolver(time_seconds, sequence=None):
        calls.append((time_seconds, sequence))
        return RotationPlanRuntimeCombatStateResult(
            time_seconds=float(time_seconds),
            sequence=sequence,
            active_bar="back",
            combat_state=runtime_state,
            unresolved=(),
        )

    result = service.resolve(
        build,
        runtime_combat_state_resolver=runtime_resolver,
        time_seconds=12.5,
        sequence=3,
    )

    assert result.resolved
    assert result.context is rebuilt_context
    assert result.active_bar == "back"
    assert result.time_seconds == 12.5
    assert result.sequence == 3
    assert calls == [(12.5, 3)]
    assert static.calls == [
        {
            "build": build,
            "bars": ("back",),
            "combat_state": runtime_state,
        }
    ]


def test_unresolved_runtime_state_blocks_context_rebuild() -> None:
    static = _StaticContextService(context=object())
    service = RotationPlanRuntimeBuildContextService(static_context_service=static)

    def runtime_resolver(time_seconds, sequence=None):
        return RotationPlanRuntimeCombatStateResult(
            time_seconds=float(time_seconds),
            sequence=sequence,
            active_bar="front",
            combat_state=None,
            unresolved=("runtime proc window unresolved",),
        )

    result = service.resolve(
        object(),
        runtime_combat_state_resolver=runtime_resolver,
        time_seconds=4.0,
        sequence=1,
    )

    assert not result.resolved
    assert result.context is None
    assert result.unresolved == ("runtime proc window unresolved",)
    assert static.calls == []


def test_unresolved_rebuilt_context_fails_closed() -> None:
    static = _StaticContextService(
        context=None,
        unresolved=("back static context: runtime gear effect unresolved",),
    )
    service = RotationPlanRuntimeBuildContextService(static_context_service=static)

    def runtime_resolver(time_seconds, sequence=None):
        return RotationPlanRuntimeCombatStateResult(
            time_seconds=float(time_seconds),
            sequence=sequence,
            active_bar="back",
            combat_state=CombatState(in_combat=True),
            unresolved=(),
        )

    result = service.resolve(
        object(),
        runtime_combat_state_resolver=runtime_resolver,
        time_seconds=9.0,
    )

    assert not result.resolved
    assert result.context is None
    assert result.unresolved == (
        "back static context: runtime gear effect unresolved",
    )
