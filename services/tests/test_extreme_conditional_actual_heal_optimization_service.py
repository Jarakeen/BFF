from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.combat_state import CombatState
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


class _RestorationHeavyState:
    def __init__(self, *, unresolved=()):
        self.calls = []
        self.unresolved = tuple(unresolved)

    def resolve(
        self,
        *,
        build,
        progression,
        active_bar,
        fully_charged_heavy_attack_completed,
    ):
        self.calls.append(
            (
                build.BuildName,
                progression,
                active_bar,
                fully_charged_heavy_attack_completed,
            )
        )
        return SimpleNamespace(
            combat_state=CombatState(in_combat=True, active_buffs=("Major Mending",)),
            unresolved=self.unresolved,
        )



class _PotionUseResolver:
    def __init__(self, *, duration=40.0, unresolved=()):
        self.duration = float(duration)
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, selected_label):
        self.calls.append(selected_label)
        return SimpleNamespace(
            resolved=not self.unresolved,
            unresolved=self.unresolved,
            buff_grants=(
                SimpleNamespace(buff_name="Major Sorcery", duration=self.duration),
            ),
        )

def _install_progression_adapter(monkeypatch, *, passive_ranks=None):
    resolution = SimpleNamespace(
        resolved=True,
        character_id="char-1",
        progression=CharacterProgression(
            attributes=AttributeAllocation(),
            passive_ranks={} if passive_ranks is None else passive_ranks,
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
    assert result.search_scope[0] == "explicit conditional target health fraction 0.290000"


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
    assert service.fully_charged_restoration_heavy_attack_completed is False


def test_conditional_optimizer_routes_explicit_restoration_heavy_state_to_every_context(monkeypatch):
    _install_progression_adapter(monkeypatch)
    optimizer = _Optimizer()
    heavy_state = _RestorationHeavyState()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        fully_charged_restoration_heavy_attack_completed=True,
        restoration_heavy_state=heavy_state,
        optimizer=optimizer,
        healing_events=_ConditionalHealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Post Heavy Emergency"),
        "blessing_of_protection",
        max_passes=2,
    )

    assert heavy_state.calls
    assert all(call[2:] == ("front", True) for call in heavy_state.calls)
    assert optimizer.context_factory.combat_states
    assert all(
        state.has_buff("Major Mending")
        for state in optimizer.context_factory.combat_states
    )
    assert result.search_scope[0] == "explicit conditional target health fraction 0.290000"
    assert "fully charged Restoration Staff heavy attack completed" in result.search_scope[1]
    assert "Essence Drain Major Mending" in result.search_scope[1]


def test_conditional_optimizer_preserves_restoration_heavy_blocker_on_selected_state(monkeypatch):
    _install_progression_adapter(monkeypatch)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        fully_charged_restoration_heavy_attack_completed=True,
        restoration_heavy_state=_RestorationHeavyState(
            unresolved=("Essence Drain passive rank unresolved",)
        ),
        optimizer=_Optimizer(),
        healing_events=_ConditionalHealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Blocked Heavy"),
        "blessing_of_protection",
        max_passes=1,
    )

    assert "Essence Drain passive rank unresolved" in result.unresolved
    assert not result.mechanic_complete


def test_conditional_optimizer_routes_explicit_named_buffs_to_every_context(monkeypatch):
    _install_progression_adapter(monkeypatch)
    optimizer = _Optimizer()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        active_buffs=("Major Sorcery", "Minor Brutality", "Major Sorcery", ""),
        optimizer=optimizer,
        healing_events=_ConditionalHealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Named Buff Emergency"),
        "blessing_of_protection",
        max_passes=2,
    )

    assert service.active_buffs == ("Major Sorcery", "Minor Brutality")
    assert optimizer.context_factory.combat_states
    assert all(
        state.active_buffs == ("Major Sorcery", "Minor Brutality")
        for state in optimizer.context_factory.combat_states
    )
    assert result.search_scope[1] == (
        "explicit active named buffs: Major Sorcery, Minor Brutality"
    )


def test_conditional_optimizer_combines_explicit_named_buffs_with_triggered_mending(monkeypatch):
    _install_progression_adapter(monkeypatch)
    optimizer = _Optimizer()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        active_buffs=("Major Sorcery",),
        fully_charged_restoration_heavy_attack_completed=True,
        restoration_heavy_state=_RestorationHeavyState(),
        optimizer=optimizer,
        healing_events=_ConditionalHealingEvents(),
    )

    service.optimize(
        PlayerBuild(BuildName="Combined Buff Emergency"),
        "blessing_of_protection",
        max_passes=1,
    )

    assert optimizer.context_factory.combat_states
    assert all(
        state.active_buffs == ("Major Sorcery", "Major Mending")
        for state in optimizer.context_factory.combat_states
    )


def test_conditional_optimizer_routes_saved_potion_active_window_to_combat_state(monkeypatch):
    _install_progression_adapter(
        monkeypatch, passive_ranks={"Medicinal Use": 3}
    )
    optimizer = _Optimizer()
    potion_resolver = _PotionUseResolver(duration=40.0)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        potion_elapsed_seconds=20.0,
        potion_use_resolver=potion_resolver,
        optimizer=optimizer,
        healing_events=_ConditionalHealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(
            BuildName="Potion Window Emergency",
            Potion="Increase Spell Power",
        ),
        "blessing_of_protection",
        max_passes=1,
    )

    assert potion_resolver.calls
    assert optimizer.context_factory.combat_states
    assert all(
        state.has_buff("Major Sorcery")
        for state in optimizer.context_factory.combat_states
    )
    assert any(
        "saved-potion use window at 20.000000 seconds" in item
        for item in result.search_scope
    )


def test_conditional_optimizer_respects_potion_buff_expiration_with_medicinal_use(monkeypatch):
    _install_progression_adapter(
        monkeypatch, passive_ranks={"Medicinal Use": 3}
    )
    optimizer = _Optimizer()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        potion_elapsed_seconds=52.0,
        potion_use_resolver=_PotionUseResolver(duration=40.0),
        optimizer=optimizer,
        healing_events=_ConditionalHealingEvents(),
    )

    service.optimize(
        PlayerBuild(BuildName="Expired Potion", Potion="Increase Spell Power"),
        "blessing_of_protection",
        max_passes=1,
    )

    assert optimizer.context_factory.combat_states
    assert all(
        not state.has_buff("Major Sorcery")
        for state in optimizer.context_factory.combat_states
    )


def test_conditional_optimizer_blocks_potion_window_without_medicinal_use_proof(monkeypatch):
    _install_progression_adapter(monkeypatch)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        potion_elapsed_seconds=0.0,
        potion_use_resolver=_PotionUseResolver(),
        optimizer=_Optimizer(),
        healing_events=_ConditionalHealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Unproven Potion", Potion="Increase Spell Power"),
        "blessing_of_protection",
        max_passes=1,
    )

    assert "Medicinal Use rank is unresolved for explicit potion-use window" in result.unresolved
    assert not result.mechanic_complete


def test_conditional_optimizer_rejects_negative_potion_elapsed_time():
    with pytest.raises(ValueError, match="potion_elapsed_seconds cannot be negative"):
        ExtremeConditionalActualHealOptimizationService(
            target_health_fraction=0.29,
            potion_elapsed_seconds=-0.01,
            optimizer=_Optimizer(),
            healing_events=_ConditionalHealingEvents(),
        )
