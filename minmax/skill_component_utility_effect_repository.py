from __future__ import annotations

"""Read-only repository for canonical Phase 6 component utility effects."""

import re
import sqlite3
from pathlib import Path

from .skill_component_text_evidence import extract_component_text_evidence
from .skill_component_utility_effect import (
    SkillComponentUtilityEffect,
    extract_explicit_component_utility_effects,
)


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"
_ANY_PLACEHOLDER_RE = re.compile(r"\$(\d+)(?!\d)")
_ORDINAL_CLAUSE_RE = re.compile(
    r"(?:^|,\s*)(?:and\s+)?(?:their|the)\s+"
    r"(?:first|second|third|fourth|fifth|sixth)\s+(?:attack|hit)\b",
    re.IGNORECASE,
)


def _ordinal_component_segment(fragment: str, coefficient_number: int) -> str | None:
    """Return an explicit ordinal attack/hit clause that owns ``$N``.

    Multi-stage tooltips such as Unstable Core put the utility wording before
    each coefficient placeholder. Placeholder-to-placeholder slicing therefore
    leaks the next stage's utility backward. Explicit ordinal clauses are a
    stronger ownership signal, so use them when present.
    """

    text = " ".join(str(fragment or "").split())
    clauses = list(_ORDINAL_CLAUSE_RE.finditer(text))
    if not clauses:
        return None

    placeholder = re.compile(rf"\${int(coefficient_number)}(?!\d)")
    for index, match in enumerate(clauses):
        start = match.start()
        if text[start:start + 1] == ",":
            start += 1
        end = clauses[index + 1].start() if index + 1 < len(clauses) else len(text)
        clause = text[start:end].strip(" ,")
        if placeholder.search(clause):
            return clause
    return None


def _owned_component_segment(fragment: str, coefficient_number: int) -> str:
    """Return the coefficient-owned segment without borrowing adjacent utility prose."""

    ordinal = _ordinal_component_segment(fragment, coefficient_number)
    if ordinal is not None:
        return ordinal

    text = " ".join(str(fragment or "").split())
    placeholders = list(_ANY_PLACEHOLDER_RE.finditer(text))
    current_index = next(
        (
            index
            for index, match in enumerate(placeholders)
            if int(match.group(1)) == int(coefficient_number)
        ),
        None,
    )
    if current_index is None:
        return ""

    start = 0 if current_index == 0 else placeholders[current_index - 1].end()
    end = len(text) if current_index + 1 >= len(placeholders) else placeholders[current_index + 1].start()
    return text[start:end].strip()


class SkillComponentUtilityEffectRepository:
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
    ) -> tuple[SkillComponentUtilityEffect, ...]:
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

        component_text = _owned_component_segment(evidence.fragment, int(coefficient_number))
        if not component_text:
            return ()

        return extract_explicit_component_utility_effects(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            component_text=component_text,
        )
