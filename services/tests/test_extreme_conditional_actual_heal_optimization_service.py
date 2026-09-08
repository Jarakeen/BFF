from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import AttributeAllocation, CharacterProgression
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
    def build(self, **kwargs):
        _ = kwargs
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
