from __future__ import annotations

import pytest

from models.build_model import PlayerBuild
from services.extreme_arcanist_cascading_fortune_healing_service import (
    ExtremeArcanistCascadingFortuneHealingService,
)


def _service():
    return ExtremeArcanistCascadingFortuneHealingService()


def test_cascading_fortune_scales_linearly_with_missing_target_health():
    service = _service()
    build = PlayerBuild(EsoClass="arcanist")

    full = service.resolve(
        build=build,
        ability_name="Cascading Fortune",
        target_health_fraction=1.0,
    )
    half = service.resolve(
        build=build,
        ability_name="Cascading Fortune",
        target_health_fraction=0.5,
    )
    quarter = service.resolve(
        build=build,
        ability_name="Cascading Fortune",
        target_health_fraction=0.25,
    )
    empty = service.resolve(
        build=build,
        ability_name="Cascading Fortune",
        target_health_fraction=0.0,
    )

    assert full.multiplier == pytest.approx(1.0)
    assert half.multiplier == pytest.approx(1.25)
    assert quarter.multiplier == pytest.approx(1.375)
    assert empty.multiplier == pytest.approx(1.50)
    assert empty.unresolved == ()


def test_cascading_fortune_does_not_modify_other_heals():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="arcanist"),
        ability_name="Combat Prayer",
        target_health_fraction=0.10,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == ()


def test_cascading_fortune_requires_curative_runeforms_when_class_lines_are_explicit():
    service = _service()

    removed = service.resolve(
        build=PlayerBuild(
            EsoClass="arcanist",
            ClassSkillLines=["herald_of_the_tome", "soldier_of_apocrypha", "green_balance"],
        ),
        ability_name="Cascading Fortune",
        target_health_fraction=0.25,
    )
    subclassed = service.resolve(
        build=PlayerBuild(
            EsoClass="warden",
            ClassSkillLines=["green_balance", "curative_runeforms", "siphoning"],
        ),
        ability_name="Cascading Fortune",
        target_health_fraction=0.25,
    )

    assert removed.multiplier == 1.0
    assert subclassed.multiplier == pytest.approx(1.375)


def test_cascading_fortune_without_target_health_does_not_invent_emergency_bonus():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="arcanist"),
        ability_name="Cascading Fortune",
        target_health_fraction=None,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == ()


def test_cascading_fortune_rejects_invalid_target_health():
    with pytest.raises(ValueError, match="between 0 and 1"):
        _service().resolve(
            build=PlayerBuild(EsoClass="arcanist"),
            ability_name="Cascading Fortune",
            target_health_fraction=-0.01,
        )
