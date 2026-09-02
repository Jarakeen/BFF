from __future__ import annotations

import math
import re
import sqlite3
from pathlib import Path

from .skill_component_source_alignment_issue import (
    SkillComponentSourceAlignmentIssue,
    SkillComponentSourceAlignmentIssueType,
)


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


class SkillComponentSourceAlignmentIssueRepository:
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
        return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})")}

    @staticmethod
    def _same(left: object, right: object) -> bool:
        if left is None or right is None:
            return left is right
        try:
            return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)
        except (TypeError, ValueError):
            return str(left) == str(right)

    def resolve(
        self,
        skill_rank_id: int,
        coefficient_number: int,
    ) -> tuple[SkillComponentSourceAlignmentIssue, ...]:
        if not self.database_path.exists():
            return ()

        number = int(coefficient_number)
        if number < 1 or number > 6:
            return ()

        with sqlite3.connect(self.database_path) as db:
            if not all(self._table_exists(db, name) for name in ("skill_rank", "skill_coefficient", "ability")):
                return ()
            ability_columns = self._columns(db, "ability")
            required = {
                "coef_description", "raw_description",
                f"type{number}", f"a{number}", f"b{number}", f"c{number}", f"r{number}", f"avg{number}",
            }
            if not required.issubset(ability_columns):
                return ()

            row = db.execute(
                f"""
                SELECT
                    sc.type, sc.a, sc.b, sc.c, sc.r, sc.avg,
                    a.type{number}, a.a{number}, a.b{number}, a.c{number}, a.r{number}, a.avg{number},
                    a.coef_description, a.raw_description
                FROM skill_rank sr
                JOIN skill_coefficient sc
                  ON sc.skill_rank_id = sr.id
                 AND sc.coefficient_number = ?
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE sr.id = ?
                """,
                (number, int(skill_rank_id)),
            ).fetchone()
            if row is None:
                return ()

        coefficient_type = str(row[0] or "").strip()
        # A negative non-sentinel type is a special coefficient family. We do
        # not assign semantics from that type code alone.
        if not coefficient_type.startswith("-") or coefficient_type == "-1":
            return ()

        raw_type = str(row[6] or "").strip()
        if raw_type != coefficient_type:
            return ()
        if not all(self._same(row[index], row[index + 6]) for index in range(1, 6)):
            return ()

        coef_description = str(row[12] or "")
        raw_description = str(row[13] or "")
        own_dollar = re.search(rf"\${number}(?!\d)", coef_description)
        own_raw = re.search(rf"<<\s*{number}\s*>>", raw_description)
        if own_dollar is not None or own_raw is None:
            return ()

        # Require the raw placeholder to be embedded in timing/channel prose.
        # This proves the raw ordinal is not a trustworthy visible mechanic map.
        raw_normalized = " ".join(raw_description.split())
        timing_match = re.search(
            rf"(?:every|over|for|once every)\s+<<\s*{number}\s*>>",
            raw_normalized,
            re.IGNORECASE,
        )
        if timing_match is None:
            return ()

        evidence = (
            f"active special coefficient type {coefficient_type} matches raw slot; "
            f"raw placeholder {timing_match.group(0)!r} has no corresponding ${number} in coef_description"
        )
        return (
            SkillComponentSourceAlignmentIssue(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=number,
                coefficient_type=coefficient_type,
                issue_type=SkillComponentSourceAlignmentIssueType.SPECIAL_COEFFICIENT_DISPLAY_MISMATCH,
                evidence=evidence,
            ),
        )
