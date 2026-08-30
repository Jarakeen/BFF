from __future__ import annotations

import sqlite3

import pytest

from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.context_factory import BuildCalculationContextFactory
from minmax.stat_ids import StatId
from models.build_model import ChampionPointEntry, PlayerBuild


def _repo(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.execute(
        """
        CREATE TABLE champion_point (
            name TEXT PRIMARY KEY,
            skill_type INTEGER,
            max_points INTEGER,
            jump_points TEXT,
            description TEXT,
            min_description TEXT,
            max_description TEXT
        )
        """
    )
    db.execute(
        "INSERT INTO champion_point VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "Bracing Anchor",
            1,
            50,
            "0,10,20,30,40,50",
            "",
            "While in combat, increase the amount of damage you can block by 4% per stage, but reduces your Movement Speed by 16% at all stages.",
            "While in combat, increase the amount of damage you can block by 4% per stage, but reduces your Movement Speed by 16% at all stages.",
        ),
    )
    db.commit()
    db.close()
    return ChampionPointStaticRepository(path)


def _build(points: int) -> PlayerBuild:
    return PlayerBuild(
        ChampionPoints=[ChampionPointEntry(Name="Bracing Anchor", Points=str(points))]
    )


def test_bracing_anchor_is_known_but_inactive_out_of_combat(tmp_path):
    context = BuildCalculationContextFactory(
        champion_point_repository=_repo(tmp_path),
    ).build(
        character_id="character",
        build_id="tank",
        build=_build(50),
        progression=CharacterProgression(),
        combat_state=CombatState(in_combat=False),
    )

    assert context.combat_state.in_combat is False
    assert context.core_state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.50)
    assert not any("Bracing Anchor" in message for message in context.unresolved_gear_effects)


def test_bracing_anchor_applies_maxed_amount_blocked_bonus_in_combat(tmp_path):
    context = BuildCalculationContextFactory(
        champion_point_repository=_repo(tmp_path),
    ).build(
        character_id="character",
        build_id="tank",
        build=_build(50),
        progression=CharacterProgression(),
        combat_state=CombatState(in_combat=True),
    )

    trace = context.core_state.derived[StatId.BLOCK_MITIGATION]
    assert context.combat_state.in_combat is True
    assert trace.final_value == pytest.approx(0.60)
    assert any(
        step.label == "Champion Point: Bracing Anchor (in combat)"
        and step.value == pytest.approx(0.20)
        for step in trace.steps
    )
    assert not any("Bracing Anchor" in message for message in context.unresolved_gear_effects)


def test_bracing_anchor_uses_completed_stage_scaling(tmp_path):
    context = BuildCalculationContextFactory(
        champion_point_repository=_repo(tmp_path),
    ).build(
        character_id="character",
        build_id="tank",
        build=_build(30),
        progression=CharacterProgression(),
        combat_state=CombatState(in_combat=True),
    )

    # Three completed stages at 4% amount blocked each: 50% + (50% * 12%) = 56%.
    assert context.core_state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.56)
