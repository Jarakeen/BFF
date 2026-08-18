import sqlite3
from pathlib import Path

from .effect_mapper import EffectMapper
from .effects import Effect


class ArmorGlyphEffectRepository:
    """Loads armor glyph effects from the ESO database."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def get_armor_glyph_effect(
        self,
        item_id: int,
        *,
        use_max_value: bool = True,
    ) -> list[Effect]:

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    g.name,
                    e.effect_type,
                    e.value_min,
                    e.value_max,
                    e.unit,
                    e.description
                FROM armor_glyph g
                JOIN armor_glyph_effect e
                    ON e.glyph_item_id = g.item_id
                WHERE g.item_id = ?
                ORDER BY e.id
                """,
                (item_id,),
            ).fetchall()

        effects: list[Effect] = []

        for (
            glyph_name,
            effect_type,
            value_min,
            value_max,
            unit,
            description,
        ) in rows:

            value = value_max if use_max_value else value_min

            if value is None:
                raise ValueError(
                    f"Armor glyph effect has no usable value: "
                    f"{glyph_name!r}"
                )

            effects.append(
                EffectMapper.create_additive(
                    effect_type=effect_type,
                    value=float(value),
                    unit=unit,
                    source=glyph_name,
                )
            )

        return effects