from __future__ import annotations

"""Create the deterministic first-install FoundryDock planning seed.

This database is intentionally reference/demo planning state, not a developer's
personal user database. It exists so a fresh packaged EXE opens with populated
raid-planning pages and a meaningful Coverage view.

Runtime copies this database only when the recipient has no existing
foundrydock.db. Existing user data is never replaced.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_repository import RaidPlanRepository


TEAM_NAME = "FoundryDock Reference Team"
PLAN_ID = "foundrydock-reference-raid"
PLAN_NAME = "FoundryDock Reference Raid"


ROSTER = (
    # name, character, class, role, primary assignment, secondary assignment, gear
    ("Reference Tank A", "Bulwark", "Dragonknight", "Tank", "Major Breach", "Crusher",
     ("Pearlescent Ward", "Turning Tide", "Nazaray")),
    ("Reference Tank B", "Warden", "Necromancer", "Tank", "Minor Courage", "Major Vulnerability",
     ("Crimson Oath's Rive", "Claw of Yolnahkriin", "Archdruid Devyric")),
    ("Reference Healer A", "Lantern", "Warden", "Healer", "Major Courage", "Minor Resolve",
     ("Spell Power Cure", "Powerful Assault", "Spaulder of Ruin")),
    ("Reference Healer B", "Compass", "Arcanist", "Healer", "Major Slayer", "Minor Intellect",
     ("Roaring Opportunist", "Jorvuld's Guidance", "Symphony of Blades")),
    ("Reference DD A", "Ember", "Dragonknight", "DD", "Touch of Z'en", "Minor Brutality",
     ("Z'en's Redress",)),
    ("Reference DD B", "Glass", "Nightblade", "DD", "Way of Martial Knowledge", "Minor Savagery",
     ("Way of Martial Knowledge",)),
    ("Reference DD C", "Static", "Sorcerer", "DD", "Elemental Catalyst", "Minor Prophecy",
     ("Elemental Catalyst",)),
    ("Reference DD D", "Frost", "Warden", "DD", "Minor Brittle", "Minor Vulnerability",
     ()),
    ("Reference DD E", "Horn", "Necromancer", "DD", "Major Force", "Minor Maim",
     ()),
    ("Reference DD F", "Torch", "Templar", "DD", "Minor Sorcery", "Minor Berserk",
     ()),
    ("Reference DD G", "Ink", "Arcanist", "DD", "Minor Fortitude", "Minor Endurance",
     ()),
    ("Reference DD H", "Shade", "Nightblade", "DD", "Minor Lifesteal", "Magickasteal",
     ()),
)


def _connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def _create_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS roster_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            character_name TEXT,
            eso_class TEXT,
            primary_role TEXT,
            secondary_role TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            canonical_player_id TEXT NOT NULL DEFAULT '',
            canonical_character_id TEXT NOT NULL DEFAULT '',
            discord_name TEXT NOT NULL DEFAULT '',
            youtube TEXT NOT NULL DEFAULT '',
            twitch TEXT NOT NULL DEFAULT '',
            personnel_notes TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS team (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            raid_days TEXT NOT NULL DEFAULT '',
            raid_time TEXT NOT NULL DEFAULT '',
            timezone TEXT NOT NULL DEFAULT '',
            raid_schedule_json TEXT NOT NULL DEFAULT '',
            current_focus TEXT NOT NULL DEFAULT '',
            discord_url TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS team_member (
            roster_member_id INTEGER NOT NULL
                REFERENCES roster_member(id) ON DELETE CASCADE,
            team_id INTEGER NOT NULL
                REFERENCES team(id) ON DELETE CASCADE,
            PRIMARY KEY (roster_member_id, team_id)
        );

        CREATE TABLE IF NOT EXISTS roster_member_assignment (
            roster_member_id INTEGER PRIMARY KEY
                REFERENCES roster_member(id) ON DELETE CASCADE,
            primary_assignment TEXT NOT NULL DEFAULT '',
            secondary_assignment TEXT NOT NULL DEFAULT '',
            gear_needed TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS build_catalog (
            singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def _seat(index: int) -> str:
    if index == 0:
        return "tank-1"
    if index == 1:
        return "tank-2"
    if index == 2:
        return "healer-1"
    if index == 3:
        return "healer-2"
    return f"dd-{index - 3}"


def create_seed(destination: Path) -> Path:
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)

    player_rows = []
    character_rows = []
    build_rows = []
    plan_members = []

    with _connect(destination) as db:
        _create_schema(db)
        raid_schedule = json.dumps(
            [
                {"Day": "Monday", "StartTime": "9:00 PM", "EndTime": "11:00 PM"},
                {"Day": "Wednesday", "StartTime": "9:00 PM", "EndTime": "11:00 PM"},
            ]
        )
        cursor = db.execute(
            """
            INSERT INTO team(
                name, raid_days, raid_time, timezone, raid_schedule_json,
                current_focus, discord_url
            ) VALUES (?, ?, ?, ?, ?, ?, '')
            """,
            (
                TEAM_NAME,
                "Monday, Wednesday",
                "9:00 PM",
                "EST",
                raid_schedule,
                "Reference coverage and comp-planning workspace",
            ),
        )
        team_id = int(cursor.lastrowid)

        for index, (
            player_name,
            character_name,
            eso_class,
            role,
            primary,
            secondary,
            planned_gear,
        ) in enumerate(ROSTER):
            player_id = f"reference-player-{index + 1}"
            character_id = f"reference-character-{index + 1}"
            build_id = f"reference-build-{index + 1}"
            member_cursor = db.execute(
                """
                INSERT INTO roster_member(
                    player_name, character_name, eso_class, primary_role,
                    secondary_role, status, canonical_player_id,
                    canonical_character_id, personnel_notes
                ) VALUES (?, ?, ?, ?, '', 'Active', ?, ?, ?)
                """,
                (
                    player_name,
                    character_name,
                    eso_class,
                    role,
                    player_id,
                    character_id,
                    "Reference seed data. Replace with your own Personnel.",
                ),
            )
            roster_member_id = int(member_cursor.lastrowid)
            db.execute(
                "INSERT INTO team_member(roster_member_id, team_id) VALUES (?, ?)",
                (roster_member_id, team_id),
            )
            db.execute(
                """
                INSERT INTO roster_member_assignment(
                    roster_member_id, primary_assignment, secondary_assignment,
                    gear_needed, notes
                ) VALUES (?, ?, ?, '', ?)
                """,
                (
                    roster_member_id,
                    primary,
                    secondary,
                    "Reference provider assignment.",
                ),
            )

            player_rows.append(
                {
                    "player_id": player_id,
                    "gamertag": player_name,
                    "display_name": player_name,
                }
            )
            character_rows.append(
                {
                    "character_id": character_id,
                    "player_id": player_id,
                    "name": character_name,
                    "gamertag": player_name,
                    "eso_class": eso_class,
                    "role": role,
                }
            )
            build_rows.append(
                {
                    "build_id": build_id,
                    "character_id": character_id,
                    "player_id": player_id,
                    "name": f"{character_name} Reference",
                    "gamertag": player_name,
                    "character_name": character_name,
                    "eso_class": eso_class,
                    "role": role,
                    "planned_gear_sets": list(planned_gear),
                    "planned_skills": [],
                    "source": {
                        "kind": "reference_seed",
                        "plan_id": PLAN_ID,
                        "plan_name": PLAN_NAME,
                        "seat_id": _seat(index),
                    },
                }
            )
            plan_members.append(
                RaidPlanMember(
                    seat_id=_seat(index),
                    gamertag=player_name,
                    roster_member_id=roster_member_id,
                    player_id=player_id,
                    character_id=character_id,
                    character_name=character_name,
                    role=role,
                    eso_class=eso_class,
                    selected_build_id=build_id,
                    selected_build_name=f"{character_name} Reference",
                    build_source_kind="reference_seed",
                    build_source_name="FoundryDock first-install reference data",
                    planned_gear_sets=tuple(planned_gear),
                    primary_assignment=primary,
                    secondary_assignment=secondary,
                    assignment_source="FoundryDock reference seed",
                    notes="Reference planning row. Replace with live raid data.",
                )
            )

        catalog = {
            "schema_version": 4,
            "players": player_rows,
            "characters": character_rows,
            "builds": build_rows,
            "team_assignments": [],
        }
        db.execute(
            "INSERT INTO build_catalog(singleton_id, payload_json) VALUES (1, ?)",
            (json.dumps(catalog, ensure_ascii=False, sort_keys=True),),
        )
        db.commit()

    RaidPlanRepository(destination).save(
        RaidPlan(
            plan_id=PLAN_ID,
            trial_id="sunspire",
            name=PLAN_NAME,
            team_name=TEAM_NAME,
            difficulty="Veteran Hardmode",
            status="planning",
            plan_note=(
                "First-install reference plan. It exists so Raid Plan, Assignments, "
                "Comp Builder, Readiness, and Coverage are populated on a fresh EXE."
            ),
            members=tuple(plan_members),
        )
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    path = create_seed(args.destination)
    print(f"release_user_seed={path}")
    print(f"team={TEAM_NAME}")
    print(f"plan={PLAN_NAME}")
    print(f"members={len(ROSTER)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
