from __future__ import annotations

from models.build_model import PlayerBuild
from services.extreme_dragonknight_earthen_heart_mending_service import (
    ExtremeDragonknightEarthenHeartMendingService,
)


def _service():
    return ExtremeDragonknightEarthenHeartMendingService()


def test_fragmented_shield_grants_six_second_major_mending_window():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="dragonknight"),
        source_ability_name="Fragmented Shield",
        major_mending_window_active=True,
    )

    assert result.major_mending_active
    assert result.combat_state.has_buff("Major Mending")
    assert result.reviewed_duration_seconds == 6.0
    assert result.unresolved == ()


def test_igneous_shield_grants_four_second_major_mending_window():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="dragonknight"),
        source_ability_name="Igneous Shield",
        major_mending_window_active=True,
    )

    assert result.major_mending_active
    assert result.reviewed_duration_seconds == 4.0
    assert result.unresolved == ()


def test_inactive_window_does_not_invent_major_mending():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="dragonknight"),
        source_ability_name="Fragmented Shield",
        major_mending_window_active=False,
    )

    assert not result.major_mending_active
    assert not result.combat_state.has_buff("Major Mending")
    assert result.unresolved == ()


def test_explicit_subclass_route_can_remove_native_earthen_heart_legality():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="dragonknight",
            ClassSkillLines=["ardent_flame", "draconic_power", "green_balance"],
        ),
        source_ability_name="Fragmented Shield",
        major_mending_window_active=True,
    )

    assert not result.major_mending_active
    assert "Earthen Heart" in result.unresolved[0]


def test_foreign_class_can_use_reviewed_source_with_explicit_earthen_heart_route():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="warden",
            ClassSkillLines=["green_balance", "earthen_heart", "siphoning"],
        ),
        source_ability_name="Obsidian Shield",
        major_mending_window_active=True,
    )

    assert result.major_mending_active
    assert result.combat_state.has_buff("Major Mending")
    assert result.reviewed_duration_seconds == 4.0
    assert result.unresolved == ()


def test_unknown_earthen_heart_source_preserves_unbuffed_state_and_blocker():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="dragonknight"),
        source_ability_name="Mystery Shield",
        major_mending_window_active=True,
    )

    assert not result.major_mending_active
    assert not result.combat_state.has_buff("Major Mending")
    assert "reviewed Obsidian Shield-family source" in result.unresolved[0]
