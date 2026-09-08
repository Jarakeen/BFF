import sqlite3

from minmax.character_progression import CharacterProgression
from services.extreme_bash_deadly_bash_service import ExtremeDeadlyBashService


def _database(tmp_path, description="WITH ONE HAND WEAPON AND SHIELD EQUIPPED Improves your standard Bash attacks, causing them to deal 500 more damage and cost 50% less Stamina."):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                is_passive INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                rank INTEGER NOT NULL,
                raw_description TEXT
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                description TEXT
            );
            """
        )
        db.execute(
            "INSERT INTO skill(id, name, description, is_passive) VALUES (1, 'Deadly Bash', '', 1)"
        )
        db.execute(
            "INSERT INTO ability(ability_id, description) VALUES (100, ?)",
            (description,),
        )
        db.execute(
            "INSERT INTO skill_rank(id, skill_id, ability_id, rank, raw_description) VALUES (10, 1, 100, 2, '')"
        )
    return path


def test_max_rank_maps_deadly_bash_to_skill_formula_channels(tmp_path):
    result = ExtremeDeadlyBashService(_database(tmp_path)).resolve(
        CharacterProgression(passive_ranks={"Deadly Bash": 2})
    )

    assert result.mechanic_complete
    assert result.rank == 2
    assert result.skill2_bash_damage == 500.0
    assert result.skill_bash_cost == -0.5


def test_explicit_unpurchased_deadly_bash_is_reviewed_zero(tmp_path):
    result = ExtremeDeadlyBashService(_database(tmp_path)).resolve(
        CharacterProgression(passive_ranks={"Deadly Bash": 0})
    )

    assert result.mechanic_complete
    assert result.skill2_bash_damage == 0.0
    assert result.skill_bash_cost == 0.0


def test_unknown_passive_rank_fails_closed(tmp_path):
    result = ExtremeDeadlyBashService(_database(tmp_path)).resolve(
        CharacterProgression(passive_ranks=None)
    )

    assert not result.mechanic_complete
    assert result.skill2_bash_damage is None
    assert result.unresolved == ("Passive rank is not recorded for character: Deadly Bash",)


def test_missing_recorded_rank_fails_closed(tmp_path):
    result = ExtremeDeadlyBashService(_database(tmp_path)).resolve(
        CharacterProgression(passive_ranks={"Deadly Bash": 1})
    )

    assert not result.mechanic_complete
    assert result.unresolved == ("Canonical Deadly Bash rank not found: 1",)


def test_unrecognized_tooltip_fails_closed(tmp_path):
    result = ExtremeDeadlyBashService(
        _database(tmp_path, description="Deadly Bash has changed in a way we have not reviewed.")
    ).resolve(CharacterProgression(passive_ranks={"Deadly Bash": 2}))

    assert not result.mechanic_complete
    assert result.skill2_bash_damage is None
    assert result.skill_bash_cost is None
    assert result.unresolved[0].startswith("Unrecognized Deadly Bash tooltip:")
