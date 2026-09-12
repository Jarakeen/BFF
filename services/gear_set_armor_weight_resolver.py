from __future__ import annotations

import sqlite3
from pathlib import Path


_ARMOR_WEIGHT_LABELS = {
    1: "Light",
    2: "Medium",
    3: "Heavy",
}


class GearSetArmorWeightResolver:
    """Resolve a set's armor weight only when canonical data is unambiguous."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._cache: dict[str, str | None] = {}

    def resolve(self, set_name: str) -> str | None:
        name = " ".join(str(set_name or "").strip().split())
        key = name.casefold()
        if not key:
            return None
        if key in self._cache:
            return self._cache[key]

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT gsp.armor_type
                FROM gear_set gs
                JOIN gear_set_piece gsp ON gsp.set_id = gs.id
                WHERE gs.name = ?
                  AND gsp.armor_type IN (1, 2, 3)
                ORDER BY gsp.armor_type
                """,
                (name,),
            ).fetchall()

        armor_types = {
            int(row[0])
            for row in rows
            if row[0] is not None and int(row[0]) in _ARMOR_WEIGHT_LABELS
        }
        result = _ARMOR_WEIGHT_LABELS[next(iter(armor_types))] if len(armor_types) == 1 else None
        self._cache[key] = result
        return result
