from __future__ import annotations

"""Read-only repository for Phase 6 current stat-bonus display semantics."""

import re
import sqlite3
from pathlib import Path

from .skill_component_current_bonus import (
    SkillComponentCurrentBonus,
    extract_explicit_component_current_bonus,
)

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"
_COLOR_TAG_RE = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")


def _normalize(value: object) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    text = _COLOR_TAG_RE.sub("", text)
    return " ".join(text.split())


class SkillComponentCurrentBonusRepository:
    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _table_exists(db: sqlite3.Connection, name: str) -> bool:
        return db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone() is not None

    def resolve(self, skill_rank_id: int, coefficient_number: int) -> tuple[SkillComponentCurrentBonus, ...]:
        if not self.database_path.exists():
            return ()
        with sqlite3.connect(self.database_path) as db:
            if not all(self._table_exists(db, name) for name in ("skill_rank", "ability")):
                return ()
            row = db.execute(
                """
                SELECT a.coef_description
                FROM skill_rank sr
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE sr.id = ?
                """,
                (int(skill_rank_id),),
            ).fetchone()
            if row is None:
                return ()
        return extract_explicit_component_current_bonus(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            component_text=_normalize(row[0]),
        )
