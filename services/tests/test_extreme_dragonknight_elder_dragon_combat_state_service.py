from __future__ import annotations

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_dragonknight_elder_dragon_combat_state_service import (
    ExtremeDragonknightElderDragonCombatStateService,
)


class _SkillLines:
    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Elder Dragon" else None


def _service():
    return ExtremeDragonknightElderDragonCombatStateService(
        "fake.db",
        skill_line_repository=_SkillLines(),
    )


def test_elder_dragon_grants_minor_brutality_in_explicit_active_window():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Dragonknight"),
        progression=CharacterProgression(passive_ranks={"Elder Dragon": 2}),
        elder_dragon_window_active=True,
    )

    assert result.minor_brutality_active
    assert result.combat_state.has_buff("Minor Brutality")
    assert result.unresolved == ()


def test_elder_dragon_is_not_invented_without_explicit_window():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Dragonknight"),
        progression=CharacterProgression(passive_ranks={"Elder Dragon": 2}),
        elder_dragon_window_active=False,
    )

    assert not result.minor_brutality_active
    assert not result.combat_state.active_buffs
    assert result.unresolved == ()


def test_rank_one_elder_dragon_can_supply_same_named_buff():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Dragonknight"),
        progression=CharacterProgression(passive_ranks={"Elder Dragon": 1}),
        elder_dragon_window_active=True,
    )

    assert result.minor_brutality_active
    assert result.combat_state.has_buff("Minor Brutality")
    assert result.unresolved == ()


def test_explicit_subclass_route_can_remove_native_elder_dragon():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Dragonknight",
            ClassSkillLines=["Ardent Flame", "Earthen Heart", "Restoring Light"],
        ),
        progression=CharacterProgression(passive_ranks={"Elder Dragon": 2}),
        elder_dragon_window_active=True,
    )

    assert not result.minor_brutality_active
    assert result.unresolved == (
        "Elder Dragon scenario requires an equipped Draconic Power class line",
    )


def test_foreign_class_can_gain_elder_dragon_through_draconic_power_route():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Draconic Power"],
        ),
        progression=CharacterProgression(passive_ranks={"Elder Dragon": 2}),
        elder_dragon_window_active=True,
    )

    assert result.minor_brutality_active
    assert result.combat_state.has_buff("Minor Brutality")
    assert result.unresolved == ()


def test_unknown_elder_dragon_rank_preserves_unbuffed_state_and_blocker():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Dragonknight"),
        progression=CharacterProgression(passive_ranks=None),
        elder_dragon_window_active=True,
    )

    assert not result.minor_brutality_active
    assert result.unresolved == ("Elder Dragon passive rank is not recorded",)


def test_missing_elder_dragon_rank_preserves_unbuffed_state_and_blocker():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Dragonknight"),
        progression=CharacterProgression(passive_ranks={}),
        elder_dragon_window_active=True,
    )

    assert not result.minor_brutality_active
    assert result.unresolved == (
        "Passive rank is not recorded for character: Elder Dragon",
    )


def test_unlearned_elder_dragon_does_not_grant_minor_brutality():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Dragonknight"),
        progression=CharacterProgression(passive_ranks={"Elder Dragon": 0}),
        elder_dragon_window_active=True,
    )

    assert not result.minor_brutality_active
    assert result.unresolved == ()
