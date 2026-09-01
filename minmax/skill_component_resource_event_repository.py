from __future__ import annotations

"""Read-only repository for canonical Phase 6 component resource events."""

import re
import sqlite3
from pathlib import Path

from .skill_component_resource_event import (
    SkillComponentResourceEvent,
    extract_explicit_component_resource_events,
)
from .skill_component_text_evidence import extract_component_text_evidence


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"
_CURRENT_RESTORE_RE = re.compile(r"\bcurrent\s+restore\s*:\s*\$(?P<number>\d+)(?!\d)", re.IGNORECASE)


def _current_restore_evidence_window(text: str | None, coefficient_number: int) -> str | None:
    """Return the defining sentence plus ``Current Restore: $N`` sentence.

    Some ESO coefficient descriptions place the actual resource rule immediately
    before the sentence that contains the coefficient placeholder, for example
    ``restore 12% Stamina ... current Health. Current Restore: $2``. For that
    explicit display shape only, preserve the immediately preceding sentence so
    the coefficient can be linked to its stated resource basis without opening
    broad backward semantic leakage.
    """

    normalized = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
    if not normalized:
        return None

    matches = [
        match
        for match in _CURRENT_RESTORE_RE.finditer(normalized)
        if int(match.group("number")) == int(coefficient_number)
    ]
    if not matches:
        return None

    match = matches[0]
    prior_period = normalized.rfind(".", 0, match.start())
    if prior_period == -1:
        return normalized
    prior_prior_period = normalized.rfind(".", 0, prior_period)
    start = prior_prior_period + 1 if prior_prior_period != -1 else 0
    following_period = normalized.find(".", match.end())
    end = following_period + 1 if following_period != -1 else len(normalized)
    return normalized[start:end].strip()


class SkillComponentResourceEventRepository:
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
    ) -> tuple[SkillComponentResourceEvent, ...]:
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

        component_text = evidence.fragment
        current_restore_window = _current_restore_evidence_window(row[0], int(coefficient_number))
        if current_restore_window is not None:
            component_text = current_restore_window

        return extract_explicit_component_resource_events(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            component_text=component_text,
        )
