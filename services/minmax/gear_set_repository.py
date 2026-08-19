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

    def get_set(self, name: str) -> GearSet | None:
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

        if row is None:
            return None

        return self._to_gear_set(row)

    def get_set_by_id(self, set_id: int) -> GearSet | None:
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

        if row is None:
            return None

        return self._to_gear_set(row)

    def get_bonuses(self, set_id: int) -> list[GearSetBonus]:
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

        return [self._to_gear_set_bonus(row) for row in rows]

    def get_bonus(self, set_id: int, piece_count: int) -> GearSetBonus | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    set_id,
                    piece_count,
                    description
                FROM gear_set_bonus
                WHERE set_id = ? AND piece_count = ?
                ORDER BY id
                """,
                (set_id, piece_count),
            ).fetchone()

        if row is None:
            return None

        return self._to_gear_set_bonus(row)

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
