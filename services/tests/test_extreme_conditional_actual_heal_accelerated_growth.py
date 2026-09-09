from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)


class _Optimizer:
    database_path = None

    def __init__(self):
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=object())
        )
        self.context_factory = SimpleNamespace()

    @staticmethod
    def objective(key):
        return SimpleNamespace(key=key)

    @staticmethod
    def _candidates(*args, **kwargs):
        _ = args, kwargs
        return ()


class _AcceleratedGrowthState:
    def __init__(self, *, unresolved=()):
        self.calls = []
        self.unresolved = tuple(unresolved)

    def resolve(
        self,
        *,
        build,
        progression,
        accelerated_growth_window_active,
    ):
        self.calls.append(
            (
                build.BuildName,
                progression,
                accelerated_growth_window_active,
            )
        )
        return SimpleNamespace(
            combat_state=CombatState(
                in_combat=True,
                active_buffs=("Major Mending",),
            ),
            unresolved=self.unresolved,
        )


def _service(*, window_active, state, active_buffs=()):
    return ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        accelerated_growth_window_active=window_active,
        active_buffs=active_buffs,
        warden_accelerated_growth_state=state,
        optimizer=_Optimizer(),
        healing_events=object(),
    )


def _progression():
    return CharacterProgression(
        passive_ranks={"Accelerated Growth": 2},
        passive_cp_points={},
    )


def test_conditional_state_routes_accelerated_growth_major_mending():
    state = _AcceleratedGrowthState()
    service = _service(window_active=True, state=state)

    combat_state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Warden Emergency"),
        progression=_progression(),
        active_bar="front",
    )

    assert state.calls
    assert state.calls[0][2] is True
    assert combat_state.in_combat is True
    assert combat_state.has_buff("Major Mending")
    assert unresolved == ()


def test_conditional_state_does_not_invent_accelerated_growth_window():
    state = _AcceleratedGrowthState()
    service = _service(window_active=False, state=state)

    combat_state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Standing Warden"),
        progression=_progression(),
        active_bar="front",
    )

    assert state.calls == []
    assert combat_state.has_buff("Major Mending") is False
    assert unresolved == ()


def test_conditional_state_deduplicates_major_mending_sources():
    state = _AcceleratedGrowthState()
    service = _service(
        window_active=True,
        state=state,
        active_buffs=("Major Mending",),
    )

    combat_state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Double Source Warden"),
        progression=_progression(),
        active_bar="front",
    )

    assert combat_state.active_buffs == ("Major Mending",)
    assert unresolved == ()


def test_conditional_state_preserves_accelerated_growth_blockers():
    state = _AcceleratedGrowthState(
        unresolved=("Accelerated Growth passive rank is not recorded",)
    )
    service = _service(window_active=True, state=state)

    combat_state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Unresolved Warden"),
        progression=_progression(),
        active_bar="front",
    )

    assert combat_state.has_buff("Major Mending")
    assert unresolved == ("Accelerated Growth passive rank is not recorded",)
