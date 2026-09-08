from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services import extreme_actual_heal_optimization_service as base_module
from services.extreme_templar_conditional_actual_heal_service import (
    ExtremeTemplarConditionalActualHealService,
)


class _Event:
    def __init__(self, entity_id: str):
        self.entity_id = entity_id
        self.critical_heal = 150.0
        self.normal_heal = 100.0
        self.unresolved = ()
        self.mechanic_complete = True
        self.tooltip_result = None


class _HealingEvents:
    def evaluate(self, *, build, context, entity_id, **kwargs):
        _ = build, context, kwargs
        return _Event(entity_id)


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


class _IlluminateState:
    def __init__(self, *, active=True, unresolved=()):
        self.active = active
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, progression, illuminate_window_active):
        self.calls.append((build.BuildName, progression, illuminate_window_active))
        buffs = ("Minor Sorcery",) if self.active else ()
        return SimpleNamespace(
            combat_state=CombatState(in_combat=True, active_buffs=buffs),
            unresolved=self.unresolved,
        )


def _install_progression_adapter(monkeypatch):
    resolution = SimpleNamespace(
        resolved=True,
        character_id="char-1",
        progression=CharacterProgression(
            attributes=AttributeAllocation(),
            passive_ranks={"Illuminate": 2},
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


def test_illuminate_state_is_present_before_every_conditional_heal_context(monkeypatch):
    _install_progression_adapter(monkeypatch)
    optimizer = _Optimizer()
    illuminate = _IlluminateState()
    service = ExtremeTemplarConditionalActualHealService(
        target_health_fraction=0.25,
        illuminate_window_active=True,
        templar_illuminate_state=illuminate,
        optimizer=optimizer,
        healing_events=_HealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Illuminated Templar", EsoClass="Templar"),
        "blessing_of_protection",
        max_passes=1,
    )

    assert illuminate.calls
    assert optimizer.context_factory.combat_states
    assert all(
        state.has_buff("Minor Sorcery")
        for state in optimizer.context_factory.combat_states
    )
    assert "Illuminate active window" in result.search_scope[1]
    assert "before coefficient evaluation" in result.search_scope[1]


def test_illuminate_state_is_not_added_without_explicit_window(monkeypatch):
    _install_progression_adapter(monkeypatch)
    optimizer = _Optimizer()
    illuminate = _IlluminateState()
    service = ExtremeTemplarConditionalActualHealService(
        target_health_fraction=0.25,
        illuminate_window_active=False,
        templar_illuminate_state=illuminate,
        optimizer=optimizer,
        healing_events=_HealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Standing Templar", EsoClass="Templar"),
        "blessing_of_protection",
        max_passes=1,
    )

    assert illuminate.calls == []
    assert optimizer.context_factory.combat_states
    assert all(
        not state.has_buff("Minor Sorcery")
        for state in optimizer.context_factory.combat_states
    )
    assert all("Illuminate active window" not in item for item in result.search_scope)


def test_illuminate_legality_blocker_survives_conditional_optimization(monkeypatch):
    _install_progression_adapter(monkeypatch)
    blocker = "Illuminate scenario requires an equipped Dawn's Wrath class line"
    service = ExtremeTemplarConditionalActualHealService(
        target_health_fraction=0.25,
        illuminate_window_active=True,
        templar_illuminate_state=_IlluminateState(active=False, unresolved=(blocker,)),
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Blocked Illuminate", EsoClass="Templar"),
        "blessing_of_protection",
        max_passes=1,
    )

    assert blocker in result.unresolved
    assert not result.mechanic_complete
