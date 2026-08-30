import sqlite3

import pytest

from minmax.base_character_state import BaseCharacterCalculator
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.character_progression import CharacterProgression
from minmax.core_stat_calculator import CoreStatCalculator
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.static_build_inputs import StaticBuildInputResolver
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


def _db(tmp_path):
    path = tmp_path / "eso.db"
    connection = sqlite3.connect(path)
    connection.execute(
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
    return path, connection


def _insert(connection, name, max_points, jumps, description):
    connection.execute(
        "INSERT INTO champion_point VALUES (?, 0, ?, ?, '', ?, ?)",
        (name, max_points, jumps, description, description),
    )


def test_passive_block_champion_points_feed_block_specific_buckets(tmp_path):
    path, db = _db(tmp_path)
    _insert(
        db,
        "Tireless Guardian",
        20,
        "0,10,20",
        "Reduces the cost of Block by 20 Stamina per stage.",
    )
    _insert(
        db,
        "Fortification",
        30,
        "0,15,30",
        "Increases the amount of damage you can block by 2% per stage.",
    )
    db.commit()
    db.close()

    result = StaticBuildInputResolver(
        champion_point_repository=ChampionPointStaticRepository(path),
    ).apply(GearCalculationInputs(), PlayerBuild())

    assert result.core.block_cost.flat_reductions == (
        ("Champion Point: Tireless Guardian", 40.0),
    )
    assert result.core.block_mitigation.amount_blocked_modifiers == (
        ("Champion Point: Fortification", pytest.approx(0.04)),
    )
    assert result.unresolved == ()

    state = CoreStatCalculator().calculate(
        character_progression=CharacterProgression(),
        base_character=BaseCharacterCalculator().calculate(),
        inputs=result.core,
    )
    assert state.derived[StatId.BLOCK_COST].final_value == 1710
    assert state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.52)


def test_savage_defense_stays_out_of_block_cost_pipeline(tmp_path):
    path, db = _db(tmp_path)
    _insert(
        db,
        "Savage Defense",
        30,
        "0,15,30",
        "Reduces the cost of Bash by 45 Stamina per stage.",
    )
    db.commit()
    db.close()

    result = StaticBuildInputResolver(
        champion_point_repository=ChampionPointStaticRepository(path),
    ).apply(GearCalculationInputs(), PlayerBuild())

    assert result.core.block_cost.flat_reductions == ()
    assert result.unresolved == (
        "Champion Point is dynamic or not yet stat-mapped: Savage Defense",
    )
