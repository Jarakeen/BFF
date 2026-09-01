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
_CURRENT_RESTORE_RE = re.compile(
    r"\bcurrent\s+restore\s*:\s*\$(?P<number>\d+)(?!\d)",
    re.IGNORECASE,
)
_PERCENT_RESOURCE_CONTEXT_RE = re.compile(
    r"\b(?:restore|restores|restored|restoring|gain|gains|gained|gaining)\b"
    r"[^.;]{0,60}?\d+(?:\.\d+)?\s*%\s+(?:magicka|stamina|ultimate)\b",
    re.IGNORECASE,
)
_CURRENT_HEALTH_CONTEXT_RE = re.compile(
    r"\bincreas(?:e|es|ed|ing)\s+by\s+up\s+to\s+\d+(?:\.\d+)?\s*%"
    r"[^.;]{0,100}?\bbased\s+on\s+how\s+high\s+(?:your|their)\s+current\s+health\s+is\b",
    re.IGNORECASE,
)


def _current_restore_evidence_window(text: str | None, coefficient_number: int) -> str | None:
    """Return tightly bounded defining context for ``Current Restore: $N``.

    ESO/Uesp source formatting is not guaranteed to preserve clean sentence
    boundaries around runtime-display lines. For this explicit display shape,
    inspect only a short prefix before ``Current Restore: $N`` and retain it only
    when that prefix itself proves both a named percentage resource restore and
    current-Health scaling. This avoids broad backward semantic borrowing while
    tolerating missing punctuation/newline normalization.
    """

    normalized = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
    if not normalized:
        return None

    match = next(
        (
            item
            for item in _CURRENT_RESTORE_RE.finditer(normalized)
            if int(item.group("number")) == int(coefficient_number)
        ),
        None,
    )
    if match is None:
        return None

    prefix_start = max(0, match.start() - 320)
    prefix = normalized[prefix_start:match.start()].strip()
    if not _PERCENT_RESOURCE_CONTEXT_RE.search(prefix):
        return None
    if not _CURRENT_HEALTH_CONTEXT_RE.search(prefix):
        return None

    following_period = normalized.find(".", match.end())
    suffix_end = following_period + 1 if following_period != -1 else len(normalized)
    return normalized[prefix_start:suffix_end].strip()


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
