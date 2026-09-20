from __future__ import annotations

import sqlite3
from pathlib import Path

from services.gear_lookup_text_cleanup_service import clean_gear_lookup_database


def test_clean_gear_lookup_database_strips_color_markup_without_changing_identity() -> None:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE gear_set (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT
        );
        CREATE TABLE gear_set_bonus (
            id INTEGER PRIMARY KEY,
            set_id INTEGER,
            piece_count INTEGER,
            description TEXT
        );
        CREATE TABLE entity (
            id TEXT PRIMARY KEY,
            entity_type TEXT,
            name TEXT
        );
        CREATE TABLE content (
            id INTEGER PRIMARY KEY,
            content_type TEXT,
            name TEXT,
            location TEXT
        );

        INSERT INTO gear_set VALUES
            (1, '|cFFAA00Spell Power Cure|r', '<font color="#FFFFFF">Dungeon</font>');
        INSERT INTO gear_set_bonus VALUES
            (10, 1, 5, '|c00FF00Grants Major Courage|r');
        INSERT INTO entity VALUES
            ('gear:1', 'gear_set', '<cFFFFFF>Perfected Crushing Wall</c>'),
            ('food:1', 'food', '|cFF0000Do Not Touch|r');
        INSERT INTO content VALUES
            (1, 'dungeon', '<span style="color:#FFFFFF">White-Gold Tower</span>', '|cABCDEFImperial City|r');
        """
    )

    changed = clean_gear_lookup_database(connection)

    assert changed == 6
    assert connection.execute("SELECT name, category FROM gear_set WHERE id = 1").fetchone() == (
        "Spell Power Cure",
        "Dungeon",
    )
    assert connection.execute(
        "SELECT description FROM gear_set_bonus WHERE id = 10"
    ).fetchone()[0] == "Grants Major Courage"
    assert connection.execute(
        "SELECT name FROM entity WHERE id = 'gear:1'"
    ).fetchone()[0] == "Perfected Crushing Wall"
    assert connection.execute(
        "SELECT name FROM entity WHERE id = 'food:1'"
    ).fetchone()[0] == "|cFF0000Do Not Touch|r"
    assert connection.execute(
        "SELECT name, location FROM content WHERE id = 1"
    ).fetchone() == ("White-Gold Tower", "Imperial City")


def test_clean_gear_lookup_database_is_idempotent() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE gear_set_bonus (id INTEGER PRIMARY KEY, description TEXT)"
    )
    connection.execute(
        "INSERT INTO gear_set_bonus VALUES (1, '|cFFFFFFAdds 129 Weapon and Spell Damage|r')"
    )

    assert clean_gear_lookup_database(connection) == 1
    assert clean_gear_lookup_database(connection) == 0


def test_gear_lookup_and_importer_share_plain_text_cleanup_boundary() -> None:
    page = Path("ui/gear_lookup_page.py").read_text(encoding="utf-8")
    importer = Path("importers/gear_set_importer.py").read_text(encoding="utf-8")

    assert "clean_gear_lookup_database(connection)" in page
    assert "_plain_text(description)" in page
    assert "_plain_text(name)" in page
    assert "from services.eso_text_cleanup import clean_eso_text" in importer
    assert "clean_eso_text(description)" in importer
