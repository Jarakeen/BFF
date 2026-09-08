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
    def __init__(self, multiplier=1.12):
        self.multiplier = multiplier
        self.calls = []

    def resolve(self, *, build, progression, active_crux):
        self.calls.append((build.BuildName, progression, active_crux))
        return SimpleNamespace(multiplier=self.multiplier, unresolved=())


def _event(skill_name: str):
    return ExtremeHealingEventResult(
        entity_id="cascading_fortune",
        normal_heal=1000.0,
        critical_heal=1700.0,
        critical_healing_bonus=0.20,
        critical_multiplier=1.70,
        heal_coefficient_numbers=(1,),
        crit_eligible_coefficient_numbers=(1,),
        noncrit_coefficient_numbers=(),
        tooltip_result=SimpleNamespace(skill=SimpleNamespace(name=skill_name)),
        unresolved=(),
    )


def test_crux_consuming_cascading_fortune_does_not_claim_unproven_healing_tides():
    tides = _HealingTides(multiplier=1.12)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        active_crux=3,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        arcanist_curative_runeforms_healing=tides,
    )
    progression = CharacterProgression(passive_ranks={"Healing Tides": 2})
    build = PlayerBuild(BuildName="Three Crux Fortune", EsoClass="arcanist")

    blocked = service._arcanist_healing_tides_event(
        build=build,
        progression=progression,
        event=_event("Cascading Fortune"),
    )
    result = service._arcanist_cascading_fortune_event(
        build=build,
        event=blocked,
    )

    assert tides.calls == []
    assert result.normal_heal == pytest.approx(1375.0)
    assert result.critical_heal == pytest.approx(2337.5)
    assert any("Healing Tides timing is unresolved" in message for message in result.unresolved)
    assert not result.mechanic_complete


def test_non_consuming_heal_still_receives_healing_tides_with_active_crux():
    tides = _HealingTides(multiplier=1.12)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        active_crux=3,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        arcanist_curative_runeforms_healing=tides,
    )
    progression = CharacterProgression(passive_ranks={"Healing Tides": 2})

    result = service._arcanist_healing_tides_event(
        build=PlayerBuild(BuildName="Three Crux Prayer", EsoClass="arcanist"),
        progression=progression,
        event=_event("Combat Prayer"),
    )

    assert result.normal_heal == pytest.approx(1120.0)
    assert result.critical_heal == pytest.approx(1904.0)
    assert result.unresolved == ()
    assert len(tides.calls) == 1


def test_zero_crux_cascading_fortune_has_no_consume_timing_blocker():
    tides = _HealingTides(multiplier=1.0)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        active_crux=0,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        arcanist_curative_runeforms_healing=tides,
    )
    progression = CharacterProgression(passive_ranks={"Healing Tides": 2})

    result = service._arcanist_healing_tides_event(
        build=PlayerBuild(BuildName="Zero Crux Fortune", EsoClass="arcanist"),
        progression=progression,
        event=_event("Cascading Fortune"),
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.unresolved == ()
    assert len(tides.calls) == 1
