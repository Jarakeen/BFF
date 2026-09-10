from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_templar_light_weaver_service import (
    ExtremeTemplarLightWeaverService,
)


class _SkillLines:
    lines = {
        "Breath of Life": "Restoring Light",
        "Combat Prayer": "Restoration Staff",
    }

    def skill_line_for_ability_name(self, name):
        return self.lines.get(name)

    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Light Weaver" else None


def _service():
    return ExtremeTemplarLightWeaverService(
        "fake.db",
        skill_line_repository=_SkillLines(),
    )


def test_light_weaver_rank_two_grants_two_ultimate_to_low_health_ally():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Light Weaver": 2}),
        ability_name="Breath of Life",
        target_health_fraction=0.49,
        target_is_ally=True,
    )

    assert result.ally_ultimate_granted == 2
    assert result.unresolved == ()


def test_light_weaver_rank_one_grants_one_ultimate_to_low_health_ally():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Light Weaver": 1}),
        ability_name="Breath of Life",
        target_health_fraction=0.10,
        target_is_ally=True,
    )

    assert result.ally_ultimate_granted == 1
    assert result.automatic_block_cooldown_seconds == pytest.approx(30.0)


def test_light_weaver_does_not_grant_ultimate_at_exactly_half_health():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Light Weaver": 2}),
        ability_name="Breath of Life",
        target_health_fraction=0.50,
        target_is_ally=True,
    )

    assert result.ally_ultimate_granted == 0


def test_light_weaver_does_not_grant_ultimate_to_self_or_non_restoring_light_heal():
    service = _service()
    progression = CharacterProgression(passive_ranks={"Light Weaver": 2})

    self_heal = service.resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=progression,
        ability_name="Breath of Life",
        target_health_fraction=0.10,
        target_is_ally=False,
    )
    restoration_staff = service.resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=progression,
        ability_name="Combat Prayer",
        target_health_fraction=0.10,
        target_is_ally=True,
    )

    assert self_heal.ally_ultimate_granted == 0
    assert restoration_staff.ally_ultimate_granted == 0


def test_light_weaver_rank_two_auto_blocks_for_two_seconds_when_off_cooldown():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Light Weaver": 2}),
        activation_has_cast_or_channel_time=True,
        in_combat=True,
        activation_time_seconds=20.0,
        previous_automatic_block_proc_time_seconds=5.0,
    )

    assert result.automatic_block_active
    assert result.automatic_block_seconds == pytest.approx(2.0)
    assert result.automatic_block_cooldown_seconds == pytest.approx(15.0)


def test_light_weaver_rank_two_auto_block_respects_cooldown():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Light Weaver": 2}),
        activation_has_cast_or_channel_time=True,
        in_combat=True,
        activation_time_seconds=19.99,
        previous_automatic_block_proc_time_seconds=5.0,
    )

    assert not result.automatic_block_active
    assert result.automatic_block_seconds == 0.0


def test_light_weaver_auto_block_requires_cast_or_channel_and_combat():
    service = _service()
    progression = CharacterProgression(passive_ranks={"Light Weaver": 2})

    instant = service.resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=progression,
        activation_has_cast_or_channel_time=False,
        in_combat=True,
        activation_time_seconds=10.0,
    )
    out_of_combat = service.resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=progression,
        activation_has_cast_or_channel_time=True,
        in_combat=False,
        activation_time_seconds=10.0,
    )

    assert not instant.automatic_block_active
    assert not out_of_combat.automatic_block_active


def test_light_weaver_respects_explicit_subclass_route():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Aedric Spear", "Dawn's Wrath", "Green Balance"],
        ),
        progression=CharacterProgression(passive_ranks={"Light Weaver": 2}),
        ability_name="Breath of Life",
        target_health_fraction=0.10,
        target_is_ally=True,
        activation_has_cast_or_channel_time=True,
        in_combat=True,
        activation_time_seconds=10.0,
    )

    assert result.ally_ultimate_granted == 0
    assert not result.automatic_block_active


def test_light_weaver_unknown_rank_preserves_lower_bound_and_blocker():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks=None),
        ability_name="Breath of Life",
        target_health_fraction=0.10,
        target_is_ally=True,
    )

    assert result.ally_ultimate_granted == 0
    assert not result.automatic_block_active
    assert result.unresolved == ("Light Weaver passive rank is not recorded",)


def test_light_weaver_rejects_impossible_runtime_timing():
    with pytest.raises(ValueError, match="cannot occur after activation"):
        _service().resolve(
            build=PlayerBuild(EsoClass="Templar"),
            progression=CharacterProgression(passive_ranks={"Light Weaver": 2}),
            activation_has_cast_or_channel_time=True,
            in_combat=True,
            activation_time_seconds=10.0,
            previous_automatic_block_proc_time_seconds=11.0,
        )
