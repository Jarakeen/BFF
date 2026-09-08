from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services import extreme_actual_heal_optimization_service as module
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)
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
        five_slots = ("Chest", "Legs", "Hands", "Waist", "Feet")
        has_five = all(build.Armor[slot]["Set"] == "Body Healer" for slot in five_slots)
        has_monster = (
            build.Armor["Head"]["Set"] == "Monster Healer"
            and build.Armor["Shoulders"]["Set"] == "Monster Healer"
        )
        return _Event(entity_id, 250.0 if has_five and has_monster else 100.0)


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


class _MonsterPackages:
    @staticmethod
    def build_candidates(baseline_build, *, character_id, baseline_build_id):
        build = PlayerBuild.from_dict(baseline_build.to_dict())
        five_slots = ("Chest", "Legs", "Hands", "Waist", "Feet")
        for slot in five_slots:
            build.Armor[slot]["Set"] = "Body Healer"
        build.Armor["Head"]["Set"] = "Monster Healer"
        build.Armor["Shoulders"]["Set"] = "Monster Healer"
        return (
            ExtremeCompleteOptimizationService._direct_candidate(
                build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                token="actual-heal-5plus2:Body Healer:Monster Healer",
                path="Armor.FivePiecePlusMonster",
                before={},
                after={"five": "Body Healer", "monster": "Monster Healer"},
                source="test:5+2",
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


def test_actual_heal_optimizer_can_select_five_plus_monster_package(monkeypatch):
    _install_progression_adapter(monkeypatch)
    service = ExtremeActualHealOptimizationService(
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        monster_packages=_MonsterPackages(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Heal Baseline"),
        "test_heal",
        max_passes=2,
    )

    assert result.baseline_event.critical_heal == 100.0
    assert result.optimized_event.critical_heal == 250.0
    assert result.gain == 150.0
    assert result.steps[-1].path == "Armor.FivePiecePlusMonster"
    assert result.optimized_build.Armor["Head"]["Set"] == "Monster Healer"
    assert result.optimized_build.Armor["Shoulders"]["Set"] == "Monster Healer"
    assert sum(
        1
        for slot in ("Chest", "Legs", "Hands", "Waist", "Feet")
        if result.optimized_build.Armor[slot]["Set"] == "Body Healer"
    ) == 5
