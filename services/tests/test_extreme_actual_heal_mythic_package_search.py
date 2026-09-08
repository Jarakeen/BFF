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
        has_primary = all(
            build.Armor[slot]["Set"] == "Primary Healer"
            for slot in ("Chest", "Legs", "Hands", "Waist", "Feet")
        )
        has_secondary = (
            build.Armor["Head"]["Set"] == "Secondary Healer"
            and build.Armor["Shoulders"]["Set"] == "Secondary Healer"
            and build.Necklace.Set == "Secondary Healer"
            and build.FrontBarWeapon.Set == "Secondary Healer"
        )
        has_mythic = build.Ring1.Set == "Ring Mythic"
        score = 410.0 if has_primary and has_secondary and has_mythic else 100.0
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


class _MythicPackages:
    @staticmethod
    def build_candidates(
        baseline_build,
        *,
        character_id,
        baseline_build_id,
        active_bar="front",
    ):
        build = PlayerBuild.from_dict(baseline_build.to_dict())
        for slot in ("Chest", "Legs", "Hands", "Waist", "Feet"):
            build.Armor[slot]["Set"] = "Primary Healer"
        build.Armor["Head"]["Set"] = "Secondary Healer"
        build.Armor["Shoulders"]["Set"] = "Secondary Healer"
        build.Necklace.Set = "Secondary Healer"
        main, _offhand = build.active_weapon_slots(active_bar)
        main.Set = "Secondary Healer"
        build.Ring1.Set = "Ring Mythic"
        return (
            ExtremeCompleteOptimizationService._direct_candidate(
                build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                token="actual-heal-5plus5plus1:test",
                path="Gear.FivePiecePlusFivePiecePlusRingMythic",
                before={},
                after={
                    "primary": "Primary Healer",
                    "secondary": "Secondary Healer",
                    "mythic": "Ring Mythic",
                },
                source="test:5+5+1:ring-mythic",
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


def test_actual_heal_optimizer_can_select_ring_mythic_five_plus_five_plus_one(monkeypatch):
    _install_progression_adapter(monkeypatch)
    baseline = PlayerBuild(BuildName="Heal Baseline")
    baseline.FrontBarWeapon.WeaponType = "Restoration Staff"
    service = ExtremeActualHealOptimizationService(
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        mythic_packages=_MythicPackages(),
    )

    result = service.optimize(
        baseline,
        "test_heal",
        max_passes=2,
    )

    assert result.baseline_event.critical_heal == 100.0
    assert result.optimized_event.critical_heal == 410.0
    assert result.gain == 310.0
    assert result.steps[-1].path == "Gear.FivePiecePlusFivePiecePlusRingMythic"
    assert result.optimized_build.Ring1.Set == "Ring Mythic"
    assert result.optimized_build.FrontBarWeapon.Set == "Secondary Healer"
    assert result.optimized_build.FrontBarWeapon.WeaponType == "Restoration Staff"
    assert any("ring mythic" in item for item in result.search_scope)
    assert any("exact active weapon subtype proof" in item for item in result.search_scope)
    assert any("arena-weapon" in item and "paired main/off-hand" in item for item in result.search_scope)
    assert not any("weapon-subtype" in item for item in result.omitted_scope)
    assert result.omitted_scope[0] == "non-ring mythics"
