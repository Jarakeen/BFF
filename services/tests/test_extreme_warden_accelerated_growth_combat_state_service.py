from __future__ import annotations

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_warden_accelerated_growth_combat_state_service import (
    ExtremeWardenAcceleratedGrowthCombatStateService,
)


def _progression(rank):
    ranks = None if rank is ... else {"Accelerated Growth": rank}
    return CharacterProgression(
        owned_skill_lines=("Green Balance",),
        passive_ranks=ranks,
    )


def test_inactive_window_is_neutral_even_when_passive_is_owned():
    result = ExtremeWardenAcceleratedGrowthCombatStateService().resolve(
        build=PlayerBuild(BuildName="Warden", EsoClass="Warden"),
        progression=_progression(2),
        accelerated_growth_window_active=False,
    )

    assert result.combat_state.active_buffs == ()
    assert not result.major_mending_active
    assert result.active_window_seconds is None
    assert result.unresolved == ()


def test_rank_two_active_window_routes_major_mending_through_combat_state():
    result = ExtremeWardenAcceleratedGrowthCombatStateService().resolve(
        build=PlayerBuild(BuildName="Warden", EsoClass="Warden"),
        progression=_progression(2),
        accelerated_growth_window_active=True,
    )

    assert result.combat_state.active_buffs == ("Major Mending",)
    assert result.major_mending_active
    assert result.active_window_seconds == 4.0
    assert result.unresolved == ()


def test_rank_one_active_window_preserves_reviewed_two_second_duration():
    result = ExtremeWardenAcceleratedGrowthCombatStateService().resolve(
        build=PlayerBuild(BuildName="Warden", EsoClass="Warden"),
        progression=_progression(1),
        accelerated_growth_window_active=True,
    )

    assert result.combat_state.active_buffs == ("Major Mending",)
    assert result.active_window_seconds == 2.0
    assert result.unresolved == ()


def test_explicit_subclass_route_with_green_balance_is_legal():
    result = ExtremeWardenAcceleratedGrowthCombatStateService().resolve(
        build=PlayerBuild(
            BuildName="Subclass",
            EsoClass="Templar",
            ClassSkillLines=["restoring_light", "green_balance", "siphoning"],
        ),
        progression=_progression(2),
        accelerated_growth_window_active=True,
    )

    assert result.major_mending_active
    assert result.combat_state.active_buffs == ("Major Mending",)
    assert result.unresolved == ()


def test_explicit_route_without_green_balance_blocks_claimed_window():
    result = ExtremeWardenAcceleratedGrowthCombatStateService().resolve(
        build=PlayerBuild(
            BuildName="No Green Balance",
            EsoClass="Warden",
            ClassSkillLines=["restoring_light", "living_death", "siphoning"],
        ),
        progression=_progression(2),
        accelerated_growth_window_active=True,
    )

    assert not result.major_mending_active
    assert result.combat_state.active_buffs == ()
    assert result.unresolved == (
        "Accelerated Growth scenario requires an equipped Green Balance class line",
    )


def test_missing_passive_rank_blocks_claimed_window():
    result = ExtremeWardenAcceleratedGrowthCombatStateService().resolve(
        build=PlayerBuild(BuildName="Warden", EsoClass="Warden"),
        progression=CharacterProgression(
            owned_skill_lines=("Green Balance",),
            passive_ranks={},
        ),
        accelerated_growth_window_active=True,
    )

    assert not result.major_mending_active
    assert result.unresolved == (
        "Passive rank is not recorded for character: Accelerated Growth",
    )


def test_zero_passive_rank_cannot_create_major_mending():
    result = ExtremeWardenAcceleratedGrowthCombatStateService().resolve(
        build=PlayerBuild(BuildName="Warden", EsoClass="Warden"),
        progression=_progression(0),
        accelerated_growth_window_active=True,
    )

    assert not result.major_mending_active
    assert result.combat_state.active_buffs == ()
    assert result.unresolved == ()
