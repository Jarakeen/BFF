from __future__ import annotations

"""Read-only repository for canonical Phase 6 component trigger relationships."""

import re
import sqlite3
from pathlib import Path

from .skill_component_trigger_relationship import (
    SkillComponentTriggerRelationship,
    extract_explicit_component_trigger_relationships,
)


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"
_COLOR_TAG_RE = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")


def _normalize_source_text(value: object) -> str:
    text = _COLOR_TAG_RE.sub("", str(value or ""))
    return " ".join(text.split())


class SkillComponentTriggerRelationshipRepository:
    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _table_exists(db: sqlite3.Connection, name: str) -> bool:
        return db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone() is not None

    def resolve(
        self,
        skill_rank_id: int,
        coefficient_number: int,
    ) -> tuple[SkillComponentTriggerRelationship, ...]:
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

        text = _normalize_source_text(row[0])
        if not text:
            return ()

        return extract_explicit_component_trigger_relationships(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            component_text=text,
        )
