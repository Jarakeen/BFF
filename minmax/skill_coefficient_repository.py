from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .skill_coefficients import SkillCoefficient


def ability_entity_id(name: str) -> str:
    """Return the canonical lower-snake-case identity for an ESO ability name.

    ESO numeric ability IDs remain source/rank crosswalk identifiers. They are
    not durable logical identities because one named ability can map to several
    numeric IDs across ranks/variants.
    """

    text = unicodedata.normalize("NFKD", str(name or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.replace("’", "'")
    text = re.sub(r"['`]", "", text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_").lower()


@dataclass(frozen=True)
class ResolvedSkillRank:
    entity_id: str
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
    """Resolve canonical ability entities, concrete ranks, and coefficient rows."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._entity_resolution_cache: dict[str, SkillRankResolution] = {}
        self._name_resolution_cache: dict[str, SkillRankResolution] = {}

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
        """Resolve one numeric ESO ability ID as a source/crosswalk lookup."""

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

    def resolve_entity_id(self, entity_id: str) -> SkillRankResolution:
        """Resolve the canonical lower-snake-case ability identity.

        Numeric ESO IDs are deliberately not used as the logical identity.
        Multiple rank/variant IDs may legitimately map to one entity ID.
        """

        requested = ability_entity_id(entity_id)
        if not requested:
            return SkillRankResolution(None, ("Ability entity ID is required",))

        cached = self._entity_resolution_cache.get(requested)
        if cached is not None:
            return cached

        with self._connect() as connection:
            rows = self._all_rank_identity_rows(connection)

        matches = [row for row in rows if ability_entity_id(str(row["name"] or "")) == requested]
        resolution = self._resolve_matching_rows(matches, requested, label="ability entity ID")
        self._entity_resolution_cache[requested] = resolution
        return resolution

    def resolve_name(self, name: str) -> SkillRankResolution:
        requested = str(name or "").strip()
        if not requested:
            return SkillRankResolution(None, ("Skill name is required",))

        cache_key = requested.casefold()
        cached = self._name_resolution_cache.get(cache_key)
        if cached is not None:
            return cached

        with self._connect() as connection:
            if not self._table_exists(connection, "skill_rank"):
                resolution = SkillRankResolution(None, ("skill_rank table is unavailable",))
                self._name_resolution_cache[cache_key] = resolution
                return resolution

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

        resolution = self._resolve_matching_rows(rows, requested, label="skill name")
        self._name_resolution_cache[cache_key] = resolution
        return resolution

    def _all_rank_identity_rows(self, connection: sqlite3.Connection) -> list[sqlite3.Row]:
        if not self._table_exists(connection, "skill_rank"):
            return []
        return connection.execute(
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
            ORDER BY sr.rank DESC, sr.ability_id DESC
            """
        ).fetchall()

    def _resolve_matching_rows(
        self,
        rows: list[sqlite3.Row] | tuple[sqlite3.Row, ...],
        requested: str,
        *,
        label: str,
    ) -> SkillRankResolution:
        if not rows:
            return SkillRankResolution(None, (f"{label.title()} not found: {requested}",))

        # Repeated numeric IDs for ranks/variants are expected. Ambiguity only
        # exists when the same canonical name maps to different logical
        # skill/morph identities.
        identities = {(int(row["skill_id"]), int(row["morph"])) for row in rows}
        if len(identities) > 1:
            ability_ids = ", ".join(str(int(row["ability_id"])) for row in rows)
            return SkillRankResolution(
                None,
                (f"Ambiguous {label} {requested!r}; matching numeric ability IDs: {ability_ids}",),
            )

        return self._resolved_row(rows[0])

    def _resolved_row(self, row: sqlite3.Row) -> SkillRankResolution:
        rank_id = int(row["skill_rank_id"])
        coefficients = self.get_for_skill_rank(rank_id)
        name = str(row["name"] or "")
        resolved = ResolvedSkillRank(
            entity_id=ability_entity_id(name),
            skill_rank_id=rank_id,
            skill_id=int(row["skill_id"]),
            ability_id=int(row["ability_id"]),
            base_ability_id=int(row["base_ability_id"]),
            name=name,
            rank=int(row["rank"] or 0),
            morph=int(row["morph"] or 0),
            coefficients=coefficients,
        )
        if not coefficients:
            return SkillRankResolution(
                resolved,
                (f"No coefficient rows found for {resolved.entity_id or resolved.name} (source ability {resolved.ability_id})",),
            )
        return SkillRankResolution(resolved)
