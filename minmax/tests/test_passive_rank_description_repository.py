from __future__ import annotations

import sqlite3

from minmax.passive_rank_description_repository import PassiveRankDescriptionRepository


def _database(tmp_path, *, raw_description: str = "", ability_description: str = "Rank two tooltip"):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE skill (id INTEGER PRIMARY KEY, name TEXT NOT NULL, is_passive INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, skill_id INTEGER NOT NULL, ability_id INTEGER NOT NULL, rank INTEGER NOT NULL, raw_description TEXT);
            CREATE TABLE ability (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL UNIQUE, description TEXT);
        """)
        db.execute("INSERT INTO skill(id, name, is_passive) VALUES (1, 'Test Passive', 1)")
        db.execute("INSERT INTO ability(id, ability_id, description) VALUES (7, 9001, ?)", (ability_description,))
        db.execute("INSERT INTO skill_rank(id, skill_id, ability_id, rank, raw_description) VALUES (10, 1, 9001, 2, ?)", (raw_description,))
    return path


def test_exact_rank_joins_on_eso_ability_id_not_local_row_id(tmp_path):
    result = PassiveRankDescriptionRepository(_database(tmp_path)).resolve("Test Passive", 2)
    assert result.complete
    assert result.ability_id == 9001
    assert result.description == "Rank two tooltip"


def test_matching_raw_and_ability_descriptions_are_accepted(tmp_path):
    result = PassiveRankDescriptionRepository(_database(tmp_path, raw_description="Rank two tooltip", ability_description="Rank two tooltip")).resolve("Test Passive", 2)
    assert result.complete
    assert result.description == "Rank two tooltip"


def test_rank_description_disagreement_fails_closed(tmp_path):
    result = PassiveRankDescriptionRepository(_database(tmp_path, raw_description="Rank one tooltip", ability_description="Rank two tooltip")).resolve("Test Passive", 2)
    assert not result.complete
    assert result.description is None
    assert result.raw_description == "Rank one tooltip"
    assert result.ability_description == "Rank two tooltip"
    assert "tooltip disagreement" in result.unresolved[0]


def test_missing_rank_fails_closed(tmp_path):
    result = PassiveRankDescriptionRepository(_database(tmp_path)).resolve("Test Passive", 1)
    assert not result.complete
    assert result.unresolved == ("Canonical passive rank not found: Test Passive rank 1",)

def test_matching_rank_descriptions_ignore_eso_color_markup(tmp_path):
    result = PassiveRankDescriptionRepository(
        _database(
            tmp_path,
            raw_description="Increases damage by |cffffff129|r.",
            ability_description="Increases damage by 129.",
        )
    ).resolve("Test Passive", 2)

    assert result.complete
    assert result.description == "Increases damage by 129."
