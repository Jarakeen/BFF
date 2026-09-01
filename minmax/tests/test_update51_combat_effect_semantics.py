from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from minmax.combat_effect_semantics import (
    GameUpdate,
    U51_NEW_ALCHEMY_TRAITS,
    resolve_alchemy_trait_name,
    resolve_buff_name,
)
from minmax.combat_state import CombatState
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


def _context(*buffs: str, update: GameUpdate):
    return BuildCalculationContextFactory().build(
        character_id="character",
        build_id="build",
        build=PlayerBuild(),
        progression=CharacterProgression(),
        combat_state=CombatState(active_buffs=tuple(buffs), game_update=update),
    )


def test_u50_named_buff_semantics_remain_unchanged():
    context = _context("Major Brutality", update=GameUpdate.U50)

    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1200
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1000


def test_u51_major_brutality_routes_to_both_weapon_and_spell_damage():
    context = _context("Major Brutality", update=GameUpdate.U51)

    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1200
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1200
    assert context.unresolved_gear_effects == ()


def test_u51_major_savagery_routes_to_both_critical_stats():
    context = _context("Major Savagery", update=GameUpdate.U51)
    expected = 0.10 + GearStatInputResolver.critical_rating_to_ratio(2629.0)

    assert context.core_state.derived[StatId.WEAPON_CRITICAL].final_value == pytest.approx(expected)
    assert context.core_state.derived[StatId.SPELL_CRITICAL].final_value == pytest.approx(expected)


def test_u51_removed_source_buff_fails_closed_in_strict_mode():
    context = _context("Major Sorcery", update=GameUpdate.U51)

    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1000
    assert context.unresolved_gear_effects == (
        "Active combat buff not stat-mapped for U51: Major Sorcery",
    )


def test_u51_legacy_buff_alias_can_migrate_deliberately():
    assert resolve_buff_name(
        "Major Sorcery",
        game_update=GameUpdate.U51,
        allow_legacy_alias=True,
    ) == "Major Brutality"
    assert resolve_buff_name(
        "Major Prophecy",
        game_update=GameUpdate.U51,
        allow_legacy_alias=True,
    ) == "Major Savagery"


def test_u51_alchemy_traits_have_explicit_legacy_transitions():
    assert resolve_alchemy_trait_name(
        "Increase Spell Power",
        game_update=GameUpdate.U51,
        allow_legacy_alias=True,
    ) == "Increase Power"
    assert resolve_alchemy_trait_name(
        "Increase Weapon Power",
        game_update=GameUpdate.U51,
        allow_legacy_alias=True,
    ) == "Increase Power"
    assert resolve_alchemy_trait_name(
        "Spell Critical",
        game_update=GameUpdate.U51,
        allow_legacy_alias=True,
    ) == "Critical"
    assert resolve_alchemy_trait_name(
        "Weapon Critical",
        game_update=GameUpdate.U51,
        allow_legacy_alias=True,
    ) == "Critical"
    assert resolve_alchemy_trait_name(
        "Maim",
        game_update=GameUpdate.U51,
        allow_legacy_alias=True,
    ) == "Cowardice"


def test_u51_historical_alchemy_source_names_do_not_silently_migrate():
    assert resolve_alchemy_trait_name(
        "Increase Spell Power",
        game_update=GameUpdate.U51,
        allow_legacy_alias=False,
    ) is None
    assert resolve_alchemy_trait_name(
        "Maim",
        game_update=GameUpdate.U51,
        allow_legacy_alias=False,
    ) is None


def test_u51_new_alchemy_trait_vocabulary_is_explicit():
    assert U51_NEW_ALCHEMY_TRAITS == {
        "Mending",
        "Vexation",
        "Damage Shield",
        "Heal Absorption",
        "Force",
    }
