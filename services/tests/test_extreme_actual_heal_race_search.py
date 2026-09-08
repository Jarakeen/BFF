from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services import extreme_actual_heal_optimization_service as module
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)


class _RaceRepository:
    def list_races(self):
        return [
            SimpleNamespace(name="Breton"),
            SimpleNamespace(name="High Elf"),
            SimpleNamespace(name="Khajiit"),
        ]


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


class _RaceHealingEvents:
    VALUES = {
        "Breton": 100.0,
        "High Elf": 140.0,
        "Khajiit": 125.0,
    }

    def evaluate(self, *, build, context, entity_id):
        _ = context
        critical = self.VALUES.get(build.Race, 90.0) + float(build.AttributeMagicka or 0)
        return SimpleNamespace(
            entity_id=entity_id,
            critical_heal=critical,
            normal_heal=critical / 1.5,
            unresolved=(),
            mechanic_complete=True,
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


def test_actual_heal_race_candidates_cover_every_other_canonical_race():
    service = ExtremeActualHealOptimizationService(
        optimizer=_Optimizer(),
        healing_events=_RaceHealingEvents(),
        race_repository=_RaceRepository(),
    )
    baseline = PlayerBuild(BuildName="Heal Baseline", Race="Breton")

    candidates = service._race_candidates(
        baseline,
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert {candidate.candidate_build.Race for candidate in candidates} == {
        "High Elf",
        "Khajiit",
    }
    assert all(candidate.changes[0].path == "Race" for candidate in candidates)
    assert baseline.Race == "Breton"


def test_actual_heal_optimizer_can_select_best_race_and_resource_together(monkeypatch):
    _install_progression_adapter(monkeypatch)
    service = ExtremeActualHealOptimizationService(
        optimizer=_Optimizer(),
        healing_events=_RaceHealingEvents(),
        race_repository=_RaceRepository(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Heal Baseline", Race="Breton"),
        "test_heal",
        max_passes=4,
    )

    assert result.optimized_build.Race == "High Elf"
    assert result.optimized_build.AttributeMagicka == 64
    assert result.optimized_event.critical_heal == 204.0
    assert {step.path for step in result.steps} == {"Race", "Attributes"}
    assert "race" in result.search_scope
    assert "race change" not in result.omitted_scope
