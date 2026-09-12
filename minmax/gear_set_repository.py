import sqlite3
from pathlib import Path

from .gear_sets import GearSet, GearSetBonus


class GearSetRepository:
    """Read-only data access for gear sets and their piece-count bonuses.

    This layer only exposes the `gear_set` / `gear_set_bonus` tables as-is.
    It does not resolve bonus descriptions into `Effect` objects and does not
    parse or normalize description text. That interpretation happens in a
    later layer.
    """

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._set_name_cache: dict[str, GearSet | None] = {}
        self._set_id_cache: dict[int, GearSet | None] = {}
        self._bonuses_cache: dict[int, tuple[GearSetBonus, ...]] = {}
        self._all_sets_cache: tuple[GearSet, ...] | None = None

    def list_sets(self) -> tuple[GearSet, ...]:
        """Return every canonical gear set in deterministic name/id order."""

        if self._all_sets_cache is not None:
            return self._all_sets_cache

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    name,
                    category,
                    max_equip_count
                FROM gear_set
                WHERE name IS NOT NULL
                  AND TRIM(name) <> ''
                ORDER BY name COLLATE NOCASE, id
                """
            ).fetchall()

        sets = tuple(self._to_gear_set(row) for row in rows)
        self._all_sets_cache = sets
        for gear_set in sets:
            self._set_id_cache[gear_set.id] = gear_set
            self._set_name_cache[gear_set.name] = gear_set
        return sets

    def get_set(self, name: str) -> GearSet | None:
        cache_key = str(name)
        if cache_key in self._set_name_cache:
            return self._set_name_cache[cache_key]

        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    name,
                    category,
                    max_equip_count
                FROM gear_set
                WHERE name = ?
                """,
                (name,),
            ).fetchone()

        result = None if row is None else self._to_gear_set(row)
        self._set_name_cache[cache_key] = result
        if result is not None:
            self._set_id_cache[result.id] = result
        return result

    def get_set_by_id(self, set_id: int) -> GearSet | None:
        cache_key = int(set_id)
        if cache_key in self._set_id_cache:
            return self._set_id_cache[cache_key]

        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    name,
                    category,
                    max_equip_count
                FROM gear_set
                WHERE id = ?
                """,
                (set_id,),
            ).fetchone()

        result = None if row is None else self._to_gear_set(row)
        self._set_id_cache[cache_key] = result
        if result is not None:
            self._set_name_cache[result.name] = result
        return result

    def get_bonuses(self, set_id: int) -> list[GearSetBonus]:
        cache_key = int(set_id)
        if cache_key in self._bonuses_cache:
            return list(self._bonuses_cache[cache_key])

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    set_id,
                    piece_count,
                    description
                FROM gear_set_bonus
                WHERE set_id = ?
                ORDER BY piece_count, id
                """,
                (set_id,),
            ).fetchall()

        bonuses = tuple(self._to_gear_set_bonus(row) for row in rows)
        self._bonuses_cache[cache_key] = bonuses
        return list(bonuses)

    def get_bonus(self, set_id: int, piece_count: int) -> GearSetBonus | None:
        """Return the first deterministic bonus for one piece count.

        Reuse ``get_bonuses`` so callers share the repository's existing
        instance-scoped cache instead of reopening SQLite for every focused
        bonus lookup.
        """
        target_piece_count = int(piece_count)
        for bonus in self.get_bonuses(set_id):
            if int(bonus.piece_count) == target_piece_count:
                return bonus
        return None

    @staticmethod
    def _to_gear_set(row) -> GearSet:
        set_id, name, category, max_equip_count = row

        return GearSet(
            id=set_id,
            name=name,
            category=category,
            max_equip_count=max_equip_count,
        )

    @staticmethod
    def _to_gear_set_bonus(row) -> GearSetBonus:
        bonus_id, set_id, piece_count, description = row

        return GearSetBonus(
            id=bonus_id,
            set_id=set_id,
            piece_count=piece_count,
            description=description,
        )
