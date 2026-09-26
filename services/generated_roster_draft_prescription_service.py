from __future__ import annotations

"""Canonical persistence for recruit-prescription evidence attached to generated drafts.

The historical ``generated_roster_recruit_prescription`` table points at the legacy
``generated_roster_plan`` store. It is migration input only. Existing rows are copied
forward non-destructively by matching the legacy plan name to the canonical generated
draft identity. Normal reads and writes use ``generated_roster_draft_recruit_prescription``.
"""

import json

from services.eso_database import EsoDatabase
from services.generated_roster_draft_pydantic_schema import validate_generated_roster_prescription


GENERATED_ROSTER_DRAFT_PRESCRIPTION_STORAGE = (
    "generated_roster_draft_recruit_prescription"
)
LEGACY_GENERATED_ROSTER_PRESCRIPTION_READ_MIGRATION_ONLY = True


class GeneratedRosterDraftPrescriptionService:
    """Persist preserved recruit prescriptions against canonical generated draft ids."""

    def __init__(self, database: EsoDatabase) -> None:
        self.db = database
        self._ensure_schema()

    def _table_exists(self, table: str) -> bool:
        return (
            self.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            ).fetchone()
            is not None
        )

    def _columns(self, table: str) -> set[str]:
        return {
            str(row["name"])
            for row in self.db.execute(f"PRAGMA table_info({table})").fetchall()
        }

    def _ensure_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_roster_draft_recruit_prescription (
                draft_id INTEGER NOT NULL
                    REFERENCES generated_roster_draft(id)
                    ON DELETE CASCADE,
                slot_name TEXT NOT NULL,
                prescription_json TEXT NOT NULL,
                adopted_player_name TEXT NOT NULL DEFAULT '',
                adopted_character_name TEXT NOT NULL DEFAULT '',
                adopted_build_name TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (draft_id, slot_name)
            )
            """
        )
        self._migrate_legacy_storage()
        self.db.commit()

    def _migrate_legacy_storage(self) -> None:
        required_tables = (
            "generated_roster_recruit_prescription",
            "generated_roster_plan",
            "generated_roster_draft",
        )
        if not all(self._table_exists(table) for table in required_tables):
            return

        legacy_columns = self._columns("generated_roster_recruit_prescription")
        required = {"plan_id", "slot_name", "prescription_json"}
        if not required.issubset(legacy_columns):
            raise ValueError(
                "legacy generated roster recruit prescription storage is missing required columns"
            )

        def legacy_expr(column: str, default_sql: str) -> str:
            return f"p.{column}" if column in legacy_columns else default_sql

        self.db.execute(
            f"""
            INSERT OR IGNORE INTO generated_roster_draft_recruit_prescription (
                draft_id, slot_name, prescription_json,
                adopted_player_name, adopted_character_name, adopted_build_name,
                updated_at
            )
            SELECT
                d.id,
                p.slot_name,
                p.prescription_json,
                {legacy_expr('adopted_player_name', "''")},
                {legacy_expr('adopted_character_name', "''")},
                {legacy_expr('adopted_build_name', "''")},
                {legacy_expr('updated_at', 'CURRENT_TIMESTAMP')}
            FROM generated_roster_recruit_prescription p
            JOIN generated_roster_plan legacy_plan ON legacy_plan.id = p.plan_id
            JOIN generated_roster_draft d
              ON d.name = legacy_plan.name COLLATE NOCASE
            """
        )

    def load(self, draft_id: int, slot_name: str) -> dict[str, object] | None:
        row = self.db.execute(
            """
            SELECT prescription_json
            FROM generated_roster_draft_recruit_prescription
            WHERE draft_id = ? AND slot_name = ? COLLATE NOCASE
            """,
            (int(draft_id), str(slot_name or "").strip()),
        ).fetchone()
        if row is None:
            return None
        try:
            value = json.loads(str(row["prescription_json"] or "{}"))
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None

    def save(
        self,
        *,
        draft_id: int,
        slot_name: str,
        prescription: dict[str, object],
        adopted_player_name: str,
        adopted_character_name: str,
        adopted_build_name: str,
    ) -> None:
        intended = validate_generated_roster_prescription({
            "draft_id": int(draft_id),
            "slot_name": str(slot_name or "").strip(),
            "prescription": prescription,
            "adopted_player_name": str(adopted_player_name or "").strip(),
            "adopted_character_name": str(adopted_character_name or "").strip(),
            "adopted_build_name": str(adopted_build_name or "").strip(),
        })
        payload = json.dumps(intended["prescription"], ensure_ascii=False, sort_keys=True)
        db = self.db.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            parent = db.execute(
                "SELECT 1 FROM generated_roster_draft WHERE id = ?",
                (intended["draft_id"],),
            ).fetchone()
            if parent is None:
                raise ValueError(f"generated roster draft {intended['draft_id']} does not exist")
            db.execute(
                """
                INSERT INTO generated_roster_draft_recruit_prescription (
                    draft_id, slot_name, prescription_json,
                    adopted_player_name, adopted_character_name, adopted_build_name,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(draft_id, slot_name) DO UPDATE SET
                    prescription_json = excluded.prescription_json,
                    adopted_player_name = excluded.adopted_player_name,
                    adopted_character_name = excluded.adopted_character_name,
                    adopted_build_name = excluded.adopted_build_name,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    intended["draft_id"], intended["slot_name"], payload,
                    intended["adopted_player_name"], intended["adopted_character_name"],
                    intended["adopted_build_name"],
                ),
            )
            row = db.execute(
                """SELECT prescription_json, adopted_player_name, adopted_character_name,
                          adopted_build_name
                   FROM generated_roster_draft_recruit_prescription
                   WHERE draft_id = ? AND slot_name = ? COLLATE NOCASE""",
                (intended["draft_id"], intended["slot_name"]),
            ).fetchone()
            if row is None:
                raise RuntimeError("generated roster prescription was not persisted")
            read_back = validate_generated_roster_prescription({
                "draft_id": intended["draft_id"],
                "slot_name": intended["slot_name"],
                "prescription": json.loads(str(row["prescription_json"])),
                "adopted_player_name": str(row["adopted_player_name"]),
                "adopted_character_name": str(row["adopted_character_name"]),
                "adopted_build_name": str(row["adopted_build_name"]),
            })
            if read_back != intended:
                raise RuntimeError("generated roster prescription did not round-trip exactly")
            db.commit()
        except Exception:
            db.rollback()
            raise


__all__ = [
    "GENERATED_ROSTER_DRAFT_PRESCRIPTION_STORAGE",
    "LEGACY_GENERATED_ROSTER_PRESCRIPTION_READ_MIGRATION_ONLY",
    "GeneratedRosterDraftPrescriptionService",
]
