from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services import extreme_baseline_canonical_actual_heal_optimization_service as heal_module
from services import extreme_baseline_route_aware_max_health_optimization_service as health_module
from services.extreme_baseline_canonical_actual_heal_optimization_service import (
    ExtremeBaselineCanonicalActualHealOptimizationService,
)
from services.extreme_baseline_route_aware_max_health_optimization_service import (
    ExtremeBaselineRouteAwareMaxHealthOptimizationService,
)


class _HealEvent:
    entity_id = "test_heal"
    critical_heal = 1234.0
    normal_heal = 800.0
    mechanic_complete = True
    unresolved = ()


class _HealScreen(ExtremeBaselineCanonicalActualHealOptimizationService):
    def __init__(self):
        self.optimizer = SimpleNamespace(
            build_service=SimpleNamespace(canonical=SimpleNamespace(catalog_service=object()))
        )
        self.calls = []

    def _evaluate(self, build, **kwargs):
        self.calls.append((build, kwargs))
        return _HealEvent(), ()


class _HealthScreen(ExtremeBaselineRouteAwareMaxHealthOptimizationService):
    def __init__(self):
        self.build_service = SimpleNamespace(canonical=SimpleNamespace(catalog_service=object()))
        self._route_progression_override = None
        self.calls = []

    @staticmethod
    def objective(key):
        return SimpleNamespace(key=key, label="Maximum Health", ratio=False)

    def _evaluate(self, build, **kwargs):
        self.calls.append((build, kwargs, self._route_progression_override))
        return 42000.0, ()


def _install_adapter(monkeypatch, module):
    progression = CharacterProgression(owned_skill_lines=("green_balance",))
    resolution = SimpleNamespace(
        resolved=True,
        character_id="char-1",
        progression=progression,
        unresolved=(),
    )

    class _Adapter:
        def __init__(self, catalog):
            _ = catalog

        def resolve(self, build):
            _ = build
            return resolution

    monkeypatch.setattr(module, "MinmaxCharacterProgressionAdapter", _Adapter)
    return progression


def test_actual_heal_screen_performs_one_baseline_evaluation(monkeypatch):
    _install_adapter(monkeypatch, heal_module)
    service = _HealScreen()
    override = CharacterProgression(owned_skill_lines=("restoring_light",))

    result = service.optimize(
        PlayerBuild(BuildName="Screen"),
        "test_heal",
        active_bar="back",
        max_passes=999,
        progression_override=override,
    )

    assert len(service.calls) == 1
    assert service.calls[0][1]["progression"] is override
    assert service.calls[0][1]["active_bar"] == "back"
    assert result.optimized_event.critical_heal == 1234.0
    assert result.steps == ()
    assert any("zero whole-build mutation" in item for item in result.search_scope)


def test_max_health_screen_performs_one_route_aware_evaluation(monkeypatch):
    _install_adapter(monkeypatch, health_module)
    service = _HealthScreen()
    override = CharacterProgression(owned_skill_lines=("dark_magic",))

    result = service.optimize(
        PlayerBuild(BuildName="Health Screen"),
        "max_health",
        active_bar="front",
        max_passes=999,
        progression_override=override,
    )

    assert len(service.calls) == 1
    assert service.calls[0][2] is override
    assert result.baseline_value == 42000.0
    assert result.optimized_value == 42000.0
    assert result.steps == ()
    assert service._route_progression_override is None
