from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sqlite3

from .skill_coefficient_repository import SkillCoefficientRepository


@dataclass(frozen=True)
class SkillDurationResolution:
    skill_name: str
    duration_seconds: float | None
    ability_id: int | None
    unresolved: tuple[str, ...] = ()


class SkillDurationRepository:
    """Resolve canonical rank-specific duration evidence for a named ESO ability.

    Skill identity remains owned by ``SkillCoefficientRepository``. Positive
    ``skill_rank.duration`` values are authoritative seconds when present. When
    that field is absent/non-positive, the repository falls back to the resolved
    ``ability.duration`` value, which the ESO importer preserves in milliseconds.
    No duration is inferred from names or tooltip wording.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.skills = SkillCoefficientRepository(database_path)
        self._cache: dict[str, SkillDurationResolution] = {}

    def resolve_name(self, name: str) -> SkillDurationResolution:
        requested = str(name or "").strip()
        if not requested:
            return SkillDurationResolution("", None, None, ("Skill name is required",))

        key = requested.casefold()
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        identity = self.skills.resolve_name(requested)
        if identity.rank is None:
            result = SkillDurationResolution(
                requested,
                None,
                None,
                tuple(identity.unresolved),
            )
            self._cache[key] = result
            return result

        rank = identity.rank
        if not self.database_path.exists():
            result = SkillDurationResolution(
                rank.name,
                None,
                rank.ability_id,
                tuple(identity.unresolved) + ("ESO database is unavailable",),
            )
            self._cache[key] = result
            return result

        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT duration FROM skill_rank WHERE id = ?",
                (rank.skill_rank_id,),
            ).fetchone()

            if row is None:
                result = SkillDurationResolution(
                    rank.name,
                    None,
                    rank.ability_id,
                    tuple(identity.unresolved)
                    + (f"skill_rank row not found for source ability {rank.ability_id}",),
                )
                self._cache[key] = result
                return result

            raw_duration = row[0]
            rank_duration = self._positive_number(raw_duration)
            if rank_duration is not None:
                result = SkillDurationResolution(
                    rank.name,
                    rank_duration,
                    rank.ability_id,
                    tuple(identity.unresolved),
                )
                self._cache[key] = result
                return result

            ability_duration = self._ability_duration_seconds(connection, rank.ability_id)

        if ability_duration is not None:
            result = SkillDurationResolution(
                rank.name,
                ability_duration,
                rank.ability_id,
                tuple(identity.unresolved),
            )
        else:
            result = SkillDurationResolution(
                rank.name,
                None,
                rank.ability_id,
                tuple(identity.unresolved)
                + (
                    f"{rank.name} has no positive canonical skill_rank.duration "
                    "or ability.duration",
                ),
            )

        self._cache[key] = result
        return result

    @staticmethod
    def _positive_number(value: object) -> float | None:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(number) or number <= 0:
            return None
        return number

    @classmethod
    def _ability_duration_seconds(
        cls,
        connection: sqlite3.Connection,
        ability_id: int,
    ) -> float | None:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(ability)").fetchall()
        }
        if not {"ability_id", "duration"}.issubset(columns):
            return None

        row = connection.execute(
            "SELECT duration FROM ability WHERE ability_id = ?",
            (int(ability_id),),
        ).fetchone()
        if row is None:
            return None

        milliseconds = cls._positive_number(row[0])
        if milliseconds is None:
            return None
        return milliseconds / 1000.0
