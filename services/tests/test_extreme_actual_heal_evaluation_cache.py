from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services import extreme_actual_heal_optimization_service as module
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)


class _Event:
    entity_id = "blessing_of_protection"
    critical_heal = 100.0
    normal_heal = 66.6666667
    unresolved = ()
    mechanic_complete = True


class _HealingEvents:
    def __init__(self):
        self.calls = 0

    def evaluate(self, *, build, context, entity_id):
        _ = build, context, entity_id
        self.calls += 1
        return _Event()


class _ContextFactory:
    def __init__(self):
        self.calls = 0

    def build(self, **kwargs):
        _ = kwargs
        self.calls += 1
        return SimpleNamespace(unresolved_gear_effects=())


class _Optimizer:
    database_path = None

    def __init__(self):
        self.context_factory = _ContextFactory()
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=object())
        )

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

    monkeypatch.setattr(module, "MinmaxCharacterProgressionAdapter", _Adapter)


def test_shared_cache_reuses_identical_structural_evaluations(monkeypatch):
    _install_progression_adapter(monkeypatch)
    optimizer = _Optimizer()
    events = _HealingEvents()
    service = ExtremeActualHealOptimizationService(
        optimizer=optimizer,
        healing_events=events,
    )
    build = PlayerBuild(BuildName="Cache Baseline")
    shared_cache = {}

    first = service.optimize(
        build,
        "blessing_of_protection",
        max_passes=1,
        evaluation_cache=shared_cache,
    )
    context_calls_after_first = optimizer.context_factory.calls
    event_calls_after_first = events.calls

    second = service.optimize(
        PlayerBuild.from_dict(build.to_dict()),
        "blessing_of_protection",
        max_passes=1,
        evaluation_cache=shared_cache,
    )

    assert first.optimized_event.critical_heal == second.optimized_event.critical_heal
    assert context_calls_after_first > 0
    assert event_calls_after_first > 0
    assert optimizer.context_factory.calls == context_calls_after_first
    assert events.calls == event_calls_after_first


def test_cache_key_keeps_entity_and_progression_distinct(monkeypatch):
    _install_progression_adapter(monkeypatch)
    optimizer = _Optimizer()
    service = ExtremeActualHealOptimizationService(
        optimizer=optimizer,
        healing_events=_HealingEvents(),
    )
    build = PlayerBuild(BuildName="Cache Baseline")
    cache = {}
    base_progression = CharacterProgression(
        attributes=AttributeAllocation(),
        owned_skill_lines=("green_balance",),
    )
    other_progression = CharacterProgression(
        attributes=AttributeAllocation(),
        owned_skill_lines=("daedric_summoning",),
    )

    key_a = service._evaluation_key(
        build,
        progression=base_progression,
        character_id="char-1",
        entity_id="heal_a",
        active_bar="front",
    )
    key_b = service._evaluation_key(
        build,
        progression=base_progression,
        character_id="char-1",
        entity_id="heal_b",
        active_bar="front",
    )
    key_c = service._evaluation_key(
        build,
        progression=other_progression,
        character_id="char-1",
        entity_id="heal_a",
        active_bar="front",
    )

    assert key_a != key_b
    assert key_a != key_c
    assert cache == {}
