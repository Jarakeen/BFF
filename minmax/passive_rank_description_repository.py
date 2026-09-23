from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3


_COLOR = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")


@dataclass(frozen=True)
class PassiveRankDescriptionEvidence:
    passive_name: str
    rank: int
    description: str | None
    ability_id: int | None
    raw_description: str | None = None
    ability_description: str | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.description is not None and not self.unresolved


class PassiveRankDescriptionRepository:
    """Resolve one passive rank tooltip with disagreement detection.

    skill_rank.ability_id is an ESO ability identity, so production schema
    joins it to ability.ability_id rather than the ability table local row id.
    Rank-specific raw and ability descriptions are parallel evidence: when both
    are present and differ after normalization, resolution fails closed.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _columns(db: sqlite3.Connection, table: str) -> set[str]:
        return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})").fetchall()}

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(_COLOR.sub("", str(value or "")).replace("\\n", " ").split())


    @classmethod
    def reconcile_descriptions(
        cls,
        *,
        passive_name: str,
        rank: int,
        ability_id: int | None,
        raw_description: object = None,
        ability_description: object = None,
    ) -> PassiveRankDescriptionEvidence:
        name = " ".join(str(passive_name or "").strip().split())
        requested_rank = int(rank)
        raw = cls._clean(raw_description) or None
        ability = cls._clean(ability_description) or None
        if raw is not None and ability is not None and raw.casefold() != ability.casefold():
            return PassiveRankDescriptionEvidence(
                name,
                requested_rank,
                None,
                ability_id,
                raw,
                ability,
                (
                    f"Canonical passive rank tooltip disagreement: {name} rank "
                    f"{requested_rank} raw_description != ability.description",
                ),
            )
        resolved = raw or ability
        if resolved is None:
            return PassiveRankDescriptionEvidence(
                name,
                requested_rank,
                None,
                ability_id,
                raw,
                ability,
                (
                    f"Canonical passive rank description unavailable: {name} rank "
                    f"{requested_rank}",
                ),
            )
        return PassiveRankDescriptionEvidence(
            name,
            requested_rank,
            resolved,
            ability_id,
            raw,
            ability,
        )

    def resolve(self, passive_name: str, rank: int) -> PassiveRankDescriptionEvidence:
        name = " ".join(str(passive_name or "").strip().split())
        requested_rank = int(rank)
        if not name:
            raise ValueError("passive rank description requires a passive name")
        if requested_rank <= 0:
            raise ValueError("passive rank description requires a positive rank")
        if not self.database_path.exists():
            return PassiveRankDescriptionEvidence(name, requested_rank, None, None, unresolved=("Passive rank database is unavailable",))

        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            skill_columns = self._columns(db, "skill")
            rank_columns = self._columns(db, "skill_rank")
            ability_columns = self._columns(db, "ability")
            if not {"id", "name", "is_passive"}.issubset(skill_columns):
                return self._schema_failure(name, requested_rank, "skill")
            if not {"skill_id", "ability_id", "rank"}.issubset(rank_columns):
                return self._schema_failure(name, requested_rank, "skill_rank")
            if "ability_id" not in ability_columns:
                return self._schema_failure(name, requested_rank, "ability")

            raw_expr = "NULLIF(TRIM(sr.raw_description), '')" if "raw_description" in rank_columns else "NULL"
            ability_expr = "NULLIF(TRIM(a.description), '')" if "description" in ability_columns else "NULL"
            rows = db.execute(
                f"""
                SELECT sr.ability_id AS rank_ability_id,
                       {raw_expr} AS raw_description,
                       {ability_expr} AS ability_description
                FROM skill s
                JOIN skill_rank sr ON sr.skill_id = s.id
                LEFT JOIN ability a ON a.ability_id = sr.ability_id
                WHERE COALESCE(s.is_passive, 0) = 1
                  AND LOWER(TRIM(s.name)) = LOWER(TRIM(?))
                  AND sr.rank = ?
                ORDER BY sr.id
                """,
                (name, requested_rank),
            ).fetchall()

        if not rows:
            return PassiveRankDescriptionEvidence(name, requested_rank, None, None, unresolved=(f"Canonical passive rank not found: {name} rank {requested_rank}",))
        if len(rows) != 1:
            return PassiveRankDescriptionEvidence(name, requested_rank, None, None, unresolved=(f"Canonical passive rank is ambiguous: {name} rank {requested_rank} has {len(rows)} records",))

        row = rows[0]
        return self.reconcile_descriptions(
            passive_name=name,
            rank=requested_rank,
            ability_id=int(row["rank_ability_id"]),
            raw_description=row["raw_description"],
            ability_description=row["ability_description"],
        )

    @staticmethod
    def _schema_failure(passive_name: str, rank: int, table: str) -> PassiveRankDescriptionEvidence:
        return PassiveRankDescriptionEvidence(passive_name, rank, None, None, unresolved=(f"Passive rank description schema is incomplete: {table}",))


__all__ = ["PassiveRankDescriptionEvidence", "PassiveRankDescriptionRepository"]