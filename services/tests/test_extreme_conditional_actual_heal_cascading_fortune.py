from __future__ import annotations

from types import SimpleNamespace

import pytest

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


def test_cascading_fortune_emergency_event_scales_with_target_wounds():
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    result = service._arcanist_cascading_fortune_event(
        build=PlayerBuild(BuildName="Fortune Arc", EsoClass="arcanist"),
        event=_event("Cascading Fortune"),
    )

    assert result.normal_heal == pytest.approx(1375.0)
    assert result.critical_heal == pytest.approx(2337.5)
    assert result.unresolved == ()
    assert result.mechanic_complete


def test_cascading_fortune_modifier_does_not_touch_other_heals():
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.10,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )
    event = _event("Combat Prayer")

    result = service._arcanist_cascading_fortune_event(
        build=PlayerBuild(BuildName="Arc", EsoClass="arcanist"),
        event=event,
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)


def test_cascading_fortune_modifier_respects_explicit_subclass_route_removal():
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    result = service._arcanist_cascading_fortune_event(
        build=PlayerBuild(
            BuildName="No Curative",
            EsoClass="arcanist",
            ClassSkillLines=["herald_of_the_tome", "soldier_of_apocrypha", "green_balance"],
        ),
        event=_event("Cascading Fortune"),
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
