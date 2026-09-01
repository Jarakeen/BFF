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


def _normalize_source_text(text: str | None) -> str:
    return " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())


def _has_current_restore(text: str | None, coefficient_number: int) -> bool:
    normalized = _normalize_source_text(text)
    return any(
        int(match.group("number")) == int(coefficient_number)
        for match in _CURRENT_RESTORE_RE.finditer(normalized)
    )


def _defining_resource_context(text: str | None) -> str | None:
    """Return explicit percent-resource + current-Health scaling context.

    This helper is source-agnostic. Coefficient ownership is established
    separately by ``coef_description`` via ``Current Restore: $N`` before
    description/raw source text is allowed to corroborate the resource
    definition.
    """

    normalized = _normalize_source_text(text)
    if not normalized:
        return None

    resource_match = _PERCENT_RESOURCE_CONTEXT_RE.search(normalized)
    health_match = _CURRENT_HEALTH_CONTEXT_RE.search(normalized)
    if resource_match is None or health_match is None:
        return None

    start = max(0, min(resource_match.start(), health_match.start()) - 80)
    end = min(len(normalized), max(resource_match.end(), health_match.end()) + 80)
    return normalized[start:end].strip()


def _current_restore_evidence_window(text: str | None, coefficient_number: int) -> str | None:
    """Return tightly bounded defining context for ``Current Restore: $N``.

    ESO/UESP source formatting is not guaranteed to preserve clean sentence
    boundaries around runtime-display lines. For this explicit display shape,
    inspect only a short prefix before ``Current Restore: $N`` and retain it only
    when that prefix itself proves both a named percentage resource restore and
    current-Health scaling. This avoids broad backward semantic borrowing while
    tolerating missing punctuation/newline normalization.
    """

    normalized = _normalize_source_text(text)
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

    @staticmethod
    def _columns(db: sqlite3.Connection, table: str) -> set[str]:
        return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})").fetchall()}

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

            ability_columns = self._columns(db, "ability")
            rank_columns = self._columns(db, "skill_rank")
            optional_selects = [
                "a.description" if "description" in ability_columns else "NULL",
                "a.raw_description" if "raw_description" in ability_columns else "NULL",
                "a.raw_tooltip" if "raw_tooltip" in ability_columns else "NULL",
                "sr.raw_description" if "raw_description" in rank_columns else "NULL",
                "sr.raw_tooltip" if "raw_tooltip" in rank_columns else "NULL",
            ]
            row = db.execute(
                f"""
                SELECT a.coef_description, {', '.join(optional_selects)}
                FROM skill_rank sr
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE sr.id = ?
                """,
                (int(skill_rank_id),),
            ).fetchone()
            if row is None:
                return ()

        coef_description = row[0]
        evidence = extract_component_text_evidence(coef_description, int(coefficient_number))
        if not evidence.fragment:
            return ()

        if _has_current_restore(coef_description, int(coefficient_number)):
            component_text = _current_restore_evidence_window(
                coef_description,
                int(coefficient_number),
            )
            if component_text is None:
                # ``coef_description`` owns the $N runtime-display component, but
                # its defining resource rule may live in the normalized ability
                # description or other raw source text. Those fields may
                # corroborate the definition; they never own the coefficient
                # number by themselves.
                for source_text in row[1:]:
                    defining = _defining_resource_context(source_text)
                    if defining is not None:
                        component_text = f"{defining} Current Restore: ${int(coefficient_number)}"
                        break
            if component_text is None:
                return ()
        else:
            component_text = evidence.fragment

        return extract_explicit_component_resource_events(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            component_text=component_text,
        )
