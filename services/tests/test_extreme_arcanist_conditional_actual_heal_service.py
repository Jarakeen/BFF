from __future__ import annotations

from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_arcanist_conditional_actual_heal_service import (
    ExtremeArcanistConditionalActualHealService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult


class _Optimizer:
    database_path = None

    def __init__(self):
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=object())
        )
        self.context_factory = SimpleNamespace()


class _HealingEvents:
    pass


class _Channel:
    def __init__(self, *, applies=True, unresolved=("tick timing unresolved",)):
        self.applies = applies
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, ability_name):
        self.calls.append((build.BuildName, ability_name))
        return SimpleNamespace(
            applies=self.applies,
            unresolved=self.unresolved,
        )


def _event(skill_name="Curative Surge", unresolved=()):
    return ExtremeHealingEventResult(
        entity_id="curative_surge",
        normal_heal=1000.0,
        critical_heal=1700.0,
        critical_healing_bonus=0.20,
        critical_multiplier=1.70,
        heal_coefficient_numbers=(1,),
        crit_eligible_coefficient_numbers=(1,),
        noncrit_coefficient_numbers=(),
        tooltip_result=SimpleNamespace(skill=SimpleNamespace(name=skill_name)),
        unresolved=tuple(unresolved),
    )


def _service(channel):
    return ExtremeArcanistConditionalActualHealService(
        target_health_fraction=0.25,
        arcanist_curative_surge_channel=channel,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )


def test_curative_surge_keeps_numeric_lower_bound_and_adds_channel_blocker():
    channel = _Channel()
    service = _service(channel)
    event = _event()

    result = service._curative_surge_channel_event(
        build=PlayerBuild(BuildName="Arc Beam", EsoClass="Arcanist"),
        event=event,
    )

    assert result.normal_heal == 1000.0
    assert result.critical_heal == 1700.0
    assert result.unresolved == ("tick timing unresolved",)
    assert not result.mechanic_complete
    assert channel.calls == [("Arc Beam", "Curative Surge")]


def test_non_curative_surge_event_is_unchanged():
    channel = _Channel(applies=False, unresolved=())
    service = _service(channel)
    event = _event(skill_name="Combat Prayer")

    result = service._curative_surge_channel_event(
        build=PlayerBuild(BuildName="Other Heal", EsoClass="Arcanist"),
        event=event,
    )

    assert result is event
    assert channel.calls == [("Other Heal", "Combat Prayer")]


def test_existing_blockers_are_preserved_with_channel_blocker():
    channel = _Channel(unresolved=("channel blocker",))
    service = _service(channel)

    result = service._curative_surge_channel_event(
        build=PlayerBuild(BuildName="Blocked Beam", EsoClass="Arcanist"),
        event=_event(unresolved=("existing blocker",)),
    )

    assert result.unresolved == ("existing blocker", "channel blocker")
