from __future__ import annotations

from pathlib import Path

from services.eso_database import EsoDatabase
from parsers.weapon_trait_parser import WeaponTraitParser


class WeaponTraitImporter:

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
            CREATE TABLE IF NOT EXISTS weapon_trait_effect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trait_id INTEGER NOT NULL,
                material_name TEXT NOT NULL,
                effect_type TEXT NOT NULL,
                value REAL,
                secondary_value REAL,
                unit TEXT NOT NULL,
                description TEXT,

                FOREIGN KEY(trait_id)
                    REFERENCES gear_trait_material(trait_id)
            )
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_weapon_trait_effect_trait
            ON weapon_trait_effect(trait_id)
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_weapon_trait_effect_type
            ON weapon_trait_effect(effect_type)
            """
        )

    def import_traits(
        self,
        rows: list[dict],
    ) -> tuple[int, int]:

        self.db.execute(
            "DELETE FROM weapon_trait_effect"
        )

        trait_count = 0
        effect_count = 0

        for row in rows:

            material = self.db.execute(
                """
                SELECT trait_id
                FROM gear_trait_material
                WHERE material_name = ?
                  AND gear_type = ?
                """,
                (
                    row["material_name"],
                    "Weapon",
                ),
            ).fetchone()

            if material is None:
                raise RuntimeError(
                    "Weapon trait material not found: "
                    f"{row['material_name']}"
                )

            trait_id = material[0]

            trait_count += 1

            for effect in row["effects"]:

                self.db.execute(
                    """
                    INSERT INTO weapon_trait_effect (
                        trait_id,
                        material_name,
                        effect_type,
                        value,
                        secondary_value,
                        unit,
                        description
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trait_id,
                        row["material_name"],
                        effect["effect_type"],
                        effect["value"],
                        effect["secondary_value"],
                        effect["unit"],
                        effect["description"],
                    ),
                )

                effect_count += 1

        return trait_count, effect_count

    def run(self):

        rows = WeaponTraitParser.parse(
            self.source_path
        )

        self.create_schema()

        trait_count, effect_count = (
            self.import_traits(rows)
        )

        self.db.commit()

        print(
            "Weapon trait import complete:"
        )

        print(
            f"  Traits: {trait_count}"
        )

        print(
            f"  Effects: {effect_count}"
        )
