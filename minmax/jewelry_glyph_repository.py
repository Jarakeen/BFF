import sqlite3
from pathlib import Path

from .effect_mapper import EffectMapper
from .effects import Effect


class JewelryGlyphEffectRepository:
    """Loads jewelry glyph effects from the ESO database."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._names_cache: tuple[str, ...] | None = None
        self._effect_types_cache: dict[str, tuple[str, ...]] = {}
        self._descriptions_cache: dict[str, tuple[str, ...]] = {}
        self._item_cache: dict[tuple[int, bool], tuple[Effect, ...]] = {}
        self._name_cache: dict[tuple[str, bool], tuple[Effect, ...]] = {}
        self._strongest_type_cache: dict[tuple[str, bool], tuple[Effect, ...]] = {}

    @staticmethod
    def _name_key(value: str) -> str:
        return str(value or "").strip().casefold()

    def list_names(self) -> tuple[str, ...]:
        """Return every distinct canonical jewelry-glyph name."""
        if self._names_cache is not None:
            return self._names_cache

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT name
                FROM jewelry_glyph
                WHERE name IS NOT NULL AND TRIM(name) <> ''
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()
        self._names_cache = tuple(str(row[0]) for row in rows)
        return self._names_cache

    def get_jewelry_glyph_effect_types_by_name(self, glyph_name: str) -> tuple[str, ...]:
        """Return canonical semantic effect identities for one named jewelry glyph.

        This is intentionally narrower than mapped engine ``Effect`` resolution.
        Some legitimate jewelry mechanics, such as block-cost reduction or potion
        duration, are not core-stat identities. Coverage/audit callers can inspect
        the semantic source identity without forcing every ESO mechanic through
        ``EffectMapper`` merely to prove it is unrelated to their objective.
        """
        key = self._name_key(glyph_name)
        cached = self._effect_types_cache.get(key)
        if cached is not None:
            return cached

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT LOWER(TRIM(e.effect_type))
                FROM jewelry_glyph g
                JOIN jewelry_glyph_effect e
                    ON e.glyph_item_id = g.item_id
                WHERE LOWER(TRIM(g.name)) = LOWER(TRIM(?))
                  AND e.effect_type IS NOT NULL
                  AND TRIM(e.effect_type) <> ''
                ORDER BY LOWER(TRIM(e.effect_type))
                """,
                (glyph_name,),
            ).fetchall()
        result = tuple(str(row[0]) for row in rows)
        self._effect_types_cache[key] = result
        return result

    def get_jewelry_glyph_descriptions_by_name(self, glyph_name: str) -> tuple[str, ...]:
        """Return stored canonical descriptions for one named jewelry glyph.

        Descriptions are source evidence, not mechanic identity. They are exposed
        so proof/audit layers can conservatively classify a legacy corpus row whose
        semantic effect table is sparse without mutating the database or inventing
        an engine stat mapping.
        """
        key = self._name_key(glyph_name)
        cached = self._descriptions_cache.get(key)
        if cached is not None:
            return cached

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT enchant_description
                FROM jewelry_glyph
                WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
                  AND enchant_description IS NOT NULL
                  AND TRIM(enchant_description) <> ''
                ORDER BY enchant_description
                """,
                (glyph_name,),
            ).fetchall()
        result = tuple(
            str(row[0]).strip()
            for row in rows
            if str(row[0] or "").strip()
        )
        self._descriptions_cache[key] = result
        return result

    def get_jewelry_glyph_effect(
        self,
        item_id: int,
        *,
        use_max_value: bool = True,
    ) -> list[Effect]:
        cache_key = (int(item_id), bool(use_max_value))
        cached = self._item_cache.get(cache_key)
        if cached is not None:
            return list(cached)

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
                FROM jewelry_glyph g
                JOIN jewelry_glyph_effect e
                    ON e.glyph_item_id = g.item_id
                WHERE g.item_id = ?
                ORDER BY e.id
                """,
                (item_id,),
            ).fetchall()

        result = tuple(self._map_rows(rows, use_max_value=use_max_value))
        self._item_cache[cache_key] = result
        return list(result)

    def get_jewelry_glyph_effect_by_name(
        self,
        glyph_name: str,
        *,
        use_max_value: bool = True,
    ) -> list[Effect]:
        """Return the strongest matching effects for a saved glyph name.

        PlayerBuild currently stores human-readable enchantment names rather
        than ESO item ids. The deterministic max-level path therefore chooses
        the strongest recorded row for each effect type, mirroring the armor
        glyph repository while preserving multi-effect jewelry glyphs.
        """
        cache_key = (self._name_key(glyph_name), bool(use_max_value))
        cached = self._name_cache.get(cache_key)
        if cached is not None:
            return list(cached)

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
                FROM jewelry_glyph g
                JOIN jewelry_glyph_effect e
                    ON e.glyph_item_id = g.item_id
                WHERE LOWER(TRIM(g.name)) = LOWER(TRIM(?))
                ORDER BY COALESCE(e.value_max, e.value_min) DESC, e.id
                """,
                (glyph_name,),
            ).fetchall()

        strongest = []
        seen_effect_types: set[str] = set()
        for row in rows:
            effect_type = str(row[1] or "").strip().casefold()
            if effect_type in seen_effect_types:
                continue
            seen_effect_types.add(effect_type)
            strongest.append(row)

        result = tuple(self._map_rows(strongest, use_max_value=use_max_value))
        self._name_cache[cache_key] = result
        return list(result)

    def get_strongest_jewelry_glyph_effect_by_type(
        self,
        effect_type: str,
        *,
        use_max_value: bool = True,
    ) -> list[Effect]:
        """Return the strongest canonical jewelry-glyph row for one effect type.

        This supports objective-specific mechanics whose saved-build label is
        simpler than the mined glyph name. Extreme/MOST Bash uses it for the
        canonical ``bash_damage`` item channel without adding a second source of
        glyph truth or guessing a display-name mapping.
        """
        normalized = str(effect_type or "").strip().casefold()
        if not normalized:
            return []

        cache_key = (normalized, bool(use_max_value))
        cached = self._strongest_type_cache.get(cache_key)
        if cached is not None:
            return list(cached)

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
                FROM jewelry_glyph g
                JOIN jewelry_glyph_effect e
                    ON e.glyph_item_id = g.item_id
                WHERE LOWER(TRIM(e.effect_type)) = ?
                ORDER BY COALESCE(e.value_max, e.value_min) DESC, e.id
                LIMIT 1
                """,
                (normalized,),
            ).fetchall()

        result = tuple(self._map_rows(rows, use_max_value=use_max_value))
        self._strongest_type_cache[cache_key] = result
        return list(result)

    @staticmethod
    def _map_rows(rows, *, use_max_value: bool) -> list[Effect]:
        effects: list[Effect] = []
        for glyph_name, effect_type, value_min, value_max, unit, description in rows:
            value = value_max if use_max_value else value_min
            if value is None:
                value = value_min if use_max_value else value_max
            if value is None:
                raise ValueError(
                    f"Jewelry glyph effect has no usable value: {glyph_name!r}"
                )

            effects.extend(
                EffectMapper.create_additives(
                    effect_type=effect_type,
                    value=float(value),
                    unit=unit,
                    source=glyph_name,
                )
            )

        return effects
