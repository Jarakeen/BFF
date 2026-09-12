from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3

_COLOR_TAG_RE = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")


@dataclass(frozen=True)
class ClassMasteryPassive:
    skill_id: int
    base_ability_id: int
    name: str
    class_name: str
    description: str


class ClassMasteryRepository:
    """Read exact Class Mastery passive rows from the canonical skill table.

    This repository deliberately does not infer mechanics from prose. It gives
    later scoring layers clean canonical identities and descriptions while
    excluding unrelated rows such as the Breton racial passive Magicka Mastery.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        # Class Mastery rows are canonical reference data for the lifetime of a
        # repository instance. Cache the assembled immutable catalog so repeated
        # Extreme/runtime queries do not reopen and rescan SQLite.
        self._all_cache: tuple[ClassMasteryPassive, ...] | None = None
        self._class_cache: dict[str, tuple[ClassMasteryPassive, ...]] = {}

    @staticmethod
    def _plain_text(value: object) -> str:
        text = _COLOR_TAG_RE.sub("", str(value or ""))
        return " ".join(text.split())

    def all(self) -> tuple[ClassMasteryPassive, ...]:
        if self._all_cache is not None:
            return self._all_cache

        if not self.database_path.is_file():
            self._all_cache = ()
            return self._all_cache

        with sqlite3.connect(self.database_path) as db:
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(skill)").fetchall()}
            required = {
                "id",
                "base_ability_id",
                "name",
                "class_type",
                "skill_line",
                "description",
                "is_passive",
            }
            if not required.issubset(columns):
                self._all_cache = ()
                return self._all_cache

            rows = db.execute(
                """
                SELECT id, base_ability_id, name, class_type, description
                FROM skill
                WHERE COALESCE(is_passive, 0) = 1
                  AND LOWER(TRIM(COALESCE(skill_line, ''))) = 'class mastery'
                ORDER BY LOWER(TRIM(COALESCE(class_type, ''))), LOWER(TRIM(name)), id
                """
            ).fetchall()

        self._all_cache = tuple(
            ClassMasteryPassive(
                skill_id=int(row[0]),
                base_ability_id=int(row[1] or 0),
                name=self._plain_text(row[2]),
                class_name=self._plain_text(row[3]),
                description=self._plain_text(row[4]),
            )
            for row in rows
        )
        return self._all_cache

    def for_class(self, class_name: str) -> tuple[ClassMasteryPassive, ...]:
        target = str(class_name or "").strip().casefold()
        if not target:
            return ()

        cached = self._class_cache.get(target)
        if cached is not None:
            return cached

        result = tuple(row for row in self.all() if row.class_name.casefold() == target)
        self._class_cache[target] = result
        return result
