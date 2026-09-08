from __future__ import annotations

import pytest

from models.build_model import PlayerBuild
from services.extreme_dragonknight_dragon_blood_healing_service import (
    ExtremeDragonknightDragonBloodHealingService,
)


def test_green_dragon_blood_scales_linearly_with_missing_health():
    service = ExtremeDragonknightDragonBloodHealingService()
    build = PlayerBuild(EsoClass="Dragonknight")

    full = service.resolve(
        build=build,
        ability_name="Blood of the Green Dragon",
        caster_health_fraction=1.0,
    )
    half = service.resolve(
        build=build,
        ability_name="Blood of the Green Dragon",
        caster_health_fraction=0.5,
    )
    quarter = service.resolve(
        build=build,
        ability_name="Blood of the Green Dragon",
        caster_health_fraction=0.25,
    )
    empty = service.resolve(
        build=build,
        ability_name="Blood of the Green Dragon",
        caster_health_fraction=0.0,
    )

    assert full.multiplier == pytest.approx(1.0)
    assert half.multiplier == pytest.approx(1.25)
    assert quarter.multiplier == pytest.approx(1.375)
    assert empty.multiplier == pytest.approx(1.50)


def test_base_dragon_blood_uses_same_reviewed_missing_health_rule():
    result = ExtremeDragonknightDragonBloodHealingService().resolve(
        build=PlayerBuild(EsoClass="Dragonknight"),
        ability_name="Dragon Blood",
        caster_health_fraction=0.4,
    )

    assert result.multiplier == pytest.approx(1.30)
    assert result.unresolved == ()


def test_elder_dragon_and_legacy_coagulating_blood_are_not_aggregated_here():
    service = ExtremeDragonknightDragonBloodHealingService()
    build = PlayerBuild(EsoClass="Dragonknight")

    elder = service.resolve(
        build=build,
        ability_name="Blood of the Elder Dragon",
        caster_health_fraction=0.2,
    )
    legacy = service.resolve(
        build=build,
        ability_name="Coagulating Blood",
        caster_health_fraction=0.2,
    )

    assert elder.multiplier == pytest.approx(1.0)
    assert legacy.multiplier == pytest.approx(1.0)


def test_explicit_route_can_remove_native_draconic_power():
    result = ExtremeDragonknightDragonBloodHealingService().resolve(
        build=PlayerBuild(
            EsoClass="Dragonknight",
            ClassSkillLines=["Ardent Flame", "Earthen Heart", "Green Balance"],
        ),
        ability_name="Blood of the Green Dragon",
        caster_health_fraction=0.0,
    )

    assert result.multiplier == pytest.approx(1.0)
    assert result.unresolved == ()


def test_foreign_class_can_use_explicit_draconic_power_route():
    result = ExtremeDragonknightDragonBloodHealingService().resolve(
        build=PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Restoring Light", "Draconic Power", "Green Balance"],
        ),
        ability_name="Blood of the Green Dragon",
        caster_health_fraction=0.5,
    )

    assert result.multiplier == pytest.approx(1.25)


def test_missing_caster_health_preserves_lower_bound_and_blocker():
    result = ExtremeDragonknightDragonBloodHealingService().resolve(
        build=PlayerBuild(EsoClass="Dragonknight"),
        ability_name="Blood of the Green Dragon",
        caster_health_fraction=None,
    )

    assert result.multiplier == pytest.approx(1.0)
    assert result.unresolved == (
        "Dragon Blood missing-health scaling requires explicit caster Health fraction",
    )


def test_caster_health_fraction_must_be_normalized():
    with pytest.raises(ValueError, match="caster_health_fraction"):
        ExtremeDragonknightDragonBloodHealingService().resolve(
            build=PlayerBuild(EsoClass="Dragonknight"),
            ability_name="Blood of the Green Dragon",
            caster_health_fraction=1.01,
        )
