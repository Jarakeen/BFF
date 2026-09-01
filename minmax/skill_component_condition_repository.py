from __future__ import annotations

"""Read-only repository for canonical Phase 6 skill-component conditions."""

import sqlite3
from pathlib import Path

from .skill_component_condition import (
    SkillComponentCondition,
    extract_explicit_component_conditions,
)
from .skill_component_text_evidence import extract_component_text_evidence


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


class SkillComponentConditionRepository:
    """Resolve explicit coefficient-local conditions from canonical source text.

    Phase 6 records the condition identity and threshold only. It does not
    evaluate current target Health, uptime, encounter timing, or damage scaling.
    """

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
    ) -> tuple[SkillComponentCondition, ...]:
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

        evidence = extract_component_text_evidence(row[0], int(coefficient_number))
        if not evidence.fragment:
            return ()

        return extract_explicit_component_conditions(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            component_text=evidence.fragment,
        )
