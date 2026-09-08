from __future__ import annotations

import pytest

from models.build_model import PlayerBuild
from services.extreme_arcanist_curative_surge_channel_service import (
    ExtremeArcanistCurativeSurgeChannelService,
)


def _service():
    return ExtremeArcanistCurativeSurgeChannelService()


def test_curative_surge_records_final_tick_ceiling_but_not_whole_channel_multiplier():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="arcanist"),
        ability_name="Curative Surge",
    )

    assert result.applies
    assert result.final_tick_multiplier == pytest.approx(2.92)
    assert result.whole_channel_multiplier is None
    assert "tick-level channel timing" in result.unresolved[0]
    assert "192%" in result.unresolved[0]


def test_curative_surge_does_not_modify_other_curative_runeforms_heals():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="arcanist"),
        ability_name="Cascading Fortune",
    )

    assert not result.applies
    assert result.final_tick_multiplier is None
    assert result.whole_channel_multiplier == 1.0
    assert result.unresolved == ()


def test_explicit_subclass_route_can_remove_native_curative_surge_legality():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="arcanist",
            ClassSkillLines=["herald_of_the_tome", "soldier_of_apocrypha", "green_balance"],
        ),
        ability_name="Curative Surge",
    )

    assert not result.applies
    assert result.whole_channel_multiplier == 1.0
    assert result.unresolved == ()


def test_foreign_class_can_use_curative_surge_when_curative_runeforms_is_explicit():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="warden",
            ClassSkillLines=["green_balance", "curative_runeforms", "siphoning"],
        ),
        ability_name="Curative Surge",
    )

    assert result.applies
    assert result.final_tick_multiplier == pytest.approx(2.92)
    assert result.whole_channel_multiplier is None
    assert result.unresolved
