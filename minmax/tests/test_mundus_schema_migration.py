from __future__ import annotations

import sqlite3

import pytest

from minmax.mundus_repository import MundusRepository, canonical_mundus_id


@pytest.mark.parametrize("legacy_fk_column", ["mundus_id", "mundus_stone_id"])
def test_legacy_numeric_mundus_schema_migrates_in_place(tmp_path, legacy_fk_column: str) -> None:
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            f"""
            CREATE TABLE mundus_stone (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                game_update INTEGER NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                UNIQUE(name, game_update)
            );

            CREATE TABLE mundus_effect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {legacy_fk_column} INTEGER NOT NULL,
                stat_id TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                supported INTEGER NOT NULL DEFAULT 1,
                notes TEXT NOT NULL DEFAULT ''
            );
            """
        )
        connection.execute(
            "INSERT INTO mundus_stone(name, game_update, source_url) VALUES (?, ?, ?)",
            ("The Mage", 50, "legacy://source"),
        )
        legacy_id = connection.execute(
            "SELECT id FROM mundus_stone WHERE name = 'The Mage'"
        ).fetchone()[0]
        connection.execute(
            f"""
            INSERT INTO mundus_effect(
                {legacy_fk_column}, stat_id, value, unit, supported, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (legacy_id, "max_magicka", 1999.0, "flat", 1, "legacy row"),
        )
        connection.commit()

    repository = MundusRepository(database, game_update=50)

    assert "The Mage" in repository.list_names()
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        stone_columns = {
            row["name"]: str(row["type"] or "").upper()
            for row in connection.execute("PRAGMA table_info(mundus_stone)")
        }
        effect_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(mundus_effect)")
        }
        assert "TEXT" in stone_columns["id"]
        assert "mundus_id" in effect_columns
        assert "mundus_stone_id" not in effect_columns

        mage_id = canonical_mundus_id("The Mage", 50)
        assert mage_id == "the_mage_u50"
        row = connection.execute(
            """
            SELECT ms.id, me.stat_id, me.value
            FROM mundus_stone ms
            JOIN mundus_effect me ON me.mundus_id = ms.id
            WHERE ms.name = 'The Mage' AND ms.game_update = 50
            """
        ).fetchone()
        assert row is not None
        assert row["id"] == mage_id
        assert row["stat_id"] == "max_magicka"
        # Seeding refreshes the legacy value to the canonical U50 value.
        assert row["value"] == 2023.0


def test_canonical_mundus_ids_are_lower_snake_case(tmp_path) -> None:
    database = tmp_path / "eso.db"
    MundusRepository(database, game_update=50)

    with sqlite3.connect(database) as connection:
        ids = [row[0] for row in connection.execute("SELECT id FROM mundus_stone ORDER BY id")]

    assert ids
    assert all(mundus_id == mundus_id.lower() for mundus_id in ids)
    assert all(" " not in mundus_id and "-" not in mundus_id for mundus_id in ids)
    assert "the_thief_u50" in ids
