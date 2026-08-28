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

        return self._map_rows(rows, use_max_value=use_max_value)

    def get_armor_glyph_effect_by_name(
        self,
        glyph_name: str,
        *,
        use_max_value: bool = True,
    ) -> list[Effect]:
        """Return the strongest matching named glyph effects.

        The build editor currently stores a human-readable enchantment rather
        than an ESO item id. Phase 2F only calls this for explicitly max-level,
        max-tier armor glyphs, so choosing the highest recorded value for each
        effect type is deterministic and avoids pretending lower tiers are max.
        """
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
                WHERE LOWER(TRIM(g.name)) = LOWER(TRIM(?))
                ORDER BY COALESCE(e.value_max, e.value_min) DESC, e.id
                """,
                (glyph_name,),
            ).fetchall()

        # A glyph name can appear at multiple levels/qualities. Keep only the
        # strongest row for each distinct effect type for the CP160/max-tier
        # calculation path.
        strongest = []
        seen_effect_types: set[str] = set()
        for row in rows:
            effect_type = str(row[1] or "").strip().casefold()
            if effect_type in seen_effect_types:
                continue
            seen_effect_types.add(effect_type)
            strongest.append(row)
        return self._map_rows(strongest, use_max_value=use_max_value)

    @staticmethod
    def _map_rows(rows, *, use_max_value: bool) -> list[Effect]:
        effects: list[Effect] = []
        for glyph_name, effect_type, value_min, value_max, unit, description in rows:
            value = value_max if use_max_value else value_min
            if value is None:
                value = value_min if use_max_value else value_max
            if value is None:
                raise ValueError(
                    f"Armor glyph effect has no usable value: {glyph_name!r}"
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
