# ==================================================
# Black Feather Foundry
#
# File:
# importers/gear_customization_importer.py
#
# Purpose:
# Import gear traits, trait materials, glyphs, and
# enchantments from UESP reference JSON.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from services.eso_database import EsoDatabase

from parsers.gear_customization_parser import (
    GearCustomizationParser,
)


class GearCustomizationImporter:

    def __init__(
        self,
        db: EsoDatabase,
        raw_dir: Path,
    ):

        self.db = db
        self.raw_dir = raw_dir

    # --------------------------------------------------
    # Schema
    # --------------------------------------------------

    def create_schema(self):

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS gear_trait_material (
                material_item_id INTEGER PRIMARY KEY,
                trait_id INTEGER NOT NULL,
                gear_type TEXT NOT NULL,
                material_name TEXT NOT NULL,
                material_icon TEXT,
                description TEXT
            )
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_gear_trait_material_trait
            ON gear_trait_material(trait_id)
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_gear_trait_material_type
            ON gear_trait_material(gear_type)
            """
        )

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS gear_glyph (
                item_id INTEGER PRIMARY KEY,
                gear_type TEXT NOT NULL,
                name TEXT NOT NULL,
                icon TEXT,
                enchant_name TEXT NOT NULL,
                enchant_description TEXT,
                default_enchant_id INTEGER,
                level_range TEXT,
                quality_range TEXT
            )
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_gear_glyph_enchant
            ON gear_glyph(default_enchant_id)
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_gear_glyph_type
            ON gear_glyph(gear_type)
            """
        )

    # --------------------------------------------------
    # Traits
    # --------------------------------------------------

    def import_traits(
        self,
        rows: list[dict],
    ) -> int:

        sql = """
            INSERT INTO gear_trait_material (
                material_item_id,
                trait_id,
                gear_type,
                material_name,
                material_icon,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(material_item_id)
            DO UPDATE SET
                trait_id = excluded.trait_id,
                gear_type = excluded.gear_type,
                material_name = excluded.material_name,
                material_icon = excluded.material_icon,
                description = excluded.description
        """

        values = [
            (
                row["material_item_id"],
                row["trait_id"],
                row["gear_type"],
                row["material_name"],
                row["material_icon"],
                row["description"],
            )
            for row in rows
        ]

        if values:
            self.db.executemany(
                sql,
                values,
            )

        return len(values)

    # --------------------------------------------------
    # Glyphs
    # --------------------------------------------------

    def import_glyphs(
        self,
        rows: list[dict],
    ) -> int:

        sql = """
            INSERT INTO gear_glyph (
                item_id,
                gear_type,
                name,
                icon,
                enchant_name,
                enchant_description,
                default_enchant_id,
                level_range,
                quality_range
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(item_id)
            DO UPDATE SET
                gear_type = excluded.gear_type,
                name = excluded.name,
                icon = excluded.icon,
                enchant_name = excluded.enchant_name,
                enchant_description =
                    excluded.enchant_description,
                default_enchant_id =
                    excluded.default_enchant_id,
                level_range =
                    excluded.level_range,
                quality_range =
                    excluded.quality_range
        """

        values = [
            (
                row["item_id"],
                row["gear_type"],
                row["name"],
                row["icon"],
                row["enchant_name"],
                row["enchant_description"],
                row["default_enchant_id"],
                row["level_range"],
                row["quality_range"],
            )
            for row in rows
        ]

        if values:
            self.db.executemany(
                sql,
                values,
            )

        return len(values)

    # --------------------------------------------------
    # Run
    # --------------------------------------------------

    def run(self):

        data = (
            GearCustomizationParser.parse_all(
                self.raw_dir
            )
        )

        self.create_schema()

        trait_count = self.import_traits(
            data["traits"]
        )

        glyph_count = self.import_glyphs(
            data["glyphs"]
        )

        self.db.commit()

        print(
            f"Gear customization import complete:"
        )

        print(
            f"  Trait materials: {trait_count}"
        )

        print(
            f"  Glyphs/enchantments: {glyph_count}"
        )