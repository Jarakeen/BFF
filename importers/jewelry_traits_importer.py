# ==================================================
# Black Feather Foundry
#
# File:
# importers/jewelry_glyph_importer.py
#
# Purpose:
# Import mined ESO jewelry glyph definitions
# and their semantic effects.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from services.eso_database import EsoDatabase

from parsers.jewelry_glyph_parser import (
    JewelryGlyphParser,
)


class JewelryGlyphImporter:

    def __init__(
        self,
        db: EsoDatabase,
        source_path: Path,
    ):
        self.db = db
        self.source_path = source_path

    # --------------------------------------------------
    # Schema
    # --------------------------------------------------

    def create_schema(self):

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS jewelry_glyph (
                item_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                icon TEXT,
                level_range TEXT,
                quality_range TEXT,
                value_range TEXT,
                enchant_name TEXT,
                enchant_description TEXT,
                glyph_min_level TEXT,
                craft_skill_rank INTEGER,
                default_enchant_id INTEGER,
                craft_type INTEGER
            )
            """
        )

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS jewelry_glyph_effect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                glyph_item_id INTEGER NOT NULL,
                effect_type TEXT NOT NULL,
                value_min REAL,
                value_max REAL,
                unit TEXT NOT NULL,
                description TEXT,

                FOREIGN KEY(glyph_item_id)
                    REFERENCES jewelry_glyph(item_id)
            )
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_jewelry_glyph_effect_glyph
            ON jewelry_glyph_effect(glyph_item_id)
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_jewelry_glyph_effect_type
            ON jewelry_glyph_effect(effect_type)
            """
        )

    # --------------------------------------------------
    # Import glyphs
    # --------------------------------------------------

    def import_glyphs(
        self,
        rows: list[dict],
    ) -> int:

        self.db.execute(
            "DELETE FROM jewelry_glyph_effect"
        )

        self.db.execute(
            "DELETE FROM jewelry_glyph"
        )

        glyph_sql = """
            INSERT INTO jewelry_glyph (
                item_id,
                name,
                icon,
                level_range,
                quality_range,
                value_range,
                enchant_name,
                enchant_description,
                glyph_min_level,
                craft_skill_rank,
                default_enchant_id,
                craft_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        glyph_values = [
            (
                row["item_id"],
                row["name"],
                row["icon"],
                row["level_range"],
                row["quality_range"],
                row["value_range"],
                row["enchant_name"],
                row["enchant_description"],
                row["glyph_min_level"],
                row["craft_skill_rank"],
                row["default_enchant_id"],
                row["craft_type"],
            )
            for row in rows
        ]

        self.db.executemany(
            glyph_sql,
            glyph_values,
        )

        effect_sql = """
            INSERT INTO jewelry_glyph_effect (
                glyph_item_id,
                effect_type,
                value_min,
                value_max,
                unit,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """

        effect_values = []

        for row in rows:

            for effect in row["effects"]:

                effect_values.append(
                    (
                        row["item_id"],
                        effect["effect_type"],
                        effect["value_min"],
                        effect["value_max"],
                        effect["unit"],
                        effect["description"],
                    )
                )

        if effect_values:

            self.db.executemany(
                effect_sql,
                effect_values,
            )

        return len(glyph_values), len(effect_values)

    # --------------------------------------------------
    # Run
    # --------------------------------------------------

    def run(self):

        rows = JewelryGlyphParser.parse(
            self.source_path
        )

        self.create_schema()

        glyph_count, effect_count = (
            self.import_glyphs(rows)
        )

        self.db.commit()

        print(
            "Jewelry glyph import complete:"
        )

        print(
            f"  Glyphs: {glyph_count}"
        )

        print(
            f"  Effects: {effect_count}"
        )