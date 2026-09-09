from __future__ import annotations

import sqlite3
from pathlib import Path

from .skill_component_classification import (
    HealRecipientScope,
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)


class SkillComponentRepository:
    """Read verified per-coefficient component identities from the ESO database.

    The repository never infers component mechanics from names, duration, or
    target text. If the canonical classification table is unavailable or a row
    is incomplete, callers receive only what the database explicitly proves.

    Positive runtime critical observations live in a separate evidence table.
    An explicit classification ``can_crit`` value always wins; otherwise any
    stored positive runtime proof resolves ``can_crit`` to True. Absence of
    runtime evidence remains None and never becomes False.

    Classification columns have grown over time. Optional columns are loaded when
    present and remain ``None`` for older databases, preserving backward
    compatibility without fabricating missing mechanics.
    """

    TABLE = "skill_component_classification"
    CRITICAL_EVIDENCE_TABLE = "skill_component_critical_evidence"

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self._skill_rank_cache: dict[int, tuple[SkillComponentClassification, ...]] = {}

    @staticmethod
    def _table_exists(db: sqlite3.Connection, name: str) -> bool:
        row = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone()
        return row is not None

    @staticmethod
    def _table_columns(db: sqlite3.Connection, name: str) -> set[str]:
        return {str(row[1]) for row in db.execute(f"PRAGMA table_info({name})").fetchall()}

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

    @staticmethod
    def _recipient_scope(value: str | None) -> HealRecipientScope | None:
        text = str(value or "").strip().casefold()
        if not text:
            return None
        try:
            return HealRecipientScope(text)
        except ValueError:
            return None

    @staticmethod
    def _temporal_scope(value: str | None) -> HealTemporalScope | None:
        text = str(value or "").strip().casefold()
        if not text:
            return None
        try:
            return HealTemporalScope(text)
        except ValueError:
            return None

    @staticmethod
    def _optional_text(value) -> str | None:
        text = str(value or "").strip()
        return text or None

    def get_for_skill_rank(self, skill_rank_id: int) -> tuple[SkillComponentClassification, ...]:
        rank_id = int(skill_rank_id)
        if rank_id in self._skill_rank_cache:
            return self._skill_rank_cache[rank_id]

        if not self.database_path.exists():
            self._skill_rank_cache[rank_id] = ()
            return ()

        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            if not self._table_exists(db, self.TABLE):
                self._skill_rank_cache[rank_id] = ()
                return ()

            columns = self._table_columns(db, self.TABLE)
            has_runtime_crit = self._table_exists(db, self.CRITICAL_EVIDENCE_TABLE)
            if has_runtime_crit and "can_crit" in columns:
                can_crit_expression = f"""
                    CASE
                        WHEN c.can_crit IS NOT NULL THEN c.can_crit
                        WHEN EXISTS (
                            SELECT 1
                            FROM {self.CRITICAL_EVIDENCE_TABLE} e
                            WHERE e.skill_rank_id = c.skill_rank_id
                              AND e.coefficient_number = c.coefficient_number
                              AND e.can_crit = 1
                              AND e.observed_count > 0
                        ) THEN 1
                        ELSE NULL
                    END
                """
            elif "can_crit" in columns:
                can_crit_expression = "c.can_crit"
            else:
                can_crit_expression = "NULL"

            def optional_column(name: str) -> str:
                return f"c.{name}" if name in columns else "NULL"

            rows = db.execute(
                f"""
                SELECT
                    c.skill_rank_id,
                    c.coefficient_number,
                    {optional_column('effect_kind')} AS effect_kind,
                    {optional_column('damage_type')} AS damage_type,
                    {optional_column('is_dot')} AS is_dot,
                    {optional_column('is_aoe')} AS is_aoe,
                    {can_crit_expression} AS can_crit,
                    {optional_column('source')} AS source,
                    {optional_column('confidence')} AS confidence,
                    {optional_column('heal_recipient_scope')} AS heal_recipient_scope,
                    {optional_column('heal_temporal_scope')} AS heal_temporal_scope,
                    {optional_column('heal_recipient_key')} AS heal_recipient_key,
                    {optional_column('heal_event_key')} AS heal_event_key
                FROM {self.TABLE} c
                WHERE c.skill_rank_id = ?
                ORDER BY c.coefficient_number
                """,
                (rank_id,),
            ).fetchall()

        components = tuple(
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
                heal_recipient_scope=self._recipient_scope(row["heal_recipient_scope"]),
                heal_temporal_scope=self._temporal_scope(row["heal_temporal_scope"]),
                heal_recipient_key=self._optional_text(row["heal_recipient_key"]),
                heal_event_key=self._optional_text(row["heal_event_key"]),
            )
            for row in rows
        )
        self._skill_rank_cache[rank_id] = components
        return components

    def get_component(
        self,
        skill_rank_id: int,
        coefficient_number: int,
    ) -> SkillComponentClassification | None:
        for component in self.get_for_skill_rank(skill_rank_id):
            if component.coefficient_number == int(coefficient_number):
                return component
        return None
