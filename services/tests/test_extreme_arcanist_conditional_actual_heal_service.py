from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from minmax.derived_stats import DerivedStatTrace
from minmax.stat_ids import StatId
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


class _Fortune:
    def __init__(self, *, bonus=0.12, unresolved=()):
        self.bonus = float(bonus)
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, progression, fated_fortune_active):
        self.calls.append((build.BuildName, progression, fated_fortune_active))
        return SimpleNamespace(
            critical_healing_bonus=self.bonus,
            duration_seconds=7.0 if self.bonus else 0.0,
            unresolved=self.unresolved,
        )


@dataclass(frozen=True)
class _CoreState:
    derived: dict


@dataclass(frozen=True)
class _Context:
    core_state: _CoreState | None


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


def _service(channel=None, **kwargs):
    return ExtremeArcanistConditionalActualHealService(
        target_health_fraction=0.25,
        arcanist_curative_surge_channel=channel,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        **kwargs,
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


def test_active_fated_fortune_adds_twelve_percent_to_canonical_critical_healing():
    fortune = _Fortune(bonus=0.12)
    service = _service(
        _Channel(applies=False, unresolved=()),
        fated_fortune_active=True,
        arcanist_fated_fortune_critical_healing=fortune,
    )
    trace = DerivedStatTrace(
        stat=StatId.CRITICAL_HEALING,
        steps=[("base", "set", 0.0, 0.0), ("existing", "add", 0.20, 0.20)],
        raw_value=0.20,
        final_value=0.20,
    )
    context = _Context(core_state=_CoreState(derived={StatId.CRITICAL_HEALING: trace}))
    progression = object()

    updated, unresolved = service._fated_fortune_context(
        build=PlayerBuild(BuildName="Fated Arc", EsoClass="Arcanist"),
        progression=progression,
        context=context,
    )

    updated_trace = updated.core_state.derived[StatId.CRITICAL_HEALING]
    assert updated_trace.final_value == pytest.approx(0.32)
    assert updated_trace.raw_value == pytest.approx(0.32)
    assert updated_trace.steps[-1] == (
        "Arcanist: Fated Fortune",
        "add",
        0.12,
        pytest.approx(0.32),
    )
    assert unresolved == ()
    assert fortune.calls == [("Fated Arc", progression, True)]
    assert trace.final_value == pytest.approx(0.20)


def test_inactive_fated_fortune_does_not_change_canonical_critical_healing():
    fortune = _Fortune(bonus=0.0)
    service = _service(
        _Channel(applies=False, unresolved=()),
        fated_fortune_active=False,
        arcanist_fated_fortune_critical_healing=fortune,
    )
    trace = DerivedStatTrace(
        stat=StatId.CRITICAL_HEALING,
        raw_value=0.20,
        final_value=0.20,
    )
    context = _Context(core_state=_CoreState(derived={StatId.CRITICAL_HEALING: trace}))

    updated, unresolved = service._fated_fortune_context(
        build=PlayerBuild(BuildName="Inactive Arc", EsoClass="Arcanist"),
        progression=object(),
        context=context,
    )

    assert updated is context
    assert unresolved == ()


def test_crux_consuming_heal_does_not_self_award_inactive_fated_fortune():
    service = _service(
        _Channel(applies=False, unresolved=()),
        fated_fortune_active=False,
        active_crux=2,
    )

    result = service._fated_fortune_same_event_boundary(
        _event(skill_name="Cascading Fortune")
    )

    assert result.normal_heal == 1000.0
    assert result.critical_heal == 1700.0
    assert any("Fated Fortune same-event timing is unresolved" in message for message in result.unresolved)
    assert not result.mechanic_complete


def test_already_active_fated_fortune_needs_no_same_event_blocker():
    service = _service(
        _Channel(applies=False, unresolved=()),
        fated_fortune_active=True,
        active_crux=2,
    )
    event = _event(skill_name="Cascading Fortune")

    result = service._fated_fortune_same_event_boundary(event)

    assert result is event
