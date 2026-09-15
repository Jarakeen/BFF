from __future__ import annotations

"""Canonical persistence for recruit-prescription evidence attached to generated drafts.

The historical ``generated_roster_recruit_prescription`` table points at the legacy
``generated_roster_plan`` store. It is migration input only. Existing rows are copied
forward non-destructively by matching the legacy plan name to the canonical generated
draft identity. Normal reads and writes use ``generated_roster_draft_recruit_prescription``.
"""

import json

from services.eso_database import EsoDatabase


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
        resolved_slot = str(slot_name or "").strip()
        if not resolved_slot:
            raise ValueError("generated draft prescription requires slot_name")
        payload = json.dumps(prescription, ensure_ascii=False, sort_keys=True)
        self.db.execute(
            """
            INSERT INTO generated_roster_draft_recruit_prescription (
                draft_id, slot_name, prescription_json,
                adopted_player_name, adopted_character_name, adopted_build_name,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(draft_id, slot_name) DO UPDATE SET
                adopted_player_name = excluded.adopted_player_name,
                adopted_character_name = excluded.adopted_character_name,
                adopted_build_name = excluded.adopted_build_name,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                int(draft_id),
                resolved_slot,
                payload,
                str(adopted_player_name or "").strip(),
                str(adopted_character_name or "").strip(),
                str(adopted_build_name or "").strip(),
            ),
        )
        self.db.commit()


__all__ = [
    "GENERATED_ROSTER_DRAFT_PRESCRIPTION_STORAGE",
    "LEGACY_GENERATED_ROSTER_PRESCRIPTION_READ_MIGRATION_ONLY",
    "GeneratedRosterDraftPrescriptionService",
]
