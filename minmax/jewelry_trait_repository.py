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

# Current CP160 trait values. These are intentionally hardcoded rather than
# read from jewelry_trait_effect because the production database contains older
# historical values for several traits (notably Protective and Triune) and no
# numeric rows for Arcane, Healthy, or Robust.
INFUSED_ENCHANTMENT_PERCENT = {
    "Normal": 24.0,
    "Fine": 33.0,
    "Superior": 42.0,
    "Epic": 51.0,
    "Legendary": 60.0,
}

STATIC_TRAIT_VALUES = {
    "arcane": {
        "Normal": ((StatId.MAX_MAGICKA, 767.0),),
        "Fine": ((StatId.MAX_MAGICKA, 797.0),),
        "Superior": ((StatId.MAX_MAGICKA, 827.0),),
        "Epic": ((StatId.MAX_MAGICKA, 847.0),),
        "Legendary": ((StatId.MAX_MAGICKA, 877.0),),
    },
    "healthy": {
        "Normal": ((StatId.MAX_HEALTH, 844.0),),
        "Fine": ((StatId.MAX_HEALTH, 877.0),),
        "Superior": ((StatId.MAX_HEALTH, 914.0),),
        "Epic": ((StatId.MAX_HEALTH, 932.0),),
        "Legendary": ((StatId.MAX_HEALTH, 965.0),),
    },
    "robust": {
        "Normal": ((StatId.MAX_STAMINA, 767.0),),
        "Fine": ((StatId.MAX_STAMINA, 797.0),),
        "Superior": ((StatId.MAX_STAMINA, 827.0),),
        "Epic": ((StatId.MAX_STAMINA, 847.0),),
        "Legendary": ((StatId.MAX_STAMINA, 877.0),),
    },
    "protective": {
        "Normal": (
            (StatId.PHYSICAL_RESISTANCE, 1053.0),
            (StatId.SPELL_RESISTANCE, 1053.0),
        ),
        "Fine": (
            (StatId.PHYSICAL_RESISTANCE, 1091.0),
            (StatId.SPELL_RESISTANCE, 1091.0),
        ),
        "Superior": (
            (StatId.PHYSICAL_RESISTANCE, 1128.0),
            (StatId.SPELL_RESISTANCE, 1128.0),
        ),
        "Epic": (
            (StatId.PHYSICAL_RESISTANCE, 1153.0),
            (StatId.SPELL_RESISTANCE, 1153.0),
        ),
        "Legendary": (
            (StatId.PHYSICAL_RESISTANCE, 1190.0),
            (StatId.SPELL_RESISTANCE, 1190.0),
        ),
    },
    "triune": {
        "Normal": (
            (StatId.MAX_HEALTH, 422.0),
            (StatId.MAX_MAGICKA, 384.0),
            (StatId.MAX_STAMINA, 384.0),
        ),
        "Fine": (
            (StatId.MAX_HEALTH, 438.0),
            (StatId.MAX_MAGICKA, 399.0),
            (StatId.MAX_STAMINA, 399.0),
        ),
        "Superior": (
            (StatId.MAX_HEALTH, 455.0),
            (StatId.MAX_MAGICKA, 414.0),
            (StatId.MAX_STAMINA, 414.0),
        ),
        "Epic": (
            (StatId.MAX_HEALTH, 466.0),
            (StatId.MAX_MAGICKA, 424.0),
            (StatId.MAX_STAMINA, 424.0),
        ),
        "Legendary": (
            (StatId.MAX_HEALTH, 482.0),
            (StatId.MAX_MAGICKA, 439.0),
            (StatId.MAX_STAMINA, 439.0),
        ),
    },
}


class JewelryTraitRepository:
    """Resolve deterministic jewelry trait rules using current game constants.

    ``database_path`` is retained for dependency-injection compatibility and
    provenance, but CP160 static trait math intentionally does not trust stale
    numeric rows in the local database.
    """

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
        return INFUSED_ENCHANTMENT_PERCENT.get(database_quality)

    def get_static_effects(self, trait_name: str, *, quality: str, level: str) -> list[Effect]:
        trait = str(trait_name or "").strip()
        database_quality = self.database_quality(quality)
        item_level = self.database_item_level(level)
        if not trait or not database_quality or item_level is None:
            return []

        rows = STATIC_TRAIT_VALUES.get(trait.casefold(), {}).get(database_quality, ())
        return [
            Effect(
                operation=EffectOperation.ADD,
                value=value,
                source=trait,
                stat=stat,
                unit=EffectUnit.FLAT,
            )
            for stat, value in rows
        ]
