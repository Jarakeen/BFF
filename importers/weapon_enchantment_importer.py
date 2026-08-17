from __future__ import annotations

from pathlib import Path

from services.eso_database import EsoDatabase
from parsers.weapon_enchantment_parser import (
    WeaponEnchantmentParser,
)


class WeaponEnchantmentImporter:

    def __init__(
        self,
        db: EsoDatabase,
        source_path: Path,
    ):
        self.db = db
        self.source_path = source_path

    def create_schema(self):

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS weapon_enchantment (
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
            CREATE TABLE IF NOT EXISTS weapon_enchantment_effect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enchantment_item_id INTEGER NOT NULL,
                effect_type TEXT NOT NULL,
                damage_type TEXT,
                target TEXT,
                value_min REAL,
                value_max REAL,
                unit TEXT NOT NULL,
                duration_value REAL,
                duration_unit TEXT,
                scaling_type TEXT,
                description TEXT,

                FOREIGN KEY(enchantment_item_id)
                    REFERENCES weapon_enchantment(item_id)
            )
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_weapon_enchantment_effect_enchantment
            ON weapon_enchantment_effect(
                enchantment_item_id
            )
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_weapon_enchantment_effect_type
            ON weapon_enchantment_effect(
                effect_type
            )
            """
        )

    def import_enchantments(
        self,
        rows: list[dict],
    ) -> tuple[int, int]:

        self.db.execute(
            "DELETE FROM weapon_enchantment_effect"
        )

        self.db.execute(
            "DELETE FROM weapon_enchantment"
        )

        enchantment_sql = """
            INSERT INTO weapon_enchantment (
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

        enchantment_values = [
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
            enchantment_sql,
            enchantment_values,
        )

        effect_sql = """
            INSERT INTO weapon_enchantment_effect (
                enchantment_item_id,
                effect_type,
                damage_type,
                target,
                value_min,
                value_max,
                unit,
                duration_value,
                duration_unit,
                scaling_type,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        effect_values = []

        for row in rows:

            for effect in row["effects"]:

                effect_values.append(
                    (
                        row["item_id"],
                        effect["effect_type"],
                        effect["damage_type"],
                        effect["target"],
                        effect["value_min"],
                        effect["value_max"],
                        effect["unit"],
                        effect["duration_value"],
                        effect["duration_unit"],
                        effect["scaling_type"],
                        effect["description"],
                    )
                )

        if effect_values:
            self.db.executemany(
                effect_sql,
                effect_values,
            )

        return (
            len(enchantment_values),
            len(effect_values),
        )

    def run(self):

        rows = WeaponEnchantmentParser.parse(
            self.source_path
        )

        self.create_schema()

        enchantment_count, effect_count = (
            self.import_enchantments(rows)
        )

        self.db.commit()

        print(
            "Weapon enchantment import complete:"
        )

        print(
            f"  Enchantments: {enchantment_count}"
        )

        print(
            f"  Effects: {effect_count}"
        )
