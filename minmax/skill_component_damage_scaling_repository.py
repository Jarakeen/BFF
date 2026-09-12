from __future__ import annotations

"""Read-only repository for canonical Phase 6 component damage scaling."""

import sqlite3
from pathlib import Path

from .skill_component_damage_scaling import (
    SkillComponentDamageScaling,
    extract_explicit_component_damage_scaling,
)
from .skill_component_text_evidence import extract_component_text_evidence


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


class SkillComponentDamageScalingRepository:
    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)
        self._source_text_cache: dict[int, str | None] = {}
        self._resolve_cache: dict[
            tuple[int, int], tuple[SkillComponentDamageScaling, ...]
        ] = {}

    @staticmethod
    def _table_exists(db: sqlite3.Connection, name: str) -> bool:
        return db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone() is not None

    def _source_text(self, skill_rank_id: int) -> str | None:
        rank_id = int(skill_rank_id)
        if rank_id in self._source_text_cache:
            return self._source_text_cache[rank_id]

        if not self.database_path.exists():
            self._source_text_cache[rank_id] = None
            return None

        with sqlite3.connect(self.database_path) as db:
            if not all(self._table_exists(db, name) for name in ("skill_rank", "ability")):
                self._source_text_cache[rank_id] = None
                return None
            row = db.execute(
                """
                SELECT a.coef_description
                FROM skill_rank sr
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE sr.id = ?
                """,
                (rank_id,),
            ).fetchone()

        source_text = None if row is None else str(row[0] or "")
        self._source_text_cache[rank_id] = source_text
        return source_text

    def resolve(
        self,
        skill_rank_id: int,
        coefficient_number: int,
    ) -> tuple[SkillComponentDamageScaling, ...]:
        cache_key = (int(skill_rank_id), int(coefficient_number))
        if cache_key in self._resolve_cache:
            return self._resolve_cache[cache_key]

        source_text = self._source_text(cache_key[0])
        if source_text is None:
            self._resolve_cache[cache_key] = ()
            return ()

        evidence = extract_component_text_evidence(source_text, cache_key[1])
        if not evidence.fragment or evidence.effect_kind != "damage":
            self._resolve_cache[cache_key] = ()
            return ()

        resolved = extract_explicit_component_damage_scaling(
            skill_rank_id=cache_key[0],
            coefficient_number=cache_key[1],
            component_text=evidence.fragment,
        )
        self._resolve_cache[cache_key] = resolved
        return resolved
