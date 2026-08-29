import sqlite3
from pathlib import Path


QUALITY_TO_DATABASE = {
    "white": "Normal",
    "green": "Fine",
    "blue": "Superior",
    "purple": "Epic",
    "gold": "Legendary",
    "normal": "Normal",
    "fine": "Fine",
    "superior": "Superior",
    "epic": "Epic",
    "legendary": "Legendary",
}


class JewelryTraitRepository:
    """Load deterministic jewelry trait rules from the ESO database."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    @staticmethod
    def database_quality(saved_quality: str) -> str:
        value = str(saved_quality or "").strip()
        return QUALITY_TO_DATABASE.get(value.casefold(), value)

    def get_infused_enchantment_percent(self, quality: str) -> float | None:
        database_quality = self.database_quality(quality)
        if not database_quality:
            return None

        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT value, unit
                FROM jewelry_trait_effect
                WHERE LOWER(TRIM(trait_name)) = 'infused'
                  AND LOWER(TRIM(effect_type)) = 'enchantment_effect'
                  AND LOWER(TRIM(item_type)) = 'jewelry'
                  AND LOWER(TRIM(quality)) = LOWER(TRIM(?))
                ORDER BY id
                LIMIT 1
                """,
                (database_quality,),
            ).fetchone()

        if row is None:
            return None

        value, unit = row
        if value is None:
            return None
        if str(unit or "").strip().casefold() != "percent":
            raise ValueError(f"Infused jewelry rule has unsupported unit: {unit!r}")
        return float(value)
