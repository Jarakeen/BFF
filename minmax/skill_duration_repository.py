from __future__ import annotations

from dataclasses import dataclass
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

    Skill identity remains owned by ``SkillCoefficientRepository``. This repository
    only reads the resolved ``skill_rank.duration`` field and never infers duration
    from names or tooltip text.
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
        else:
            raw_duration = row[0]
            if raw_duration is None or float(raw_duration) <= 0:
                result = SkillDurationResolution(
                    rank.name,
                    None,
                    rank.ability_id,
                    tuple(identity.unresolved)
                    + (f"{rank.name} has no positive canonical skill_rank.duration",),
                )
            else:
                result = SkillDurationResolution(
                    rank.name,
                    float(raw_duration),
                    rank.ability_id,
                    tuple(identity.unresolved),
                )

        self._cache[key] = result
        return result
