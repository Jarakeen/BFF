from __future__ import annotations

"""Read-only repository for canonical Phase 6 conditional consequences."""

import re
import sqlite3
from pathlib import Path

from .skill_component_condition import explicit_ordinal_condition_owner
from .skill_component_condition_repository import SkillComponentConditionRepository
from .skill_component_conditional_consequence import (
    SkillComponentConditionalConsequence,
    extract_explicit_conditional_consequences,
)
from .skill_component_text_evidence import extract_component_text_evidence


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


def _normalize_source_text(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"\|c[0-9a-fA-F]{6}|\|r", "", text)
    text = re.sub(r"(?i)\bless\s*than\b", "less than", text)
    return " ".join(text.split())


def _ordinal_condition_sentence(source_text: str) -> str:
    for sentence in re.split(r"(?<=[.;])\s+", source_text):
        lower = sentence.casefold()
        if any(token in lower for token in ("first hit", "second hit", "third hit", "fourth hit", "fifth hit", "sixth hit", "first attack", "second attack", "third attack")) and "health" in lower:
            return sentence
    return ""


class SkillComponentConditionalConsequenceRepository:
    """Resolve what an explicit component condition does, without evaluating it."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)
        self.conditions = SkillComponentConditionRepository(self.database_path)

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
    ) -> tuple[SkillComponentConditionalConsequence, ...]:
        conditions = self.conditions.resolve(skill_rank_id, coefficient_number)
        if not conditions or not self.database_path.exists():
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
        evidence = extract_component_text_evidence(source_text, int(coefficient_number))
        if not evidence.fragment:
            return ()

        consequence_text = evidence.fragment
        if explicit_ordinal_condition_owner(source_text) == int(coefficient_number):
            ordinal_sentence = _ordinal_condition_sentence(source_text)
            if ordinal_sentence:
                consequence_text = ordinal_sentence

        results: list[SkillComponentConditionalConsequence] = []
        for condition in conditions:
            results.extend(
                extract_explicit_conditional_consequences(
                    skill_rank_id=int(skill_rank_id),
                    coefficient_number=int(coefficient_number),
                    condition=condition,
                    component_text=consequence_text,
                    effect_kind=evidence.effect_kind,
                )
            )
        return tuple(results)
