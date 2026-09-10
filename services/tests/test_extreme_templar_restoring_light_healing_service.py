from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_templar_restoring_light_healing_service import (
    ExtremeTemplarRestoringLightHealingService,
)


class _SkillLines:
    lines = {
        "Breath of Life": "Restoring Light",
        "Honor the Dead": "Restoring Light",
        "Combat Prayer": "Restoration Staff",
    }

    def skill_line_for_ability_name(self, name):
        return self.lines.get(name)

    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Mending" else None


def _service():
    return ExtremeTemplarRestoringLightHealingService(
        "fake.db",
        skill_line_repository=_SkillLines(),
    )


def test_mending_rank_two_scales_linearly_with_missing_target_health():
    service = _service()
    build = PlayerBuild(EsoClass="templar")
    progression = CharacterProgression(passive_ranks={"Mending": 2})

    full = service.resolve(
        build=build,
        progression=progression,
        ability_name="Breath of Life",
        target_health_fraction=1.0,
    )
    half = service.resolve(
        build=build,
        progression=progression,
        ability_name="Breath of Life",
        target_health_fraction=0.5,
    )
    quarter = service.resolve(
        build=build,
        progression=progression,
        ability_name="Breath of Life",
        target_health_fraction=0.25,
    )
    empty = service.resolve(
        build=build,
        progression=progression,
        ability_name="Breath of Life",
        target_health_fraction=0.0,
    )

    assert full.multiplier == pytest.approx(1.0)
    assert half.multiplier == pytest.approx(1.065)
    assert quarter.multiplier == pytest.approx(1.0975)
    assert empty.multiplier == pytest.approx(1.13)
    assert empty.unresolved == ()


def test_mending_rank_one_uses_its_reviewed_six_percent_maximum():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="templar"),
        progression=CharacterProgression(passive_ranks={"Mending": 1}),
        ability_name="Breath of Life",
        target_health_fraction=0.25,
    )

    assert result.multiplier == pytest.approx(1.045)
    assert result.unresolved == ()


def test_mending_does_not_modify_non_restoring_light_heals():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="templar"),
        progression=CharacterProgression(passive_ranks={"Mending": 2}),
        ability_name="Combat Prayer",
        target_health_fraction=0.10,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == ()


def test_mending_requires_restoring_light_route_when_class_lines_are_explicit():
    service = _service()
    progression = CharacterProgression(passive_ranks={"Mending": 2})

    removed = service.resolve(
        build=PlayerBuild(
            EsoClass="templar",
            ClassSkillLines=["aedric_spear", "dawns_wrath", "green_balance"],
        ),
        progression=progression,
        ability_name="Breath of Life",
        target_health_fraction=0.25,
    )
    subclassed = service.resolve(
        build=PlayerBuild(
            EsoClass="warden",
            ClassSkillLines=["green_balance", "restoring_light", "siphoning"],
        ),
        progression=progression,
        ability_name="Breath of Life",
        target_health_fraction=0.25,
    )

    assert removed.multiplier == 1.0
    assert subclassed.multiplier == pytest.approx(1.0975)


def test_mending_preserves_lower_bound_when_passive_rank_is_unknown():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="templar"),
        progression=CharacterProgression(passive_ranks=None),
        ability_name="Breath of Life",
        target_health_fraction=0.25,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == ("Mending passive rank is not recorded",)


def test_mending_unknown_ability_line_preserves_lower_bound_and_blocker():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="templar"),
        progression=CharacterProgression(passive_ranks={"Mending": 2}),
        ability_name="Mystery Heal",
        target_health_fraction=0.25,
    )

    assert result.multiplier == 1.0
    assert "Mystery Heal" in result.unresolved[0]
