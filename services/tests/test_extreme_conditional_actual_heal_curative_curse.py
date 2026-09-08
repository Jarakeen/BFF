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


class _CurativeCurse:
    def __init__(self, multiplier=1.12, unresolved=()):
        self.multiplier = multiplier
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, progression, has_negative_effect):
        self.calls.append((build.BuildName, progression, has_negative_effect))
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


def test_negative_effect_scenario_applies_curative_curse_to_generic_heal():
    curse = _CurativeCurse(multiplier=1.12)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.80,
        healer_has_negative_effect=True,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        necromancer_living_death_healing=curse,
    )
    progression = CharacterProgression(passive_ranks={"Curative Curse": 2})

    result = service._necromancer_curative_curse_event(
        build=PlayerBuild(BuildName="Cursed Necro", EsoClass="necromancer"),
        progression=progression,
        event=_event(),
    )

    assert result.normal_heal == pytest.approx(1120.0)
    assert result.critical_heal == pytest.approx(1904.0)
    assert result.unresolved == ()
    assert curse.calls == [("Cursed Necro", progression, True)]


def test_explicit_no_negative_effect_preserves_base_heal():
    curse = _CurativeCurse(multiplier=1.0)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.20,
        healer_has_negative_effect=False,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        necromancer_living_death_healing=curse,
    )
    progression = CharacterProgression(passive_ranks={"Curative Curse": 2})

    result = service._necromancer_curative_curse_event(
        build=PlayerBuild(BuildName="Clean Necro", EsoClass="necromancer"),
        progression=progression,
        event=_event(),
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert curse.calls == [("Clean Necro", progression, False)]


def test_unspecified_negative_effect_scenario_does_not_invent_curative_curse():
    curse = _CurativeCurse(multiplier=1.12)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.20,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        necromancer_living_death_healing=curse,
    )
    event = _event()

    result = service._necromancer_curative_curse_event(
        build=PlayerBuild(BuildName="Unspecified Necro", EsoClass="necromancer"),
        progression=CharacterProgression(passive_ranks={"Curative Curse": 2}),
        event=event,
    )

    assert result is event
    assert curse.calls == []


def test_curative_curse_preserves_blocker_with_numeric_lower_bound():
    curse = _CurativeCurse(
        multiplier=1.0,
        unresolved=("Curative Curse passive rank is not recorded",),
    )
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.20,
        healer_has_negative_effect=True,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        necromancer_living_death_healing=curse,
    )

    result = service._necromancer_curative_curse_event(
        build=PlayerBuild(BuildName="Unknown Curse", EsoClass="necromancer"),
        progression=CharacterProgression(passive_ranks=None),
        event=_event(),
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert result.unresolved == ("Curative Curse passive rank is not recorded",)
    assert not result.mechanic_complete
