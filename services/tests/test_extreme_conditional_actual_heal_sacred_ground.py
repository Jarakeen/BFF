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


class _HealingEvents:
    pass


class _SacredGroundState:
    def __init__(self, *, unresolved=()):
        self.calls = []
        self.unresolved = tuple(unresolved)

    def resolve(self, *, build, progression, sacred_ground_window_active):
        self.calls.append(
            (build.BuildName, progression, sacred_ground_window_active)
        )
        return SimpleNamespace(
            combat_state=CombatState(
                in_combat=True,
                active_buffs=("Minor Mending",) if not self.unresolved else (),
            ),
            unresolved=self.unresolved,
        )


class _HeavyState:
    def resolve(
        self,
        *,
        build,
        progression,
        active_bar,
        fully_charged_heavy_attack_completed,
    ):
        _ = build, progression, active_bar, fully_charged_heavy_attack_completed
        return SimpleNamespace(
            combat_state=CombatState(
                in_combat=True,
                active_buffs=("Major Mending",),
            ),
            unresolved=(),
        )


def _progression():
    return CharacterProgression(
        passive_ranks={"Sacred Ground": 2, "Essence Drain": 2},
        passive_cp_points={},
    )


def test_conditional_state_routes_sacred_ground_minor_mending():
    sacred = _SacredGroundState()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        sacred_ground_window_active=True,
        templar_sacred_ground_state=sacred,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Sacred Ground Templar", EsoClass="Templar"),
        progression=_progression(),
        active_bar="front",
    )

    assert state.has_buff("Minor Mending")
    assert not state.has_buff("Major Mending")
    assert unresolved == ()
    assert sacred.calls and sacred.calls[0][2] is True


def test_conditional_state_can_combine_minor_and_major_mending():
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        sacred_ground_window_active=True,
        fully_charged_restoration_heavy_attack_completed=True,
        templar_sacred_ground_state=_SacredGroundState(),
        restoration_heavy_state=_HeavyState(),
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Double Mending", EsoClass="Templar"),
        progression=_progression(),
        active_bar="front",
    )

    assert state.has_buff("Minor Mending")
    assert state.has_buff("Major Mending")
    assert unresolved == ()


def test_conditional_state_preserves_sacred_ground_blocker_without_minor_mending():
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        sacred_ground_window_active=True,
        templar_sacred_ground_state=_SacredGroundState(
            unresolved=("Sacred Ground passive rank unresolved",)
        ),
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Blocked Sacred Ground", EsoClass="Templar"),
        progression=_progression(),
        active_bar="front",
    )

    assert not state.has_buff("Minor Mending")
    assert unresolved == ("Sacred Ground passive rank unresolved",)
