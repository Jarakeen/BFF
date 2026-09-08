from __future__ import annotations

"""Resolve the One Hand and Shield Deadly Bash passive for Extreme/MOST Bashy.

Deadly Bash owns two standard-Bash formula channels when a legal One Hand and
Shield configuration is active:

* the flat pre-multiplier ``Skill2.BashDamage`` contribution; and
* the multiplicative ``Skill.BashCost`` reduction.

The character's recorded passive rank is resolved against the exact canonical
rank tooltip in ``eso.db``. Unknown progression or unrecognized tooltip wording
remains an explicit blocker rather than granting a max-rank passive implicitly.
"""

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from minmax.character_progression import CharacterProgression

_COLOR = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
_NUMBER = r"([0-9]+(?:\.[0-9]+)?)"


@dataclass(frozen=True)
class ExtremeDeadlyBashResult:
    passive_name: str
    rank: int | None
    skill2_bash_damage: float | None
    skill_bash_cost: float | None
    source_description: str = ""
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved and self.skill2_bash_damage is not None and self.skill_bash_cost is not None


class ExtremeDeadlyBashService:
    PASSIVE_NAME = "Deadly Bash"

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(_COLOR.sub("", str(value or "")).split())

    def _description_for_rank(self, rank: int) -> str | None:
        if not self.database_path.exists():
            return None
        with sqlite3.connect(self.database_path) as db:
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(skill_rank)").fetchall()}
            ability_columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ability)").fetchall()}
            skill_columns = {str(row[1]) for row in db.execute("PRAGMA table_info(skill)").fetchall()}
            if not {"skill_id", "ability_id", "rank"}.issubset(columns):
                return None
            if not {"ability_id", "description"}.issubset(ability_columns):
                return None
            if not {"id", "name", "is_passive"}.issubset(skill_columns):
                return None
            row = db.execute(
                """
                SELECT COALESCE(NULLIF(sr.raw_description, ''), NULLIF(a.description, ''), s.description)
                FROM skill s
                JOIN skill_rank sr ON sr.skill_id = s.id
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE COALESCE(s.is_passive, 0) = 1
                  AND LOWER(TRIM(s.name)) = LOWER(TRIM(?))
                  AND sr.rank = ?
                ORDER BY sr.id
                LIMIT 1
                """
                if "raw_description" in columns and "description" in skill_columns
                else """
                SELECT a.description
                FROM skill s
                JOIN skill_rank sr ON sr.skill_id = s.id
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE COALESCE(s.is_passive, 0) = 1
                  AND LOWER(TRIM(s.name)) = LOWER(TRIM(?))
                  AND sr.rank = ?
                ORDER BY sr.rowid
                LIMIT 1
                """,
                (self.PASSIVE_NAME, int(rank)),
            ).fetchone()
        if row is None:
            return None
        value = self._clean(row[0])
        return value or None

    @classmethod
    def _parse(cls, description: str) -> tuple[float | None, float | None]:
        clean = cls._clean(description)
        match = re.search(
            rf"(?:causing them to )?deal\s+{_NUMBER}\s+more damage\s+and\s+cost\s+{_NUMBER}%\s+less Stamina",
            clean,
            flags=re.IGNORECASE,
        )
        if not match:
            return None, None
        damage = float(match.group(1))
        cost_reduction = float(match.group(2)) / 100.0
        return damage, -cost_reduction

    def resolve(self, progression: CharacterProgression) -> ExtremeDeadlyBashResult:
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeDeadlyBashResult(
                passive_name=self.PASSIVE_NAME,
                rank=None,
                skill2_bash_damage=None,
                skill_bash_cost=None,
                unresolved=("Passive rank is not recorded for character: Deadly Bash",),
            )
        if rank <= 0:
            return ExtremeDeadlyBashResult(
                passive_name=self.PASSIVE_NAME,
                rank=rank,
                skill2_bash_damage=0.0,
                skill_bash_cost=0.0,
            )

        description = self._description_for_rank(rank)
        if not description:
            return ExtremeDeadlyBashResult(
                passive_name=self.PASSIVE_NAME,
                rank=rank,
                skill2_bash_damage=None,
                skill_bash_cost=None,
                unresolved=(f"Canonical Deadly Bash rank not found: {rank}",),
            )

        damage, cost = self._parse(description)
        if damage is None or cost is None:
            return ExtremeDeadlyBashResult(
                passive_name=self.PASSIVE_NAME,
                rank=rank,
                skill2_bash_damage=None,
                skill_bash_cost=None,
                source_description=description,
                unresolved=(f"Unrecognized Deadly Bash tooltip: {description}",),
            )

        return ExtremeDeadlyBashResult(
            passive_name=self.PASSIVE_NAME,
            rank=rank,
            skill2_bash_damage=damage,
            skill_bash_cost=cost,
            source_description=description,
        )
