from __future__ import annotations

from models.build_model import PlayerBuild
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_conditional_actual_heal_service_factory import (
    ExtremeConditionalActualHealServiceFactory,
)
from services.extreme_nightblade_conditional_actual_heal_service import (
    ExtremeNightbladeConditionalActualHealService,
)


def test_nightblade_routes_to_mastery_aware_conditional_service():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="NB", EsoClass="Nightblade"),
        target_health_fraction=0.25,
    )

    assert isinstance(service, ExtremeNightbladeConditionalActualHealService)
    assert service.target_health_fraction == 0.25


def test_nightblade_routing_is_case_and_whitespace_tolerant():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="NB", EsoClass="  NIGHTBLADE  "),
        target_health_fraction=0.5,
    )

    assert isinstance(service, ExtremeNightbladeConditionalActualHealService)


def test_other_classes_keep_generic_conditional_service():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="Warden", EsoClass="Warden"),
        target_health_fraction=0.25,
    )

    assert type(service) is ExtremeConditionalActualHealOptimizationService


def test_missing_class_keeps_generic_conditional_service():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="Unknown"),
        target_health_fraction=0.25,
    )

    assert type(service) is ExtremeConditionalActualHealOptimizationService
