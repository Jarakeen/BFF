from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


def _context(*buffs: str, build: PlayerBuild | None = None):
    return BuildCalculationContextFactory().build(
        character_id="character",
        build_id="build",
        build=build or PlayerBuild(),
        progression=CharacterProgression(),
        combat_state=CombatState(active_buffs=tuple(buffs)),
    )


def _step_labels(trace) -> list[str]:
    labels: list[str] = []
    for step in trace.steps:
        labels.append(step.label if hasattr(step, "label") else step[0])
    return labels


def test_combat_state_canonicalizes_and_deduplicates_named_buffs():
    state = CombatState(active_buffs=(" major sorcery ", "Major Sorcery", "MAJOR PROPHECY"))

    assert state.active_buffs == ("Major Sorcery", "Major Prophecy")
    assert state.has_buff("major sorcery")
    assert state.has_buff("Major Prophecy")


def test_selected_potion_does_not_activate_any_named_buff():
    context = _context(build=PlayerBuild(Potion="spell power"))

    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1000
    assert context.core_state.derived[StatId.SPELL_CRITICAL].final_value == pytest.approx(0.10)
    assert context.combat_state.active_buffs == ()


def test_major_courage_flat_is_applied_before_major_sorcery_percent():
    context = _context("Major Courage", "Major Sorcery")
    trace = context.core_state.derived[StatId.SPELL_DAMAGE]

    assert trace.final_value == 1716
    assert "Combat buff: Major Courage" in _step_labels(trace)
    assert "percentage modifiers" in _step_labels(trace)


def test_major_brutality_and_sorcery_modify_only_their_matching_damage_stats():
    brutality = _context("Major Brutality")
    sorcery = _context("Major Sorcery")

    assert brutality.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1200
    assert brutality.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1000
    assert sorcery.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1000
    assert sorcery.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1200


def test_major_prophecy_routes_verified_critical_rating_conversion():
    context = _context("Major Prophecy")
    expected = 0.10 + GearStatInputResolver.critical_rating_to_ratio(2629.0)

    assert context.core_state.derived[StatId.SPELL_CRITICAL].final_value == pytest.approx(expected)


def test_major_mending_and_force_route_to_separate_ratio_stats():
    context = _context("Major Mending", "Major Force")

    assert context.core_state.derived[StatId.HEALING_DONE].final_value == pytest.approx(0.16)
    assert context.core_state.derived[StatId.CRITICAL_DAMAGE].final_value == pytest.approx(0.70)
    assert context.core_state.derived[StatId.CRITICAL_HEALING].final_value == pytest.approx(0.0)


def test_major_resolve_routes_to_both_resistances():
    context = _context("Major Resolve")

    assert context.core_state.derived[StatId.PHYSICAL_RESISTANCE].final_value == 5948
    assert context.core_state.derived[StatId.SPELL_RESISTANCE].final_value == 5948


def test_recovery_buffs_and_minor_toughness_route_to_primary_resource_layer():
    context = _context("Major Fortitude", "Major Intellect", "Major Endurance", "Minor Toughness")

    assert context.character_state.max_health == 17600
    assert context.character_state.health_recovery == 402
    assert context.character_state.magicka_recovery == 669
    assert context.character_state.stamina_recovery == 669


def test_unmapped_active_buff_remains_explicitly_unresolved():
    context = _context("Major Berserk")

    assert "Active combat buff not yet stat-mapped: Major Berserk" in context.unresolved_gear_effects
