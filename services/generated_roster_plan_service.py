from __future__ import annotations

from dataclasses import dataclass
import json

from services.eso_database import EsoDatabase
from services.roster_service import RosterService


GENERATED_ROSTER_DRAFT_OWNERSHIP = "composition_recruitment_evidence_only"
LEGACY_GENERATED_ROSTER_PLAN_COMPATIBILITY = True


@dataclass(frozen=True)
class GeneratedRosterDraftSlot:
    """One persisted composition/recruitment draft chair.

    This is candidate/planning evidence only. It does not own final RaidPlan player,
    character, build, or assignment identity.
    """

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
    """Durable Comp Maker draft evidence waiting for explicit adoption.

    RaidPlan owns trial-specific selected people, builds, and assignments. This draft
    preserves recruitment placeholders and candidate/source evidence that cannot yet be
    represented by RaidPlan without fabricating player identity.
    """

    draft_id: int
    name: str
    goal: str
    difficulty: str
    slots: tuple[GeneratedRosterDraftSlot, ...]

    @property
    def plan_id(self) -> int:
        """Compatibility view for legacy callers during migration."""
        return self.draft_id


class GeneratedRosterDraftService:
    """Legacy-backed persistence for Comp Maker draft evidence.

    The existing ``generated_roster_plan*`` SQLite tables are retained only as a
    compatibility store during migration. Records here are not authoritative RaidPlan
    state. Explicit adoption into Team and/or RaidPlan owns final people/build/assignment
    selections; this service preserves composition, recruitment, and candidate evidence.
    """

    _STRUCTURED_COLUMNS = {
        "role": "TEXT NOT NULL DEFAULT ''",
        "source_kind": "TEXT NOT NULL DEFAULT ''",
        "source_name": "TEXT NOT NULL DEFAULT ''",
        "source_url": "TEXT NOT NULL DEFAULT ''",
        "candidate_id": "TEXT NOT NULL DEFAULT ''",
        "gear_sets_json": "TEXT NOT NULL DEFAULT '[]'",
        "skills_json": "TEXT NOT NULL DEFAULT '[]'",
        "mundus": "TEXT NOT NULL DEFAULT ''",
    }

    def __init__(self, database: EsoDatabase):
        self.db = database
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_roster_plan (
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
            CREATE TABLE IF NOT EXISTS generated_roster_plan_slot (
                plan_id INTEGER NOT NULL
                    REFERENCES generated_roster_plan(id)
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
                PRIMARY KEY (plan_id, slot_index)
            )
            """
        )
        existing = {
            row["name"]
            for row in self.db.execute(
                "PRAGMA table_info(generated_roster_plan_slot)"
            ).fetchall()
        }
        for column, definition in self._STRUCTURED_COLUMNS.items():
            if column not in existing:
                self.db.execute(
                    f"ALTER TABLE generated_roster_plan_slot ADD COLUMN {column} {definition}"
                )
        self.db.commit()

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
        plan_name = str(name or "").strip()
        plan_goal = str(goal or "").strip()
        if not plan_name:
            raise ValueError("generated roster draft requires a name")
        if not plan_goal:
            raise ValueError("generated roster draft requires a goal")
        if not slots:
            raise ValueError("generated roster draft requires at least one slot")

        self.db.execute(
            """
            INSERT INTO generated_roster_plan (name, goal, difficulty, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                goal = excluded.goal,
                difficulty = excluded.difficulty,
                updated_at = CURRENT_TIMESTAMP
            """,
            (plan_name, plan_goal, str(difficulty or "").strip()),
        )
        row = self.db.execute(
            "SELECT id FROM generated_roster_plan WHERE name = ? COLLATE NOCASE",
            (plan_name,),
        ).fetchone()
        if row is None:
            raise RuntimeError("generated roster draft could not be reloaded after save")
        draft_id = int(row["id"])
        self.db.execute(
            "DELETE FROM generated_roster_plan_slot WHERE plan_id = ?",
            (draft_id,),
        )
        for index, slot in enumerate(slots):
            self.db.execute(
                """
                INSERT INTO generated_roster_plan_slot (
                    plan_id, slot_index, slot_name, kind, player_name,
                    character_name, eso_class, build_name, gear_summary, unresolved,
                    role, source_kind, source_name, source_url, candidate_id,
                    gear_sets_json, skills_json, mundus
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft_id,
                    index,
                    slot.slot_name,
                    slot.kind,
                    slot.player_name,
                    slot.character_name,
                    slot.eso_class,
                    slot.build_name,
                    slot.gear_summary,
                    slot.unresolved,
                    slot.role,
                    slot.source_kind,
                    slot.source_name,
                    slot.source_url,
                    slot.candidate_id,
                    json.dumps(list(slot.gear_sets), ensure_ascii=False),
                    json.dumps(list(slot.skills), ensure_ascii=False),
                    slot.mundus,
                ),
            )
        self.db.commit()

        canonical_name = RosterService(self.db).ensure_team_name(plan_name)
        return GeneratedRosterDraft(
            draft_id=draft_id,
            name=canonical_name,
            goal=plan_goal,
            difficulty=str(difficulty or "").strip(),
            slots=tuple(slots),
        )

    def list_plan_names(self) -> tuple[str, ...]:
        rows = self.db.execute(
            """
            SELECT name
            FROM generated_roster_plan
            ORDER BY updated_at DESC, name COLLATE NOCASE
            """
        ).fetchall()
        return tuple(str(row["name"]) for row in rows)

    def load_plan(self, name: str) -> GeneratedRosterDraft | None:
        row = self.db.execute(
            """
            SELECT id, name, goal, difficulty
            FROM generated_roster_plan
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
            FROM generated_roster_plan
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
            FROM generated_roster_plan_slot
            WHERE plan_id = ?
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


# Compatibility aliases retained while older Phase 12.5 tools/tests are migrated.
GeneratedRosterPlanSlot = GeneratedRosterDraftSlot
GeneratedRosterPlan = GeneratedRosterDraft
GeneratedRosterPlanService = GeneratedRosterDraftService


__all__ = [
    "GENERATED_ROSTER_DRAFT_OWNERSHIP",
    "LEGACY_GENERATED_ROSTER_PLAN_COMPATIBILITY",
    "GeneratedRosterDraft",
    "GeneratedRosterDraftService",
    "GeneratedRosterDraftSlot",
    "GeneratedRosterPlan",
    "GeneratedRosterPlanService",
    "GeneratedRosterPlanSlot",
]
