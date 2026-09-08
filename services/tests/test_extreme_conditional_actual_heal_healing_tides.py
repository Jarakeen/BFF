from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
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


class _HealingTides:
    def __init__(self, multiplier=1.12, unresolved=()):
        self.multiplier = multiplier
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, progression, active_crux):
        self.calls.append((build.BuildName, progression, active_crux))
        return SimpleNamespace(
            multiplier=self.multiplier,
            unresolved=self.unresolved,
        )


def _event():
    return ExtremeHealingEventResult(
        entity_id="combat_prayer",
        normal_heal=1000.0,
        critical_heal=1700.0,
        critical_healing_bonus=0.20,
        critical_multiplier=1.70,
        heal_coefficient_numbers=(1,),
        crit_eligible_coefficient_numbers=(1,),
        noncrit_coefficient_numbers=(),
        tooltip_result=SimpleNamespace(skill=SimpleNamespace(name="Combat Prayer")),
        unresolved=(),
    )


def test_three_crux_scenario_applies_healing_tides_to_generic_heal():
    tides = _HealingTides(multiplier=1.12)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.80,
        active_crux=3,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        arcanist_curative_runeforms_healing=tides,
    )
    progression = CharacterProgression(passive_ranks={"Healing Tides": 2})

    result = service._arcanist_healing_tides_event(
        build=PlayerBuild(BuildName="Three Crux Arc", EsoClass="arcanist"),
        progression=progression,
        event=_event(),
    )

    assert result.normal_heal == pytest.approx(1120.0)
    assert result.critical_heal == pytest.approx(1904.0)
    assert result.unresolved == ()
    assert tides.calls == [("Three Crux Arc", progression, 3)]


def test_zero_crux_scenario_preserves_base_heal_but_remains_explicit():
    tides = _HealingTides(multiplier=1.0)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.20,
        active_crux=0,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        arcanist_curative_runeforms_healing=tides,
    )
    progression = CharacterProgression(passive_ranks={"Healing Tides": 2})

    result = service._arcanist_healing_tides_event(
        build=PlayerBuild(BuildName="Zero Crux Arc", EsoClass="arcanist"),
        progression=progression,
        event=_event(),
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert tides.calls == [("Zero Crux Arc", progression, 0)]


def test_unspecified_crux_scenario_does_not_invent_healing_tides():
    tides = _HealingTides(multiplier=1.12)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.20,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        arcanist_curative_runeforms_healing=tides,
    )
    event = _event()

    result = service._arcanist_healing_tides_event(
        build=PlayerBuild(BuildName="Unspecified Arc", EsoClass="arcanist"),
        progression=CharacterProgression(passive_ranks={"Healing Tides": 2}),
        event=event,
    )

    assert result is event
    assert tides.calls == []


def test_healing_tides_preserves_blocker_with_numeric_lower_bound():
    tides = _HealingTides(
        multiplier=1.0,
        unresolved=("Healing Tides passive rank is not recorded",),
    )
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.20,
        active_crux=3,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        arcanist_curative_runeforms_healing=tides,
    )

    result = service._arcanist_healing_tides_event(
        build=PlayerBuild(BuildName="Unknown Tides", EsoClass="arcanist"),
        progression=CharacterProgression(passive_ranks=None),
        event=_event(),
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert result.unresolved == ("Healing Tides passive rank is not recorded",)
    assert not result.mechanic_complete


def test_conditional_optimizer_rejects_impossible_crux_state():
    with pytest.raises(ValueError, match="0 through 3"):
        ExtremeConditionalActualHealOptimizationService(
            target_health_fraction=0.20,
            active_crux=4,
            optimizer=_Optimizer(),
            healing_events=_HealingEvents(),
        )
