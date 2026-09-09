from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_templar_mending_healing_service import (
    ExtremeTemplarMendingHealingService,
)


def _progression(rank):
    ranks = None if rank is ... else {"Mending": rank}
    return CharacterProgression(
        owned_skill_lines=("Restoring Light",),
        passive_ranks=ranks,
    )


def test_rank_two_scales_linearly_with_target_missing_health():
    result = ExtremeTemplarMendingHealingService().resolve(
        build=PlayerBuild(BuildName="Templar", EsoClass="Templar"),
        progression=_progression(2),
        target_health_fraction=0.25,
    )

    assert result.passive_rank == 2
    assert result.healing_done_bonus == pytest.approx(0.0975)
    assert result.multiplier == pytest.approx(1.0975)
    assert result.unresolved == ()


def test_rank_one_uses_reviewed_six_percent_ceiling():
    result = ExtremeTemplarMendingHealingService().resolve(
        build=PlayerBuild(BuildName="Templar", EsoClass="Templar"),
        progression=_progression(1),
        target_health_fraction=0.50,
    )

    assert result.healing_done_bonus == pytest.approx(0.03)
    assert result.multiplier == pytest.approx(1.03)
    assert result.unresolved == ()


def test_full_health_target_has_zero_mending_bonus():
    result = ExtremeTemplarMendingHealingService().resolve(
        build=PlayerBuild(BuildName="Templar", EsoClass="Templar"),
        progression=_progression(2),
        target_health_fraction=1.0,
    )

    assert result.healing_done_bonus == 0.0
    assert result.multiplier == 1.0
    assert result.unresolved == ()


def test_missing_target_health_preserves_explicit_blocker():
    result = ExtremeTemplarMendingHealingService().resolve(
        build=PlayerBuild(BuildName="Templar", EsoClass="Templar"),
        progression=_progression(2),
        target_health_fraction=None,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == (
        "Mending requires explicit heal-target Health fraction",
    )


def test_missing_passive_rank_preserves_lower_bound_and_blocker():
    result = ExtremeTemplarMendingHealingService().resolve(
        build=PlayerBuild(BuildName="Templar", EsoClass="Templar"),
        progression=CharacterProgression(
            owned_skill_lines=("Restoring Light",),
            passive_ranks={},
        ),
        target_health_fraction=0.25,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == (
        "Passive rank is not recorded for character: Mending",
    )


def test_explicit_subclass_route_with_restoring_light_can_use_mending():
    result = ExtremeTemplarMendingHealingService().resolve(
        build=PlayerBuild(
            BuildName="Subclass healer",
            EsoClass="Warden",
            ClassSkillLines=["green_balance", "restoring_light", "siphoning"],
        ),
        progression=_progression(2),
        target_health_fraction=0.0,
    )

    assert result.healing_done_bonus == pytest.approx(0.13)
    assert result.unresolved == ()


def test_explicit_route_without_restoring_light_does_not_claim_mending():
    result = ExtremeTemplarMendingHealingService().resolve(
        build=PlayerBuild(
            BuildName="No Templar line",
            EsoClass="Templar",
            ClassSkillLines=["green_balance", "living_death", "siphoning"],
        ),
        progression=_progression(2),
        target_health_fraction=0.0,
    )

    assert result.multiplier == 1.0
    assert result.healing_done_bonus == 0.0
    assert result.unresolved == ()


def test_target_health_fraction_must_be_normalized():
    with pytest.raises(ValueError, match="target_health_fraction"):
        ExtremeTemplarMendingHealingService().resolve(
            build=PlayerBuild(BuildName="Templar", EsoClass="Templar"),
            progression=_progression(2),
            target_health_fraction=-0.01,
        )
