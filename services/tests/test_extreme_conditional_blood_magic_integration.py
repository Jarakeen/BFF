from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


@dataclass(frozen=True)
class _Event:
    normal_heal: float
    critical_heal: float
    unresolved: tuple[str, ...] = ()
    tooltip_result: object = SimpleNamespace(skill=None)


class _HealingEvents:
    def evaluate(self, *, build, context, entity_id, target_health_fraction=None):
        _ = build, entity_id, target_health_fraction
        value = float(context.character_state.max_magicka)
        return _Event(normal_heal=value, critical_heal=value * 1.5)


class _ContextFactory:
    def __init__(self):
        self.combat_states: list[CombatState] = []

    def build(self, **kwargs):
        combat_state = kwargs.get("combat_state", CombatState())
        self.combat_states.append(combat_state)
        max_magicka = 11000 if combat_state.has_buff("Blood Magic: Max Magicka") else 10000
        return SimpleNamespace(
            combat_state=combat_state,
            character_state=SimpleNamespace(
                max_health=16000,
                max_magicka=max_magicka,
                max_stamina=9000,
            ),
            unresolved_gear_effects=(),
        )


class _Optimizer:
    database_path = None

    def __init__(self):
        self.context_factory = _ContextFactory()
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=object())
        )


class _BloodMagic:
    def __init__(self, *, branch="resource_window", resource_stat="max_magicka"):
        self.branch = branch
        self.resource_stat = resource_stat
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        if self.branch == "self_heal":
            return SimpleNamespace(
                branch="self_heal",
                self_heal=1600.0,
                resource_stat=None,
                resource_percent=0.0,
                duration_seconds=None,
                unresolved=(),
            )
        return SimpleNamespace(
            branch="resource_window",
            self_heal=None,
            resource_stat=self.resource_stat,
            resource_percent=0.10,
            duration_seconds=10.0,
            unresolved=(),
        )


def _snapshot(snapshot_time: float) -> ExtremeRuntimeSnapshot:
    return ExtremeRuntimeSnapshot(
        attempts=(
            RuntimeEffectEventAttempt(
                event=RuntimeEvent(
                    time_seconds=1.0,
                    trigger="cast",
                    source="Dark Exchange",
                )
            ),
        ),
        snapshot_time_seconds=snapshot_time,
    )


def _evaluate(service: ExtremeConditionalActualHealOptimizationService):
    return service._evaluate(
        PlayerBuild(BuildName="Blood Magic Integration", EsoClass="Sorcerer"),
        progression=CharacterProgression(passive_ranks={"Blood Magic": 2}),
        character_id="char-1",
        build_id="build-1",
        entity_id="test_heal",
        active_bar="front",
    )


def test_full_health_blood_magic_rebuilds_context_with_higher_magicka_window():
    optimizer = _Optimizer()
    blood_magic = _BloodMagic()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.50,
        runtime_snapshot=_snapshot(5.0),
        blood_magic_caster_health_fraction=1.0,
        blood_magic_trigger_ability_has_cost=True,
        sorcerer_blood_magic=blood_magic,
        optimizer=optimizer,
        healing_events=_HealingEvents(),
    )

    event, unresolved = _evaluate(service)

    assert unresolved == ()
    assert len(optimizer.context_factory.combat_states) == 2
    assert not optimizer.context_factory.combat_states[0].has_buff(
        "Blood Magic: Max Magicka"
    )
    assert optimizer.context_factory.combat_states[1].has_buff(
        "Blood Magic: Max Magicka"
    )
    assert event.normal_heal == 11000
    assert event.critical_heal == 16500
    assert blood_magic.calls[0]["context"].character_state.max_magicka == 10000


def test_blood_magic_resource_window_expires_at_ten_seconds():
    optimizer = _Optimizer()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.50,
        runtime_snapshot=_snapshot(11.0),
        blood_magic_caster_health_fraction=1.0,
        blood_magic_trigger_ability_has_cost=True,
        sorcerer_blood_magic=_BloodMagic(),
        optimizer=optimizer,
        healing_events=_HealingEvents(),
    )

    event, unresolved = _evaluate(service)

    assert unresolved == ()
    assert len(optimizer.context_factory.combat_states) == 1
    assert event.normal_heal == 10000


def test_blood_magic_self_heal_stays_separate_from_selected_target_heal():
    optimizer = _Optimizer()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.50,
        runtime_snapshot=_snapshot(5.0),
        blood_magic_caster_health_fraction=0.50,
        blood_magic_trigger_ability_has_cost=True,
        sorcerer_blood_magic=_BloodMagic(branch="self_heal", resource_stat=None),
        optimizer=optimizer,
        healing_events=_HealingEvents(),
    )

    event, unresolved = _evaluate(service)

    assert len(optimizer.context_factory.combat_states) == 1
    assert event.normal_heal == 10000
    assert any("Max-Health-scaled self-heal" in message for message in unresolved)
    assert any("separate caster event" in message for message in unresolved)
