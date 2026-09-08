from __future__ import annotations

from types import SimpleNamespace

from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_progression import CharacterProgression
from minmax.core_stat_calculator import CoreStatState
from minmax.derived_stats import DerivedStatCalculator, DerivedStatInputs, StatContribution
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_healing_event_service import ExtremeHealingEventResult
from services.extreme_nightblade_conditional_actual_heal_service import (
    ExtremeNightbladeConditionalActualHealService,
)
from services.extreme_nightblade_eye_for_exploitation_context_service import (
    ExtremeNightbladeEyeForExploitationContextService,
)


class _ContextFactory:
    def __init__(self, context):
        self.context = context

    def build(self, **_kwargs):
        return self.context


class _HealingEvents:
    def __init__(self, event):
        self.event = event
        self.context = None

    def evaluate(self, *, context, **_kwargs):
        self.context = context
        return self.event


class _Mastery:
    def __init__(self, *, power=1500.0, unresolved=()):
        self.power = float(power)
        self.unresolved = tuple(unresolved)

    def resolve(self, *, build, target_health_fraction, battle_spirit_active):
        _ = build, target_health_fraction, battle_spirit_active
        return SimpleNamespace(
            selected_masteries=("Above and Beyond", "An Eye for Exploitation"),
            critical_healing_bonus=0.25,
            critical_healing_cap=1.55,
            weapon_spell_damage_bonus=self.power,
            unresolved=self.unresolved,
        )


def _context():
    inputs = DerivedStatInputs(
        flat=(StatContribution("existing flat", 200.0),),
        percent=(StatContribution("existing percent", 0.10),),
    )
    calculator = DerivedStatCalculator()
    base = SimpleNamespace()
    return BuildCalculationContext(
        character_id="char",
        build_id="build",
        progression=CharacterProgression(),
        character_state=base,
        core_state=CoreStatState(
            base_character=base,
            derived={
                StatId.WEAPON_DAMAGE: calculator.weapon_damage(inputs),
                StatId.SPELL_DAMAGE: calculator.spell_damage(inputs),
            },
        ),
    )


def _event(*, unresolved=()):
    return ExtremeHealingEventResult(
        entity_id="heal",
        normal_heal=1000.0,
        critical_heal=2550.0,
        critical_healing_bonus=1.05,
        critical_multiplier=2.55,
        heal_coefficient_numbers=(1,),
        crit_eligible_coefficient_numbers=(1,),
        noncrit_coefficient_numbers=(),
        tooltip_result=SimpleNamespace(skill=None),
        unresolved=tuple(unresolved),
    )


def _service(*, mastery, event):
    context = _context()
    healing_events = _HealingEvents(event)
    optimizer = SimpleNamespace(
        database_path=None,
        context_factory=_ContextFactory(context),
    )
    service = ExtremeNightbladeConditionalActualHealService(
        target_health_fraction=0.25,
        optimizer=optimizer,
        healing_events=healing_events,
        nightblade_class_mastery_healing=mastery,
    )
    return service, healing_events


def _build():
    return PlayerBuild(
        BuildName="Pure Nightblade",
        EsoClass="Nightblade",
        AttributeHealth=0,
        AttributeMagicka=64,
        AttributeStamina=0,
    )


def test_eye_power_rebuild_happens_before_heal_event_and_clears_pending_blocker():
    service, healing_events = _service(
        mastery=_Mastery(power=1500.0),
        event=_event(
            unresolved=(ExtremeNightbladeConditionalActualHealService.EYE_PENDING_BLOCKER,)
        ),
    )

    event, unresolved = service._evaluate(
        _build(),
        progression=CharacterProgression(),
        character_id="char",
        build_id="build",
        entity_id="heal",
        active_bar="front",
    )

    weapon = healing_events.context.core_state.derived[StatId.WEAPON_DAMAGE]
    spell = healing_events.context.core_state.derived[StatId.SPELL_DAMAGE]
    assert weapon.raw_value == 2970.0000000000005
    assert weapon.final_value == 2971.0
    assert spell.final_value == 2971.0
    assert any(
        step[0] == ExtremeNightbladeEyeForExploitationContextService.LABEL
        for step in weapon.steps
    )
    assert event.critical_heal == 2550.0
    assert event.unresolved == ()
    assert unresolved == ()


def test_mastery_legality_blocker_survives_context_rebuild():
    service, _ = _service(
        mastery=_Mastery(power=0.0, unresolved=("Class Mastery unavailable",)),
        event=_event(),
    )

    event, unresolved = service._evaluate(
        _build(),
        progression=CharacterProgression(),
        character_id="char",
        build_id="build",
        entity_id="heal",
        active_bar="front",
    )

    assert event.critical_heal == 2550.0
    assert unresolved == ("Class Mastery unavailable",)


def test_pending_eye_blocker_is_not_cleared_when_power_was_not_applied():
    service, _ = _service(
        mastery=_Mastery(power=0.0),
        event=_event(
            unresolved=(ExtremeNightbladeConditionalActualHealService.EYE_PENDING_BLOCKER,)
        ),
    )

    event, unresolved = service._evaluate(
        _build(),
        progression=CharacterProgression(),
        character_id="char",
        build_id="build",
        entity_id="heal",
        active_bar="front",
    )

    assert event.unresolved == (
        ExtremeNightbladeConditionalActualHealService.EYE_PENDING_BLOCKER,
    )
    assert unresolved == event.unresolved
