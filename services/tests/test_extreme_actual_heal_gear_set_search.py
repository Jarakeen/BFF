from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services import extreme_actual_heal_optimization_service as module
from services.extreme_actual_heal_optimization_service import ExtremeActualHealOptimizationService
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService


class _Event:
    def __init__(self, entity_id: str, critical_heal: float):
        self.entity_id = entity_id
        self.critical_heal = critical_heal
        self.normal_heal = critical_heal / 1.5
        self.unresolved = ()
        self.mechanic_complete = True


class _HealingEvents:
    def evaluate(self, *, build, context, entity_id):
        _ = context
        equipped = {str(entry.get("Set", "") or "") for entry in build.Armor.values()}
        bonus = 50.0 if "Healing Power" in equipped else 0.0
        return _Event(entity_id, 100.0 + bonus)


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


class _GearSetCandidates:
    @staticmethod
    def build_candidates(baseline_build, *, character_id, baseline_build_id):
        build = PlayerBuild.from_dict(baseline_build.to_dict())
        for slot in ("Chest", "Legs", "Head", "Shoulders", "Hands"):
            build.Armor[slot]["Set"] = "Healing Power"
        return (
            ExtremeCompleteOptimizationService._direct_candidate(
                build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                token="actual-heal-five-piece:Healing Power",
                path="Armor.PrimaryFivePieceSet",
                before={},
                after={slot: "Healing Power" for slot in ("Chest", "Legs", "Head", "Shoulders", "Hands")},
                source="extreme:actual-heal:gear-set",
            ),
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

    monkeypatch.setattr(module, "MinmaxCharacterProgressionAdapter", _Adapter)


def test_actual_heal_optimizer_accepts_better_five_piece_set(monkeypatch):
    _install_progression_adapter(monkeypatch)
    service = ExtremeActualHealOptimizationService(
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        race_repository=SimpleNamespace(list_races=lambda: []),
        gear_set_candidates=_GearSetCandidates(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Heal Baseline"),
        "test_heal",
        max_passes=2,
    )

    assert result.baseline_event.critical_heal == pytest.approx(100.0)
    assert result.optimized_event.critical_heal == pytest.approx(150.0)
    assert result.steps[-1].path == "Armor.PrimaryFivePieceSet"
    assert sum(
        1 for slot in result.optimized_build.Armor.values()
        if slot["Set"] == "Healing Power"
    ) == 5
    assert "reviewed ordinary five-piece body-set replacement" in result.search_scope
