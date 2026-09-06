# ==================================================
# Black Feather Foundry
#
# File:
# services/roster_service.py
#
# Purpose:
# Read/write access to the raid roster.
#
# ==================================================

from __future__ import annotations

from models.roster_model import RosterMember
from models.team_schedule import TeamSchedule
from services.eso_database import EsoDatabase


class RosterService:
    """Roster read/write access, including many-to-many team membership."""

    def __init__(self, database: EsoDatabase):
        self.db = database
        self._ensure_schema()

    def _ensure_schema(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS roster_member (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                character_name TEXT,
                eso_class TEXT,
                primary_role TEXT,
                secondary_role TEXT,
                status TEXT NOT NULL DEFAULT 'Active'
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS team (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                raid_days TEXT NOT NULL DEFAULT '',
                raid_time TEXT NOT NULL DEFAULT '',
                timezone TEXT NOT NULL DEFAULT ''
            )
        """)
        existing_team_columns = {
            row["name"] for row in self.db.execute("PRAGMA table_info(team)").fetchall()
        }
        for column in ("raid_days", "raid_time", "timezone"):
            if column not in existing_team_columns:
                self.db.execute(
                    f"ALTER TABLE team ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
                )
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS team_member (
                roster_member_id INTEGER NOT NULL
                    REFERENCES roster_member(id)
                    ON DELETE CASCADE,
                team_id INTEGER NOT NULL
                    REFERENCES team(id)
                    ON DELETE CASCADE,
                PRIMARY KEY (roster_member_id, team_id)
            )
        """)
        self.db.commit()

    def list_members(self) -> list[RosterMember]:
        rows = self.db.execute("""
            SELECT
                rm.id,
                rm.player_name,
                rm.character_name,
                rm.eso_class,
                rm.primary_role,
                rm.secondary_role,
                rm.status,
                COALESCE((
                    SELECT GROUP_CONCAT(team_name, ', ')
                    FROM (
                        SELECT t.name AS team_name
                        FROM team_member tm
                        INNER JOIN team t ON t.id = tm.team_id
                        WHERE tm.roster_member_id = rm.id
                        ORDER BY t.name COLLATE NOCASE
                    )
                ), '') AS team_name
            FROM roster_member rm
            ORDER BY
                rm.player_name COLLATE NOCASE,
                rm.character_name COLLATE NOCASE
        """).fetchall()
        return [self._row_to_member(row) for row in rows]

    def get_member(self, member_id: int) -> RosterMember | None:
        row = self.db.execute("""
            SELECT
                rm.id,
                rm.player_name,
                rm.character_name,
                rm.eso_class,
                rm.primary_role,
                rm.secondary_role,
                rm.status,
                COALESCE((
                    SELECT GROUP_CONCAT(team_name, ', ')
                    FROM (
                        SELECT t.name AS team_name
                        FROM team_member tm
                        INNER JOIN team t ON t.id = tm.team_id
                        WHERE tm.roster_member_id = rm.id
                        ORDER BY t.name COLLATE NOCASE
                    )
                ), '') AS team_name
            FROM roster_member rm
            WHERE rm.id = ?
        """, (member_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_member(row)

    def ensure_team_name(self, team_name: str) -> str:
        """Ensure one durable Roster team identity exists for ``team_name``.

        Generated plans and roster membership are separate persistence concerns, but
        they share this user-facing team identity. This method is deliberately
        idempotent and does not fabricate membership for recruitment-only chairs.
        """

        name = str(team_name or "").strip()
        if not name:
            raise ValueError("team name is required")
        self.db.execute(
            "INSERT OR IGNORE INTO team (name) VALUES (?)",
            (name,),
        )
        row = self.db.execute(
            "SELECT name FROM team WHERE name = ? COLLATE NOCASE",
            (name,),
        ).fetchone()
        self.db.commit()
        if row is None:
            raise RuntimeError("team identity could not be reloaded after save")
        return str(row["name"])

    def list_team_names(self) -> list[str]:
        rows = self.db.execute("""
            SELECT name
            FROM team
            ORDER BY name COLLATE NOCASE
        """).fetchall()
        return [row["name"] for row in rows]

    def list_team_schedules(self) -> list[TeamSchedule]:
        rows = self.db.execute("""
            SELECT name, raid_days, raid_time, timezone
            FROM team
            ORDER BY name COLLATE NOCASE
        """).fetchall()
        return [
            TeamSchedule(
                TeamName=row["name"] or "",
                RaidDays=row["raid_days"] or "",
                RaidTime=row["raid_time"] or "",
                TimeZone=row["timezone"] or "",
            )
            for row in rows
        ]

    def get_team_schedule(self, team_name: str) -> TeamSchedule | None:
        name = str(team_name or "").strip()
        if not name:
            return None
        row = self.db.execute("""
            SELECT name, raid_days, raid_time, timezone
            FROM team
            WHERE name = ? COLLATE NOCASE
        """, (name,)).fetchone()
        if row is None:
            return None
        return TeamSchedule(
            TeamName=row["name"] or "",
            RaidDays=row["raid_days"] or "",
            RaidTime=row["raid_time"] or "",
            TimeZone=row["timezone"] or "",
        )

    def set_team_schedule(self, schedule: TeamSchedule) -> None:
        name = str(schedule.TeamName or "").strip()
        if not name:
            raise ValueError("Team name is required before a raid schedule can be saved.")
        self.db.execute(
            "INSERT OR IGNORE INTO team (name) VALUES (?)",
            (name,),
        )
        self.db.execute("""
            UPDATE team
            SET raid_days = ?, raid_time = ?, timezone = ?
            WHERE name = ? COLLATE NOCASE
        """, (
            str(schedule.RaidDays or "").strip(),
            str(schedule.RaidTime or "").strip(),
            str(schedule.TimeZone or "").strip(),
            name,
        ))
        self.db.commit()

    def delete_team(self, team_name: str) -> bool:
        """Delete one team identity without deleting roster people.

        Team memberships and the saved raid schedule belong to the team record, so
        they are removed with it. Roster members, characters, and builds remain.
        """
        name = str(team_name or "").strip()
        if not name:
            return False
        row = self.db.execute(
            "SELECT id FROM team WHERE name = ? COLLATE NOCASE",
            (name,),
        ).fetchone()
        if row is None:
            return False
        team_id = int(row["id"])
        self.db.execute("DELETE FROM team_member WHERE team_id = ?", (team_id,))
        self.db.execute("DELETE FROM team WHERE id = ?", (team_id,))
        self.db.commit()
        return True

    def create_member(self, member: RosterMember) -> int:
        cursor = self.db.execute("""
            INSERT INTO roster_member (
                player_name, character_name, eso_class,
                primary_role, secondary_role, status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            member.PlayerName,
            member.CharacterName,
            member.EsoClass,
            member.PrimaryRole,
            member.SecondaryRole,
            member.Status or "Active",
        ))
        member_id = cursor.lastrowid
        self._set_member_teams(member_id, member.Team)
        self.db.commit()
        return member_id

    def update_member(self, member: RosterMember):
        if member.Id is None:
            raise ValueError("Cannot update a roster member with no Id.")
        self.db.execute("""
            UPDATE roster_member
            SET
                player_name = ?,
                character_name = ?,
                eso_class = ?,
                primary_role = ?,
                secondary_role = ?,
                status = ?
            WHERE id = ?
        """, (
            member.PlayerName,
            member.CharacterName,
            member.EsoClass,
            member.PrimaryRole,
            member.SecondaryRole,
            member.Status or "Active",
            member.Id,
        ))
        self._set_member_teams(member.Id, member.Team)
        self.db.commit()

    def delete_member(self, member_id: int):
        self.db.execute(
            "DELETE FROM team_member WHERE roster_member_id = ?",
            (member_id,),
        )
        self.db.execute(
            "DELETE FROM roster_member WHERE id = ?",
            (member_id,),
        )
        self.db.commit()

    @staticmethod
    def _parse_team_names(value: str) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for raw in (value or "").split(","):
            name = raw.strip()
            key = name.casefold()
            if not name or key in seen:
                continue
            seen.add(key)
            result.append(name)
        return result

    def _set_member_teams(self, member_id: int, team_names: str):
        """Replace this member's memberships with the supplied comma-separated teams."""
        self.db.execute(
            "DELETE FROM team_member WHERE roster_member_id = ?",
            (member_id,),
        )

        for team_name in self._parse_team_names(team_names):
            self.db.execute(
                "INSERT OR IGNORE INTO team (name) VALUES (?)",
                (team_name,),
            )
            team_row = self.db.execute(
                "SELECT id FROM team WHERE name = ? COLLATE NOCASE",
                (team_name,),
            ).fetchone()
            if team_row is None:
                continue
            self.db.execute("""
                INSERT OR IGNORE INTO team_member (
                    roster_member_id, team_id
                )
                VALUES (?, ?)
            """, (member_id, team_row["id"]))

    @staticmethod
    def _row_to_member(row) -> RosterMember:
        return RosterMember(
            Id=row["id"],
            PlayerName=row["player_name"] or "",
            CharacterName=row["character_name"] or "",
            EsoClass=row["eso_class"] or "",
            PrimaryRole=row["primary_role"] or "",
            SecondaryRole=row["secondary_role"] or "",
            Status=row["status"] or "Active",
            Team=row["team_name"] or "",
        )
