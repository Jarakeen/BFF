from __future__ import annotations

"""Canonical persistence for Comp Maker composition/recruitment draft evidence.

Generated roster drafts are not RaidPlan state. They preserve composition chairs,
recruitment placeholders, and candidate/source evidence until a user explicitly adopts
those choices into Team/RaidPlan ownership.

The old ``generated_roster_plan*`` tables are migration input only. Existing rows are
copied forward non-destructively into the canonical ``generated_roster_draft*`` tables;
all normal reads and writes use the canonical draft tables afterwards.
"""

from dataclasses import dataclass
import json

from services.eso_database import EsoDatabase
from services.user_database import user_database_for
from services.generated_roster_draft_pydantic_schema import validate_generated_roster_draft


GENERATED_ROSTER_DRAFT_OWNERSHIP = "composition_recruitment_evidence_only"
GENERATED_ROSTER_DRAFT_STORAGE = "generated_roster_draft"
LEGACY_GENERATED_ROSTER_PLAN_READ_MIGRATION_ONLY = True


@dataclass(frozen=True)
class GeneratedRosterDraftSlot:
    """One persisted composition/recruitment draft chair."""

    slot_name: str
    kind: str
    player_name: str
    character_name: str
    eso_class: str
    build_name: str
    gear_summary: str = ""
    unresolved: str = ""
    role: str = ""
    source_kind: str = ""
    source_name: str = ""
    source_url: str = ""
    candidate_id: str = ""
    gear_sets: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    mundus: str = ""


@dataclass(frozen=True)
class GeneratedRosterDraft:
    """Durable Comp Maker draft evidence waiting for explicit adoption."""

    draft_id: int
    name: str
    goal: str
    difficulty: str
    slots: tuple[GeneratedRosterDraftSlot, ...]

    @property
    def plan_id(self) -> int:
        """Compatibility view for legacy callers during API migration."""
        return self.draft_id


