from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


_EFFECT_TYPE = "potion_cooldown_reduction"


@dataclass(frozen=True)
class JewelryPotionCooldownReduction:
    source: str
    seconds: float


class JewelryPotionCooldownRepository:
    """Load potion-cooldown reductions from canonical jewelry glyph data.

    Potion cadence is an event-timing mechanic, not a persistent character-sheet
    stat, so this repository deliberately bypasses EffectMapper/StatId just like
    the existing jewelry action-cost modifier repository. The jewelry glyph
    importer remains the single source of stored glyph evidence.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)

    def get_by_name(
        self,
        glyph_name: str,
        *,
        use_max_value: bool = True,
        multiplier: float = 1.0,
        source_prefix: str = "",
    ) -> tuple[JewelryPotionCooldownReduction, ...]:
        if multiplier < 0:
            raise ValueError("Jewelry potion cooldown multiplier cannot be negative")

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    g.name,
                    e.value_min,
                    e.value_max,
                    e.unit
                FROM jewelry_glyph g
                JOIN jewelry_glyph_effect e
                    ON e.glyph_item_id = g.item_id
                WHERE LOWER(TRIM(g.name)) = LOWER(TRIM(?))
                  AND LOWER(TRIM(e.effect_type)) = ?
                ORDER BY COALESCE(e.value_max, e.value_min) DESC, e.id
                """,
                (glyph_name, _EFFECT_TYPE),
            ).fetchall()

        if not rows:
            return ()

        stored_name, value_min, value_max, unit = rows[0]
        value = value_max if use_max_value else value_min
        if value is None:
            value = value_min if use_max_value else value_max
        if value is None:
            raise ValueError(
                f"Jewelry potion cooldown glyph has no usable value: {stored_name!r}"
            )

        normalized_unit = str(unit or "").strip().casefold()
        if normalized_unit != "seconds":
            raise ValueError(
                f"Unsupported jewelry potion cooldown unit: {unit!r}"
            )

        seconds = float(value) * float(multiplier)
        if seconds < 0:
            raise ValueError("Jewelry potion cooldown reduction cannot be negative")

        source = str(stored_name or glyph_name).strip()
        if source_prefix:
            source = f"{source_prefix}: {source}"
        return (JewelryPotionCooldownReduction(source=source, seconds=seconds),)


__all__ = [
    "JewelryPotionCooldownReduction",
    "JewelryPotionCooldownRepository",
]
