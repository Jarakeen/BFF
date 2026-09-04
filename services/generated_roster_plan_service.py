from __future__ import annotations

from dataclasses import dataclass

from services.eso_database import EsoDatabase


@dataclass(frozen=True)
class GeneratedRosterPlanSlot:
    slot_name: str
    kind: str
    player_name: str
    character_name: str
    eso_class: str
    build_name: str
    gear_summary: str = ""
    unresolved: str = ""


@dataclass(frozen=True)
class GeneratedRosterPlan:
    plan_id: int
    name: str
    goal: str
    difficulty: str
    slots: tuple[GeneratedRosterPlanSlot, ...]


class GeneratedRosterPlanService:
    """Persistent bridge between Team Optimization and the Roster page.

    Generated plans are deliberately separate from roster_member. Recruitment
    requirements are real roster-plan slots but are not fabricated people.
    Re-sending the same named prescription replaces only that generated plan.
    """

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
                PRIMARY KEY (plan_id, slot_index)
            )
            """
        )
        self.db.commit()

    def save_plan(
        self,
        *,
        name: str,
        goal: str,
        difficulty: str,
        slots: tuple[GeneratedRosterPlanSlot, ...],
    ) -> GeneratedRosterPlan:
        plan_name = str(name or "").strip()
        plan_goal = str(goal or "").strip()
        if not plan_name:
            raise ValueError("generated roster plan requires a name")
        if not plan_goal:
            raise ValueError("generated roster plan requires a goal")
        if not slots:
            raise ValueError("generated roster plan requires at least one slot")

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
            raise RuntimeError("generated roster plan could not be reloaded after save")
        plan_id = int(row["id"])
        self.db.execute(
            "DELETE FROM generated_roster_plan_slot WHERE plan_id = ?",
            (plan_id,),
        )
        for index, slot in enumerate(slots):
            self.db.execute(
                """
                INSERT INTO generated_roster_plan_slot (
                    plan_id, slot_index, slot_name, kind, player_name,
                    character_name, eso_class, build_name, gear_summary, unresolved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan_id,
                    index,
                    slot.slot_name,
                    slot.kind,
                    slot.player_name,
                    slot.character_name,
                    slot.eso_class,
                    slot.build_name,
                    slot.gear_summary,
                    slot.unresolved,
                ),
            )
        self.db.commit()
        return GeneratedRosterPlan(
            plan_id=plan_id,
            name=plan_name,
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

    def load_plan(self, name: str) -> GeneratedRosterPlan | None:
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

    def latest_plan(self) -> GeneratedRosterPlan | None:
        row = self.db.execute(
            """
            SELECT id, name, goal, difficulty
            FROM generated_roster_plan
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None
        return self._load_row(row)

    def _load_row(self, row) -> GeneratedRosterPlan:
        plan_id = int(row["id"])
        slot_rows = self.db.execute(
            """
            SELECT slot_name, kind, player_name, character_name,
                   eso_class, build_name, gear_summary, unresolved
            FROM generated_roster_plan_slot
            WHERE plan_id = ?
            ORDER BY slot_index
            """,
            (plan_id,),
        ).fetchall()
        slots = tuple(
            GeneratedRosterPlanSlot(
                slot_name=str(slot["slot_name"] or ""),
                kind=str(slot["kind"] or ""),
                player_name=str(slot["player_name"] or ""),
                character_name=str(slot["character_name"] or ""),
                eso_class=str(slot["eso_class"] or ""),
                build_name=str(slot["build_name"] or ""),
                gear_summary=str(slot["gear_summary"] or ""),
                unresolved=str(slot["unresolved"] or ""),
            )
            for slot in slot_rows
        )
        return GeneratedRosterPlan(
            plan_id=plan_id,
            name=str(row["name"]),
            goal=str(row["goal"]),
            difficulty=str(row["difficulty"] or ""),
            slots=slots,
        )
