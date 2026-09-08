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


class _Mending:
    def __init__(self, multiplier=1.09, unresolved=()):
        self.multiplier = multiplier
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(
        self,
        *,
        build,
        progression,
        ability_name,
        target_health_fraction,
    ):
        self.calls.append(
            (build.BuildName, progression, ability_name, target_health_fraction)
        )
        return SimpleNamespace(
            multiplier=self.multiplier,
            unresolved=self.unresolved,
        )


def _event(name="Breath of Life"):
    return ExtremeHealingEventResult(
        entity_id="breath_of_life",
        normal_heal=1000.0,
        critical_heal=1700.0,
        critical_healing_bonus=0.20,
        critical_multiplier=1.70,
        heal_coefficient_numbers=(1,),
        crit_eligible_coefficient_numbers=(1,),
        noncrit_coefficient_numbers=(),
        tooltip_result=SimpleNamespace(skill=SimpleNamespace(name=name)),
        unresolved=(),
    )


def test_conditional_event_applies_mending_after_base_actual_heal_event():
    mending = _Mending(multiplier=1.09)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        templar_restoring_light_healing=mending,
    )
    progression = CharacterProgression(passive_ranks={"Mending": 2})

    result = service._templar_mending_event(
        build=PlayerBuild(BuildName="Emergency Templar", EsoClass="templar"),
        progression=progression,
        event=_event(),
    )

    assert result.normal_heal == pytest.approx(1090.0)
    assert result.critical_heal == pytest.approx(1853.0)
    assert result.unresolved == ()
    assert mending.calls == [
        ("Emergency Templar", progression, "Breath of Life", 0.25)
    ]


def test_conditional_event_preserves_mending_blocker_with_numeric_lower_bound():
    mending = _Mending(
        multiplier=1.0,
        unresolved=("Mending passive rank is not recorded",),
    )
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        templar_restoring_light_healing=mending,
    )

    result = service._templar_mending_event(
        build=PlayerBuild(BuildName="Unknown Mending", EsoClass="templar"),
        progression=CharacterProgression(passive_ranks=None),
        event=_event(),
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert result.unresolved == ("Mending passive rank is not recorded",)
    assert not result.mechanic_complete


def test_conditional_event_without_skill_identity_leaves_base_event_unchanged():
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        templar_restoring_light_healing=_Mending(),
    )
    event = ExtremeHealingEventResult(
        entity_id="unknown_heal",
        normal_heal=1000.0,
        critical_heal=1700.0,
        critical_healing_bonus=0.20,
        critical_multiplier=1.70,
        heal_coefficient_numbers=(1,),
        crit_eligible_coefficient_numbers=(1,),
        noncrit_coefficient_numbers=(),
        tooltip_result=SimpleNamespace(skill=None),
        unresolved=(),
    )

    result = service._templar_mending_event(
        build=PlayerBuild(BuildName="Unknown Skill"),
        progression=CharacterProgression(passive_ranks={}),
        event=event,
    )

    assert result is event
