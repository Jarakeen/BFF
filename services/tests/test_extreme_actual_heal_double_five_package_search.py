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
        primary_slots = ("Chest", "Legs", "Hands", "Waist", "Feet")
        secondary_armor = ("Head", "Shoulders")
        has_primary = all(
            build.Armor[slot]["Set"] == "Primary Healer"
            for slot in primary_slots
        )
        has_secondary_armor = all(
            build.Armor[slot]["Set"] == "Secondary Healer"
            for slot in secondary_armor
        )
        has_secondary_jewelry = (
            build.Necklace.Set == "Secondary Healer"
            and build.Ring1.Set == "Secondary Healer"
            and build.Ring2.Set == "Secondary Healer"
        )
        score = 320.0 if (
            has_primary and has_secondary_armor and has_secondary_jewelry
        ) else 100.0
        return _Event(entity_id, score)


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


class _DoubleFivePackages:
    @staticmethod
    def build_candidates(baseline_build, *, character_id, baseline_build_id):
        build = PlayerBuild.from_dict(baseline_build.to_dict())
        for slot in ("Chest", "Legs", "Hands", "Waist", "Feet"):
            build.Armor[slot]["Set"] = "Primary Healer"
        for slot in ("Head", "Shoulders"):
            build.Armor[slot]["Set"] = "Secondary Healer"
        build.Necklace.Set = "Secondary Healer"
        build.Ring1.Set = "Secondary Healer"
        build.Ring2.Set = "Secondary Healer"

        return (
            ExtremeCompleteOptimizationService._direct_candidate(
                build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                token="actual-heal-5plus5:Primary Healer:Secondary Healer",
                path="Gear.FivePiecePlusFivePiece",
                before={},
                after={
                    "primary": "Primary Healer",
                    "secondary": "Secondary Healer",
                },
                source="test:5+5",
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


def test_actual_heal_optimizer_can_select_double_five_package(monkeypatch):
    _install_progression_adapter(monkeypatch)
    service = ExtremeActualHealOptimizationService(
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        double_five_packages=_DoubleFivePackages(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Heal Baseline"),
        "test_heal",
        max_passes=2,
    )

    assert result.baseline_event.critical_heal == 100.0
    assert result.optimized_event.critical_heal == 320.0
    assert result.gain == 220.0
    assert result.steps[-1].path == "Gear.FivePiecePlusFivePiece"
    assert sum(
        1
        for slot in ("Chest", "Legs", "Hands", "Waist", "Feet")
        if result.optimized_build.Armor[slot]["Set"] == "Primary Healer"
    ) == 5
    assert result.optimized_build.Armor["Head"]["Set"] == "Secondary Healer"
    assert result.optimized_build.Armor["Shoulders"]["Set"] == "Secondary Healer"
    assert result.optimized_build.Necklace.Set == "Secondary Healer"
    assert result.optimized_build.Ring1.Set == "Secondary Healer"
    assert result.optimized_build.Ring2.Set == "Secondary Healer"
    assert "reviewed legal five-piece + five-piece body/jewelry package" in result.search_scope
    assert (
        "reviewed legal five-piece + five-piece + ring mythic package with exact active weapon subtype proof"
        in result.search_scope
    )
    assert any("arena-weapon" in item for item in result.search_scope)
    assert "non-ring mythics / paired one-hand arena-weapon packages" in result.omitted_scope
    assert not any(
        item == "five-piece + five-piece package search"
        for item in result.omitted_scope
    )