class GeneratedRosterDraftService:
    """Persist generated composition/recruitment evidence outside RaidPlan state."""

    _STRUCTURED_COLUMNS = (
        "role",
        "source_kind",
        "source_name",
        "source_url",
        "candidate_id",
        "gear_sets_json",
        "skills_json",
        "mundus",
    )

    def __init__(self, database: EsoDatabase):
        self.db = user_database_for(database)
        self._ensure_schema()

    def _table_exists(self, table: str) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None

    def _columns(self, table: str) -> set[str]:
        return {
            str(row["name"])
            for row in self.db.execute(f"PRAGMA table_info({table})").fetchall()
        }

    def _ensure_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_roster_draft (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                goal TEXT NOT NULL,
                difficulty TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_roster_draft_slot (
                draft_id INTEGER NOT NULL
                    REFERENCES generated_roster_draft(id)
                    ON DELETE CASCADE,
                slot_index INTEGER NOT NULL,
                slot_name TEXT NOT NULL,
                kind TEXT NOT NULL,
                player_name TEXT NOT NULL DEFAULT '',
                character_name TEXT NOT NULL DEFAULT '',
                eso_class TEXT NOT NULL DEFAULT '',
                build_name TEXT NOT NULL DEFAULT '',
                gear_summary TEXT NOT NULL DEFAULT '',
                unresolved TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT '',
                source_kind TEXT NOT NULL DEFAULT '',
                source_name TEXT NOT NULL DEFAULT '',
                source_url TEXT NOT NULL DEFAULT '',
                candidate_id TEXT NOT NULL DEFAULT '',
                gear_sets_json TEXT NOT NULL DEFAULT '[]',
                skills_json TEXT NOT NULL DEFAULT '[]',
                mundus TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (draft_id, slot_index)
            )
            """
        )
        self._migrate_legacy_storage()
        self.db.commit()

    def _migrate_legacy_storage(self) -> None:
        """Copy legacy generated-plan rows forward without mutating legacy tables."""

        if not self._table_exists("generated_roster_plan"):
            return
        if not self._table_exists("generated_roster_plan_slot"):
            return

        plan_columns = self._columns("generated_roster_plan")
        required_plan = {"id", "name", "goal"}
        if not required_plan.issubset(plan_columns):
            raise ValueError("legacy generated roster plan storage is missing required columns")

        difficulty_expr = "difficulty" if "difficulty" in plan_columns else "''"
        updated_expr = "updated_at" if "updated_at" in plan_columns else "CURRENT_TIMESTAMP"
        self.db.execute(
            f"""
            INSERT OR IGNORE INTO generated_roster_draft (
                id, name, goal, difficulty, updated_at
            )
            SELECT id, name, goal, {difficulty_expr}, {updated_expr}
            FROM generated_roster_plan
            """
        )

        slot_columns = self._columns("generated_roster_plan_slot")
        required_slot = {
            "plan_id",
            "slot_index",
            "slot_name",
            "kind",
            "player_name",
            "character_name",
            "eso_class",
            "build_name",
            "gear_summary",
            "unresolved",
        }
        if not required_slot.issubset(slot_columns):
            raise ValueError("legacy generated roster plan slot storage is missing required columns")

        def legacy_expr(column: str, default_sql: str) -> str:
            return f"s.{column}" if column in slot_columns else default_sql

        structured = {
            "role": legacy_expr("role", "''"),
            "source_kind": legacy_expr("source_kind", "''"),
            "source_name": legacy_expr("source_name", "''"),
            "source_url": legacy_expr("source_url", "''"),
            "candidate_id": legacy_expr("candidate_id", "''"),
            "gear_sets_json": legacy_expr("gear_sets_json", "'[]'"),
            "skills_json": legacy_expr("skills_json", "'[]'"),
            "mundus": legacy_expr("mundus", "''"),
        }
        self.db.execute(
            f"""
            INSERT OR IGNORE INTO generated_roster_draft_slot (
                draft_id, slot_index, slot_name, kind, player_name,
                character_name, eso_class, build_name, gear_summary, unresolved,
                role, source_kind, source_name, source_url, candidate_id,
                gear_sets_json, skills_json, mundus
            )
            SELECT
                d.id, s.slot_index, s.slot_name, s.kind, s.player_name,
                s.character_name, s.eso_class, s.build_name, s.gear_summary, s.unresolved,
                {structured['role']}, {structured['source_kind']},
                {structured['source_name']}, {structured['source_url']},
                {structured['candidate_id']}, {structured['gear_sets_json']},
                {structured['skills_json']}, {structured['mundus']}
            FROM generated_roster_plan_slot s
            JOIN generated_roster_plan p ON p.id = s.plan_id
            JOIN generated_roster_draft d ON d.name = p.name COLLATE NOCASE
            """
        )

    @staticmethod
    def _json_tuple(value: str) -> tuple[str, ...]:
        try:
            raw = json.loads(str(value or "[]"))
        except json.JSONDecodeError:
            return ()
        if not isinstance(raw, list):
            return ()
        return tuple(str(item).strip() for item in raw if str(item).strip())

    def save_plan(
        self,
        *,
        name: str,
        goal: str,
        difficulty: str,
        slots: tuple[GeneratedRosterDraftSlot, ...],
    ) -> GeneratedRosterDraft:
        intended = validate_generated_roster_draft({
            "name": str(name or "").strip(),
            "goal": str(goal or "").strip(),
            "difficulty": str(difficulty or "").strip(),
            "slots": tuple({
                "slot_name": slot.slot_name, "kind": slot.kind,
                "player_name": slot.player_name, "character_name": slot.character_name,
                "eso_class": slot.eso_class, "build_name": slot.build_name,
                "gear_summary": slot.gear_summary, "unresolved": slot.unresolved,
                "role": slot.role, "source_kind": slot.source_kind,
                "source_name": slot.source_name, "source_url": slot.source_url,
                "candidate_id": slot.candidate_id, "gear_sets": tuple(slot.gear_sets),
                "skills": tuple(slot.skills), "mundus": slot.mundus,
            } for slot in slots),
        })
        db = self.db.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                """INSERT INTO generated_roster_draft (name, goal, difficulty, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(name) DO UPDATE SET goal=excluded.goal,
                       difficulty=excluded.difficulty, updated_at=CURRENT_TIMESTAMP""",
                (intended["name"], intended["goal"], intended["difficulty"]),
            )
            row = db.execute(
                "SELECT id FROM generated_roster_draft WHERE name = ? COLLATE NOCASE",
                (intended["name"],),
            ).fetchone()
            if row is None:
                raise RuntimeError("generated roster draft could not be reloaded after save")
            draft_id = int(row["id"])
            db.execute("DELETE FROM generated_roster_draft_slot WHERE draft_id = ?", (draft_id,))
            for index, slot in enumerate(intended["slots"]):
                db.execute(
                    """INSERT INTO generated_roster_draft_slot (
                        draft_id, slot_index, slot_name, kind, player_name, character_name,
                        eso_class, build_name, gear_summary, unresolved, role, source_kind,
                        source_name, source_url, candidate_id, gear_sets_json, skills_json, mundus
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (draft_id, index, slot["slot_name"], slot["kind"], slot["player_name"],
                     slot["character_name"], slot["eso_class"], slot["build_name"],
                     slot["gear_summary"], slot["unresolved"], slot["role"], slot["source_kind"],
                     slot["source_name"], slot["source_url"], slot["candidate_id"],
                     json.dumps(list(slot["gear_sets"]), ensure_ascii=False),
                     json.dumps(list(slot["skills"]), ensure_ascii=False), slot["mundus"]),
                )
            persisted = self._load_row(
                db.execute(
                    "SELECT id, name, goal, difficulty FROM generated_roster_draft WHERE id = ?",
                    (draft_id,),
                ).fetchone()
            )
            read_back = validate_generated_roster_draft({
                "name": persisted.name, "goal": persisted.goal,
                "difficulty": persisted.difficulty,
                "slots": tuple({
                    "slot_name": slot.slot_name, "kind": slot.kind,
                    "player_name": slot.player_name, "character_name": slot.character_name,
                    "eso_class": slot.eso_class, "build_name": slot.build_name,
                    "gear_summary": slot.gear_summary, "unresolved": slot.unresolved,
                    "role": slot.role, "source_kind": slot.source_kind,
                    "source_name": slot.source_name, "source_url": slot.source_url,
                    "candidate_id": slot.candidate_id, "gear_sets": tuple(slot.gear_sets),
                    "skills": tuple(slot.skills), "mundus": slot.mundus,
                } for slot in persisted.slots),
            })
            if read_back != intended:
                raise RuntimeError("generated roster draft did not round-trip exactly")
            db.commit()
        except Exception:
            db.rollback()
            raise
        return GeneratedRosterDraft(
            draft_id=draft_id,
            name=intended["name"],
            goal=intended["goal"],
            difficulty=intended["difficulty"],
            slots=tuple(slots),
        )

    def list_plan_names(self) -> tuple[str, ...]:
        rows = self.db.execute(
            """
            SELECT name
            FROM generated_roster_draft
            ORDER BY updated_at DESC, name COLLATE NOCASE
            """
        ).fetchall()
        return tuple(str(row["name"]) for row in rows)

    def load_plan(self, name: str) -> GeneratedRosterDraft | None:
        row = self.db.execute(
            """
            SELECT id, name, goal, difficulty
            FROM generated_roster_draft
            WHERE name = ? COLLATE NOCASE
            """,
            (str(name or "").strip(),),
        ).fetchone()
        if row is None:
            return None
        return self._load_row(row)

    def latest_plan(self) -> GeneratedRosterDraft | None:
        row = self.db.execute(
            """
            SELECT id, name, goal, difficulty
            FROM generated_roster_draft
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
        ).fetchone()
        if row is None:
            return None
        return self._load_row(row)

    def _load_row(self, row) -> GeneratedRosterDraft:
        draft_id = int(row["id"])
        slot_rows = self.db.execute(
            """
            SELECT slot_name, kind, player_name, character_name,
                   eso_class, build_name, gear_summary, unresolved,
                   role, source_kind, source_name, source_url, candidate_id,
                   gear_sets_json, skills_json, mundus
            FROM generated_roster_draft_slot
            WHERE draft_id = ?
            ORDER BY slot_index
            """,
            (draft_id,),
        ).fetchall()
        slots = tuple(
            GeneratedRosterDraftSlot(
                slot_name=str(slot["slot_name"] or ""),
                kind=str(slot["kind"] or ""),
                player_name=str(slot["player_name"] or ""),
                character_name=str(slot["character_name"] or ""),
                eso_class=str(slot["eso_class"] or ""),
                build_name=str(slot["build_name"] or ""),
                gear_summary=str(slot["gear_summary"] or ""),
                unresolved=str(slot["unresolved"] or ""),
                role=str(slot["role"] or ""),
                source_kind=str(slot["source_kind"] or ""),
                source_name=str(slot["source_name"] or ""),
                source_url=str(slot["source_url"] or ""),
                candidate_id=str(slot["candidate_id"] or ""),
                gear_sets=self._json_tuple(slot["gear_sets_json"]),
                skills=self._json_tuple(slot["skills_json"]),
                mundus=str(slot["mundus"] or ""),
            )
            for slot in slot_rows
        )
        return GeneratedRosterDraft(
            draft_id=draft_id,
            name=str(row["name"]),
            goal=str(row["goal"]),
            difficulty=str(row["difficulty"] or ""),
            slots=slots,
        )


__all__ = [
    "GENERATED_ROSTER_DRAFT_OWNERSHIP",
    "GENERATED_ROSTER_DRAFT_STORAGE",
    "LEGACY_GENERATED_ROSTER_PLAN_READ_MIGRATION_ONLY",
    "GeneratedRosterDraft",
    "GeneratedRosterDraftService",
    "GeneratedRosterDraftSlot",
]
