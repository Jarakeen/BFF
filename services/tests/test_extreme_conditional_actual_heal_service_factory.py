from __future__ import annotations

from models.build_model import PlayerBuild
from services.extreme_canonical_healing_done_conditional_actual_heal_service import (
    ExtremeCanonicalHealingDoneConditionalActualHealService,
)
from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
)
from services.extreme_conditional_actual_heal_service_factory import (
    ExtremeConditionalActualHealServiceFactory,
)
from services.extreme_nightblade_conditional_actual_heal_service import (
    ExtremeNightbladeConditionalActualHealService,
)
from services.extreme_templar_conditional_actual_heal_service import (
    ExtremeTemplarConditionalActualHealService,
)


def test_nightblade_routes_to_mastery_aware_conditional_service():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="NB", EsoClass="Nightblade"),
        target_health_fraction=0.25,
    )

    assert isinstance(service, ExtremeNightbladeConditionalActualHealService)
    assert isinstance(service, ExtremeCanonicalHealingDoneConditionalActualHealService)
    assert service.target_health_fraction == 0.25


def test_nightblade_routing_is_case_and_whitespace_tolerant():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="NB", EsoClass="  NIGHTBLADE  "),
        target_health_fraction=0.5,
    )

    assert isinstance(service, ExtremeNightbladeConditionalActualHealService)


def test_pure_templar_routes_to_illuminate_aware_conditional_service():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="Templar", EsoClass="Templar"),
        target_health_fraction=0.25,
        illuminate_window_active=True,
    )

    assert isinstance(service, ExtremeTemplarConditionalActualHealService)
    assert isinstance(service, ExtremeCanonicalHealingDoneConditionalActualHealService)
    assert service.illuminate_window_active


def test_foreign_dawns_wrath_route_uses_templar_conditional_service():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(
            BuildName="Subclassed Warden",
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Dawn's Wrath"],
        ),
        target_health_fraction=0.25,
        illuminate_window_active=True,
    )

    assert isinstance(service, ExtremeTemplarConditionalActualHealService)


def test_subclassed_nightblade_with_dawns_wrath_does_not_use_class_mastery_route():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(
            BuildName="Subclassed NB",
            EsoClass="Nightblade",
            ClassSkillLines=["Siphoning", "Assassination", "Dawn's Wrath"],
        ),
        target_health_fraction=0.25,
        illuminate_window_active=True,
    )

    assert isinstance(service, ExtremeTemplarConditionalActualHealService)
    assert not isinstance(service, ExtremeNightbladeConditionalActualHealService)


def test_templar_with_explicit_route_that_removed_dawns_wrath_uses_canonical_service():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(
            BuildName="Templar Subclass",
            EsoClass="Templar",
            ClassSkillLines=["Aedric Spear", "Restoring Light", "Green Balance"],
        ),
        target_health_fraction=0.25,
    )

    assert type(service) is ExtremeCanonicalHealingDoneConditionalActualHealService


def test_other_classes_use_canonical_healing_done_conditional_service():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="Warden", EsoClass="Warden"),
        target_health_fraction=0.25,
    )

    assert type(service) is ExtremeCanonicalHealingDoneConditionalActualHealService


def test_missing_class_uses_canonical_healing_done_conditional_service():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="Unknown"),
        target_health_fraction=0.25,
    )

    assert type(service) is ExtremeCanonicalHealingDoneConditionalActualHealService


def test_factory_uses_canonical_healing_event_service_by_default():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="Warden", EsoClass="Warden"),
        target_health_fraction=0.25,
    )

    assert isinstance(service.healing_events, ExtremeCanonicalHealingEventService)


def test_factory_preserves_caller_supplied_healing_event_service():
    supplied = object()
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="Warden", EsoClass="Warden"),
        target_health_fraction=0.25,
        healing_events=supplied,
    )

    assert service.healing_events is supplied


def test_inactive_illuminate_kwarg_is_ignored_for_unrelated_class():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="Warden", EsoClass="Warden"),
        target_health_fraction=0.25,
        illuminate_window_active=False,
    )

    assert type(service) is ExtremeCanonicalHealingDoneConditionalActualHealService


def test_explicit_illegal_illuminate_request_routes_to_templar_blocking_service():
    service = ExtremeConditionalActualHealServiceFactory.create(
        PlayerBuild(BuildName="Warden", EsoClass="Warden"),
        target_health_fraction=0.25,
        illuminate_window_active=True,
    )

    assert isinstance(service, ExtremeTemplarConditionalActualHealService)
