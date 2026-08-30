from __future__ import annotations

import sqlite3
from pathlib import Path

from .skill_component_classification import SkillComponentClassification, SkillEffectKind


class SkillComponentRepository:
    """Read verified per-coefficient component identities from the ESO database.

    The repository never infers component mechanics from names, duration, or
    target text.  If the canonical classification table is unavailable or a
    row is incomplete, callers receive only what the database explicitly
    proves.
    """

    TABLE = "skill_component_classification"

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _table_exists(db: sqlite3.Connection, name: str) -> bool:
        row = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone()
        return row is not None

    @staticmethod
    def _bool_or_none(value) -> bool | None:
        if value is None:
            return None
        return bool(int(value))

    @staticmethod
    def _kind(value: str | None) -> SkillEffectKind:
        text = str(value or "").strip().casefold()
        try:
            return SkillEffectKind(text)
        except ValueError:
            return SkillEffectKind.UNKNOWN

    def get_for_skill_rank(self, skill_rank_id: int) -> tuple[SkillComponentClassification, ...]:
        if not self.database_path.exists():
            return ()

        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            if not self._table_exists(db, self.TABLE):
                return ()
            rows = db.execute(
                f"""
                SELECT
                    skill_rank_id,
                    coefficient_number,
                    effect_kind,
                    damage_type,
                    is_dot,
                    is_aoe,
                    can_crit,
                    source,
                    confidence
                FROM {self.TABLE}
                WHERE skill_rank_id = ?
                ORDER BY coefficient_number
                """,
                (int(skill_rank_id),),
            ).fetchall()

        return tuple(
            SkillComponentClassification(
                skill_rank_id=int(row["skill_rank_id"]),
                coefficient_number=int(row["coefficient_number"]),
                effect_kind=self._kind(row["effect_kind"]),
                damage_type=(
                    str(row["damage_type"]).strip().casefold()
                    if row["damage_type"] is not None and str(row["damage_type"]).strip()
                    else None
                ),
                is_dot=self._bool_or_none(row["is_dot"]),
                is_aoe=self._bool_or_none(row["is_aoe"]),
                can_crit=self._bool_or_none(row["can_crit"]),
                source=str(row["source"] or ""),
                confidence=(
                    float(row["confidence"])
                    if row["confidence"] is not None
                    else None
                ),
            )
            for row in rows
        )

    def get_component(
        self,
        skill_rank_id: int,
        coefficient_number: int,
    ) -> SkillComponentClassification | None:
        for component in self.get_for_skill_rank(skill_rank_id):
            if component.coefficient_number == int(coefficient_number):
                return component
        return None
