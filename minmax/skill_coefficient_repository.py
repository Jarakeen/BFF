from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .skill_coefficients import SkillCoefficient


@dataclass(frozen=True)
class ResolvedSkillRank:
    skill_rank_id: int
    skill_id: int
    ability_id: int
    base_ability_id: int
    name: str
    rank: int
    morph: int
    coefficients: tuple[SkillCoefficient, ...]


@dataclass(frozen=True)
class SkillRankResolution:
    rank: ResolvedSkillRank | None
    unresolved: tuple[str, ...] = ()


class SkillCoefficientRepository:
    """Resolve concrete skill ranks and coefficient rows from eso.db."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone()
        return row is not None

    def get_for_skill_rank(self, skill_rank_id: int) -> tuple[SkillCoefficient, ...]:
        with self._connect() as connection:
            if not self._table_exists(connection, "skill_coefficient"):
                return ()
            rows = connection.execute(
                """
                SELECT coefficient_number, type, a, b, c, r, avg
                FROM skill_coefficient
                WHERE skill_rank_id = ?
                ORDER BY coefficient_number
                """,
                (int(skill_rank_id),),
            ).fetchall()

        return tuple(
            SkillCoefficient(
                coefficient_number=int(row["coefficient_number"]),
                type=str(row["type"] or ""),
                a=float(row["a"] or 0.0),
                b=float(row["b"] or 0.0),
                c=float(row["c"] or 0.0),
                r=float(row["r"] if row["r"] is not None else 1.0),
                avg=float(row["avg"]) if row["avg"] is not None else None,
            )
            for row in rows
        )

    def resolve_ability_id(self, ability_id: int) -> SkillRankResolution:
        with self._connect() as connection:
            if not self._table_exists(connection, "skill_rank"):
                return SkillRankResolution(None, ("skill_rank table is unavailable",))
            row = connection.execute(
                """
                SELECT
                    sr.id AS skill_rank_id,
                    sr.skill_id,
                    sr.ability_id,
                    s.base_ability_id,
                    COALESCE(NULLIF(a.name, ''), NULLIF(sr.raw_name, ''), s.name, '') AS name,
                    COALESCE(sr.rank, 0) AS rank,
                    COALESCE(sr.morph, 0) AS morph
                FROM skill_rank sr
                JOIN skill s ON s.id = sr.skill_id
                LEFT JOIN ability a ON a.ability_id = sr.ability_id
                WHERE sr.ability_id = ?
                """,
                (int(ability_id),),
            ).fetchone()
        if row is None:
            return SkillRankResolution(None, (f"Ability ID not found in skill_rank: {ability_id}",))
        return self._resolved_row(row)

    def resolve_name(self, name: str) -> SkillRankResolution:
        requested = str(name or "").strip()
        if not requested:
            return SkillRankResolution(None, ("Skill name is required",))

        with self._connect() as connection:
            if not self._table_exists(connection, "skill_rank"):
                return SkillRankResolution(None, ("skill_rank table is unavailable",))

            rows = connection.execute(
                """
                SELECT
                    sr.id AS skill_rank_id,
                    sr.skill_id,
                    sr.ability_id,
                    s.base_ability_id,
                    COALESCE(NULLIF(a.name, ''), NULLIF(sr.raw_name, ''), s.name, '') AS name,
                    COALESCE(sr.rank, 0) AS rank,
                    COALESCE(sr.morph, 0) AS morph
                FROM skill_rank sr
                JOIN skill s ON s.id = sr.skill_id
                LEFT JOIN ability a ON a.ability_id = sr.ability_id
                WHERE LOWER(COALESCE(NULLIF(a.name, ''), NULLIF(sr.raw_name, ''), s.name, '')) = LOWER(?)
                ORDER BY sr.rank DESC, sr.ability_id DESC
                """,
                (requested,),
            ).fetchall()

        if not rows:
            return SkillRankResolution(None, (f"Skill not found: {requested}",))

        # The same concrete morph name normally appears once per rank. Choose
        # the highest rank only when all matches belong to the same canonical
        # skill/morph. Duplicate names across different skills stay explicit.
        identities = {(int(row["skill_id"]), int(row["morph"])) for row in rows}
        if len(identities) > 1:
            ability_ids = ", ".join(str(int(row["ability_id"])) for row in rows)
            return SkillRankResolution(
                None,
                (f"Ambiguous skill name {requested!r}; matching ability IDs: {ability_ids}",),
            )

        return self._resolved_row(rows[0])

    def _resolved_row(self, row: sqlite3.Row) -> SkillRankResolution:
        rank_id = int(row["skill_rank_id"])
        coefficients = self.get_for_skill_rank(rank_id)
        resolved = ResolvedSkillRank(
            skill_rank_id=rank_id,
            skill_id=int(row["skill_id"]),
            ability_id=int(row["ability_id"]),
            base_ability_id=int(row["base_ability_id"]),
            name=str(row["name"] or ""),
            rank=int(row["rank"] or 0),
            morph=int(row["morph"] or 0),
            coefficients=coefficients,
        )
        if not coefficients:
            return SkillRankResolution(
                resolved,
                (f"No coefficient rows found for {resolved.name or resolved.ability_id} (ability {resolved.ability_id})",),
            )
        return SkillRankResolution(resolved)
