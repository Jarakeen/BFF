import sqlite3
from pathlib import Path

from .effects import Effect, EffectOperation, EffectUnit
from .stat_ids import StatId


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

MAX_LEVEL_TO_DATABASE = {
    "cp160": 150,
}

STATIC_EFFECT_TYPES = {
    "max_health": (StatId.MAX_HEALTH,),
    "max_magicka": (StatId.MAX_MAGICKA,),
    "max_stamina": (StatId.MAX_STAMINA,),
    "physical_spell_resistance": (
        StatId.PHYSICAL_RESISTANCE,
        StatId.SPELL_RESISTANCE,
    ),
}


class JewelryTraitRepository:
    """Load deterministic jewelry trait rules from the ESO database."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    @staticmethod
    def database_quality(saved_quality: str) -> str:
        value = str(saved_quality or "").strip()
        return QUALITY_TO_DATABASE.get(value.casefold(), value)

    @staticmethod
    def database_item_level(saved_level: str) -> int | None:
        return MAX_LEVEL_TO_DATABASE.get(str(saved_level or "").strip().casefold())

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

    def get_static_effects(self, trait_name: str, *, quality: str, level: str) -> list[Effect]:
        trait = str(trait_name or "").strip()
        database_quality = self.database_quality(quality)
        item_level = self.database_item_level(level)
        if not trait or not database_quality or item_level is None:
            return []

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT effect_type, value, unit
                FROM jewelry_trait_effect
                WHERE LOWER(TRIM(trait_name)) = LOWER(TRIM(?))
                  AND LOWER(TRIM(quality)) = LOWER(TRIM(?))
                  AND item_level = ?
                ORDER BY id
                """,
                (trait, database_quality, item_level),
            ).fetchall()

        effects: list[Effect] = []
        for effect_type, value, unit in rows:
            key = str(effect_type or "").strip().casefold()
            stats = STATIC_EFFECT_TYPES.get(key)
            if stats is None:
                continue
            if str(unit or "").strip().casefold() != "flat":
                raise ValueError(
                    f"Static jewelry trait {trait!r} has unsupported unit: {unit!r}"
                )
            for stat in stats:
                effects.append(
                    Effect(
                        operation=EffectOperation.ADD,
                        value=float(value),
                        source=trait,
                        stat=stat,
                        unit=EffectUnit.FLAT,
                    )
                )
        return effects
