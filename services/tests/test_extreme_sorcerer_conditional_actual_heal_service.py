from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services import extreme_actual_heal_optimization_service as base_module
from services.extreme_sorcerer_conditional_actual_heal_service import (
    ExtremeSorcererConditionalActualHealService,
)


class _Event:
    def __init__(self, entity_id: str, max_health: int):
        self.entity_id = entity_id
        self.critical_heal = float(max_health)
        self.normal_heal = float(max_health)
        self.unresolved = ()
        self.mechanic_complete = True
        self.tooltip_result = None


class _HealingEvents:
    def __init__(self):
        self.contexts = []

    def evaluate(self, *, context, entity_id, **kwargs):
        _ = kwargs
        self.contexts.append(context)
        return _Event(entity_id, context.character_state.max_health)


class _PetContext:
    def __init__(self, *, max_health=16800, unresolved=()):
        self.max_health = max_health
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        context = SimpleNamespace(
            character_state=SimpleNamespace(max_health=self.max_health),
            unresolved_gear_effects=(),
        )
        return SimpleNamespace(
            context=context,
            max_health_bonus_active=bool(kwargs["permanent_pet_active"]),
            unresolved=self.unresolved,
        )


class _Optimizer:
    database_path = None

    def __init__(self):
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=object())
        )
        self.context_factory = object()

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
            passive_ranks={"Expert Summoner": 2},
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


def test_permanent_pet_context_is_used_before_heal_scoring(monkeypatch):
    _install_progression_adapter(monkeypatch)
    pet = _PetContext(max_health=16800)
    healing = _HealingEvents()
    service = ExtremeSorcererConditionalActualHealService(
        target_health_fraction=0.25,
        permanent_pet_active=True,
        expert_summoner_pet_context=pet,
        optimizer=_Optimizer(),
        healing_events=healing,
    )

    result = service.optimize(
        PlayerBuild(BuildName="Pet Sorcerer", EsoClass="Sorcerer"),
        "health_scaled_heal",
        max_passes=1,
    )

    assert pet.calls
    assert all(call["permanent_pet_active"] for call in pet.calls)
    assert healing.contexts
    assert result.optimized_event.critical_heal == 16800.0
    assert "permanent pet active" in result.search_scope[1]
    assert "before healing coefficient evaluation" in result.search_scope[1]


def test_inactive_pet_scenario_stays_explicitly_unbuffed(monkeypatch):
    _install_progression_adapter(monkeypatch)
    pet = _PetContext(max_health=16000)
    service = ExtremeSorcererConditionalActualHealService(
        target_health_fraction=0.25,
        permanent_pet_active=False,
        expert_summoner_pet_context=pet,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="No Pet Sorcerer", EsoClass="Sorcerer"),
        "health_scaled_heal",
        max_passes=1,
    )

    assert pet.calls
    assert all(not call["permanent_pet_active"] for call in pet.calls)
    assert result.optimized_event.critical_heal == 16000.0
    assert all("permanent pet active" not in item for item in result.search_scope)


def test_pet_legality_blocker_survives_conditional_optimization(monkeypatch):
    _install_progression_adapter(monkeypatch)
    blocker = "Expert Summoner permanent-pet scenario requires an equipped Daedric Summoning class line"
    service = ExtremeSorcererConditionalActualHealService(
        target_health_fraction=0.25,
        permanent_pet_active=True,
        expert_summoner_pet_context=_PetContext(max_health=16000, unresolved=(blocker,)),
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Blocked Pet", EsoClass="Sorcerer"),
        "health_scaled_heal",
        max_passes=1,
    )

    assert blocker in result.unresolved
    assert not result.mechanic_complete
