import sqlite3

from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository


def test_semantic_effect_types_do_not_require_engine_stat_mapping(tmp_path):
    database = tmp_path / "glyphs.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE jewelry_glyph (
                item_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE jewelry_glyph_effect (
                id INTEGER PRIMARY KEY,
                glyph_item_id INTEGER NOT NULL,
                effect_type TEXT NOT NULL,
                value_min REAL,
                value_max REAL,
                unit TEXT NOT NULL,
                description TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO jewelry_glyph(item_id, name) VALUES (?, ?)",
            (1, "Glyph of Bracing"),
        )
        connection.execute(
            """
            INSERT INTO jewelry_glyph_effect(
                id, glyph_item_id, effect_type, value_min, value_max, unit, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, 1, "block_cost_reduction", 100, 200, "flat", "Reduce the cost of Block"),
        )

    repository = JewelryGlyphEffectRepository(database)

    assert repository.get_jewelry_glyph_effect_types_by_name(" glyph of bracing ") == (
        "block_cost_reduction",
    )
