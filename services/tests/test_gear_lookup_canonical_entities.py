import sqlite3

from ui.gear_lookup_page import GearLookupPage


def test_canonical_entity_sets_include_entity_only_arena_weapon_and_skip_duplicates():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE gear_set (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE entity (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL
        );

        INSERT INTO gear_set (id, name)
        VALUES (1, 'Perfected Crushing Wall');

        INSERT INTO entity (id, entity_type, name, slug)
        VALUES
            ('gear_set:perfected-crushing-wall', 'gear_set', 'Perfected Crushing Wall', 'perfected-crushing-wall'),
            ('gear_set:perfected-puncturing-remedy', 'gear_set', 'Perfected Puncturing Remedy', 'perfected-puncturing-remedy'),
            ('food:witchmothers-potent-brew', 'food', 'Witchmother''s Potent Brew', 'witchmothers-potent-brew');
        """
    )

    rows = GearLookupPage._canonical_entity_sets(
        connection,
        {"gear_set", "entity"},
        {"perfected crushing wall"},
    )

    assert [row["name"] for row in rows] == ["Perfected Puncturing Remedy"]
    assert rows[0]["gear_set_id"] is None
    assert rows[0]["id"] == "entity:gear_set:perfected-puncturing-remedy"
    assert rows[0]["sources"] == ["Canonical entity catalog"]


def test_canonical_entity_sets_is_safe_without_entity_table():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE gear_set (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")

    assert GearLookupPage._canonical_entity_sets(
        connection,
        {"gear_set"},
        set(),
    ) == []
