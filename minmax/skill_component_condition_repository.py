from __future__ import annotations

"""Read-only repository for canonical Phase 6 skill-component conditions."""

import re
import sqlite3
from pathlib import Path

from .skill_component_condition import (
    SkillComponentCondition,
    explicit_ordinal_condition_owner,
    extract_explicit_component_conditions,
    extract_explicit_ordinal_component_conditions,
)
from .skill_component_text_evidence import extract_component_text_evidence


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"
_COLOR_TAG_RE = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")


def _normalize_source_text(value: object) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    text = _COLOR_TAG_RE.sub("", text)
    text = re.sub(r"\bless\s*than\b", "less than", text, flags=re.IGNORECASE)
    text = re.sub(r"\bhealth\s*drops\b", "Health drops", text, flags=re.IGNORECASE)
    return " ".join(text.split())


class SkillComponentConditionRepository:
    """Resolve explicit coefficient-local conditions from canonical source text.

    Explicit ordinal wording such as ``the second hit`` takes precedence over
    placeholder proximity when both appear in the same condition sentence.
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

        source_text = _normalize_source_text(row[0])
        ordinal_owner = explicit_ordinal_condition_owner(source_text)
        if ordinal_owner is not None:
            if ordinal_owner != int(coefficient_number):
                return ()
            return extract_explicit_ordinal_component_conditions(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                source_text=source_text,
            )

        evidence = extract_component_text_evidence(source_text, int(coefficient_number))
        if not evidence.fragment:
            return ()

        return extract_explicit_component_conditions(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            component_text=evidence.fragment,
        )
