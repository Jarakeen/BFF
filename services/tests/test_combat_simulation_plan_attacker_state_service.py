from __future__ import annotations

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.combat_simulation_plan_attacker_state_service import (
    CombatSimulationPlanAttackerStateService,
)


class _PotionState:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def resolve(self, build, **kwargs):
        self.calls.append((build, kwargs))
        return self.result


class _ToggleState:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def resolve(self, build, **kwargs):
        self.calls.append((build, kwargs))
        return self.result


class _ResolvedState:
    def __init__(self, combat_state, unresolved=()):
        self.combat_state = combat_state
        self.unresolved = tuple(unresolved)

    @property
    def resolved(self):
        return self.combat_state is not None and not self.unresolved


def _build():
    return PlayerBuild(
        Name="Damage Tester",
        BuildName="DD",
        Role="DD",
        Potion="Essence of Spell Power",
    )


def _plan():
    return RotationPlan(
        character_name="Damage Tester",
        build_name="DD",
        duration_seconds=10.0,
        actions=(
            RotationAction(2.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        ),
    )


def test_plan_attacker_state_layers_potion_then_toggle_on_exact_active_bar() -> None:
    potion_state = CombatState(active_buffs=("Major Sorcery",))
    toggle_state = CombatState(active_buffs=("Major Sorcery", "Banner"))
    potion = _PotionState(_ResolvedState(potion_state))
    toggle = _ToggleState(_ResolvedState(toggle_state))
    service = CombatSimulationPlanAttackerStateService(
        potion_state_service=potion,
        toggle_state_service=toggle,
    )

    result = service.resolve(
        _build(),
        progression=CharacterProgression(passive_ranks={}, passive_cp_points={}),
        plan=_plan(),
        time_seconds=3.0,
        sequence=0,
    )

    assert result.resolved is True
    assert result.active_bar == "back"
    assert result.combat_state == toggle_state
    assert potion.calls[0][1]["base_combat_state"] == CombatState()
    assert toggle.calls[0][1]["base_combat_state"] == potion_state


def test_plan_attacker_state_fails_closed_when_potion_state_is_unresolved() -> None:
    potion = _PotionState(
        _ResolvedState(None, ("Medicinal Use rank is unresolved",))
    )
    toggle = _ToggleState(_ResolvedState(CombatState()))
    service = CombatSimulationPlanAttackerStateService(
        potion_state_service=potion,
        toggle_state_service=toggle,
    )

    result = service.resolve(
        _build(),
        progression=CharacterProgression(passive_ranks={}, passive_cp_points={}),
        plan=_plan(),
        time_seconds=3.0,
    )

    assert result.combat_state is None
    assert result.unresolved == ("Medicinal Use rank is unresolved",)
    assert toggle.calls == []


def test_plan_attacker_state_resolver_closure_preserves_plan_identity() -> None:
    potion = _PotionState(_ResolvedState(CombatState()))
    toggle = _ToggleState(_ResolvedState(CombatState(active_buffs=("Banner",))))
    service = CombatSimulationPlanAttackerStateService(
        potion_state_service=potion,
        toggle_state_service=toggle,
    )
    build = _build()
    plan = _plan()
    resolver = service.resolver(
        build,
        progression=CharacterProgression(passive_ranks={}, passive_cp_points={}),
        plan=plan,
    )

    result = resolver(1.0, 0)

    assert result.active_bar == "front"
    assert result.combat_state.active_buffs == ("Banner",)
    assert potion.calls[0][1]["plan"] is plan
    assert toggle.calls[0][1]["plan"] is plan
