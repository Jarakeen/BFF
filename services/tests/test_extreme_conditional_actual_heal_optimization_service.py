from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services import extreme_actual_heal_optimization_service as base_module
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)


class _Event:
    def __init__(self, entity_id: str, critical_heal: float):
        self.entity_id = entity_id
        self.critical_heal = critical_heal
        self.normal_heal = critical_heal / 1.5
        self.unresolved = ()
        self.mechanic_complete = True


class _ConditionalHealingEvents:
    def __init__(self):
        self.target_health_fractions = []

    def evaluate(self, *, build, context, entity_id, target_health_fraction=None):
        _ = context
        self.target_health_fractions.append(target_health_fraction)
        conditional = 100.0 if target_health_fraction is not None and target_health_fraction <= 0.30 else 0.0
        return _Event(
            entity_id,
            100.0 + float(build.AttributeMagicka or 0) + conditional,
        )


class _ContextFactory:
    def __init__(self):
        self.combat_states = []

    def build(self, **kwargs):
        self.combat_states.append(kwargs.get("combat_state", CombatState()))
        return SimpleNamespace(unresolved_gear_effects=())


class _Optimizer:
    database_path = None

    def __init__(self):
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=object())
        )
        self.context_factory = _ContextFactory()

    @staticmethod
    def objective(key):
        return SimpleNamespace(key=key)

    @staticmethod
    def _candidates(*args, **kwargs):
        _ = args, kwargs
        return ()


class _RestorationHeavyState:
    def __init__(self, *, unresolved=()):
        self.calls = []
        self.unresolved = tuple(unresolved)

    def resolve(
        self,
        *,
        build,
        progression,
        active_bar,
        fully_charged_heavy_attack_completed,
    ):
        self.calls.append(
            (
                build.BuildName,
                progression,
                active_bar,
                fully_charged_heavy_attack_completed,
            )
        )
        return SimpleNamespace(
            combat_state=CombatState(in_combat=True, active_buffs=("Major Mending",)),
            unresolved=self.unresolved,
        )


def _install_progression_adapter(monkeypatch):
    resolution = SimpleNamespace(
        resolved=True,
        character_id="char-1",
        progression=CharacterProgression(
            attributes=AttributeAllocation(),
            passive_ranks={},
            passive_cp_points={},
        ),
        unresolved=(),
    )

    class _Adapter:
        def __init__(self, catalog):
            _ = catalog

        def resolve(self, build):
            _ = build
            return resolution

    monkeypatch.setattr(base_module, "MinmaxCharacterProgressionAdapter", _Adapter)


def test_conditional_optimizer_forwards_target_health_to_every_candidate(monkeypatch):
    _install_progression_adapter(monkeypatch)
    healing_events = _ConditionalHealingEvents()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        optimizer=_Optimizer(),
        healing_events=healing_events,
    )

    result = service.optimize(
        PlayerBuild(BuildName="Emergency Heal"),
        "blessing_of_protection",
        max_passes=2,
    )

    assert healing_events.target_health_fractions
    assert set(healing_events.target_health_fractions) == {0.29}
    assert result.baseline_event.critical_heal == pytest.approx(200.0)
    assert result.optimized_event.critical_heal == pytest.approx(264.0)
    assert result.optimized_build.AttributeMagicka == 64


def test_conditional_optimizer_requires_explicit_valid_target_health():
    with pytest.raises(ValueError, match="between 0 and 1"):
        ExtremeConditionalActualHealOptimizationService(
            target_health_fraction=1.01,
            optimizer=_Optimizer(),
            healing_events=_ConditionalHealingEvents(),
        )


def test_conditional_optimizer_keeps_target_health_as_explicit_scenario_state():
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.30,
        optimizer=_Optimizer(),
        healing_events=_ConditionalHealingEvents(),
    )

    assert service.target_health_fraction == pytest.approx(0.30)
    assert service.fully_charged_restoration_heavy_attack_completed is False


def test_conditional_optimizer_routes_explicit_restoration_heavy_state_to_every_context(monkeypatch):
    _install_progression_adapter(monkeypatch)
    optimizer = _Optimizer()
    heavy_state = _RestorationHeavyState()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        fully_charged_restoration_heavy_attack_completed=True,
        restoration_heavy_state=heavy_state,
        optimizer=optimizer,
        healing_events=_ConditionalHealingEvents(),
    )

    service.optimize(
        PlayerBuild(BuildName="Post Heavy Emergency"),
        "blessing_of_protection",
        max_passes=2,
    )

    assert heavy_state.calls
    assert all(call[2:] == ("front", True) for call in heavy_state.calls)
    assert optimizer.context_factory.combat_states
    assert all(
        state.has_buff("Major Mending")
        for state in optimizer.context_factory.combat_states
    )


def test_conditional_optimizer_preserves_restoration_heavy_blocker_on_selected_state(monkeypatch):
    _install_progression_adapter(monkeypatch)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        fully_charged_restoration_heavy_attack_completed=True,
        restoration_heavy_state=_RestorationHeavyState(
            unresolved=("Essence Drain passive rank unresolved",)
        ),
        optimizer=_Optimizer(),
        healing_events=_ConditionalHealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Blocked Heavy"),
        "blessing_of_protection",
        max_passes=1,
    )

    assert "Essence Drain passive rank unresolved" in result.unresolved
    assert not result.mechanic_complete
