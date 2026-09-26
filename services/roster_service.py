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

import json

from models.roster_model import RosterMember, normalize_roster_role
from models.team_schedule import TeamSchedule, TeamScheduleSlot
from services.eso_database import EsoDatabase
from services.user_database import user_database_for
from services.roster_placeholder_identity import is_personnel_placeholder
from services.personnel_pydantic_schema import (
    ValidationError as PersonnelValidationError,
    validate_personnel_payload,
    validate_team_schedule_payload,
)

class RosterService:
    """Roster read/write access, including many-to-many team membership."""

    _ASSIGNMENT_FIELDS = {
        "primary_assignment",
        "secondary_assignment",
        "gear_needed",
        "notes",
    }

    def __init__(self, database: EsoDatabase):
        self.db = user_database_for(database)
        self._ensure_schema()
        self.remove_placeholder_members()

    def _ensure_schema(self):
        self.db.execute("""
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
            )
        """)
        existing_roster_columns = {
            row["name"] for row in self.db.execute("PRAGMA table_info(roster_member)").fetchall()
        }
        if "canonical_player_id" not in existing_roster_columns:
            self.db.execute(
                "ALTER TABLE roster_member ADD COLUMN canonical_player_id TEXT NOT NULL DEFAULT ''"
            )
        if "canonical_character_id" not in existing_roster_columns:
            self.db.execute(
                "ALTER TABLE roster_member ADD COLUMN canonical_character_id TEXT NOT NULL DEFAULT ''"
            )
        for column in ("discord_name", "youtube", "twitch", "personnel_notes"):
            if column not in existing_roster_columns:
                self.db.execute(
                    f"ALTER TABLE roster_member ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
                )
        # A single player may legitimately have multiple Personnel rows because the
        # current roster model is still player+character shaped. Character identity,
        # not player identity, is the one-to-one bridge at this layer.
        obsolete_player_index = self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'index' "
            "AND name = 'roster_member_canonical_player_id_unique'"
        ).fetchone()
        if obsolete_player_index is not None:
            self.db.execute("DROP INDEX roster_member_canonical_player_id_unique")
        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS roster_member_canonical_player_id_index
            ON roster_member(canonical_player_id)
            WHERE canonical_player_id <> ''
            """
        )
        self.db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS roster_member_canonical_character_id_unique
            ON roster_member(canonical_character_id)
            WHERE canonical_character_id <> ''
            """
        )
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS team (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                raid_days TEXT NOT NULL DEFAULT '',
                raid_time TEXT NOT NULL DEFAULT '',
                timezone TEXT NOT NULL DEFAULT '',
                raid_schedule_json TEXT NOT NULL DEFAULT '',
                current_focus TEXT NOT NULL DEFAULT '',
                discord_url TEXT NOT NULL DEFAULT ''
            )
        """)
        existing_team_columns = {
            row["name"] for row in self.db.execute("PRAGMA table_info(team)").fetchall()
        }
        for column in (
            "raid_days",
            "raid_time",
            "timezone",
            "raid_schedule_json",
            "current_focus",
            "discord_url",
        ):
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
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS roster_member_assignment (
                roster_member_id INTEGER PRIMARY KEY
                    REFERENCES roster_member(id)
                    ON DELETE CASCADE,
                primary_assignment TEXT NOT NULL DEFAULT '',
                secondary_assignment TEXT NOT NULL DEFAULT '',
                gear_needed TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT ''
            )
        """)
        self.db.commit()

    def remove_placeholder_members(self) -> tuple[str, ...]:
        """Delete exact non-player placeholder identities from Personnel.

        This is intentionally conservative: only canonical placeholder labels are
        removed. Real gamertags are never guessed from shape, prefixes, or substrings.
        """
        rows = self.db.execute(
            "SELECT id, player_name FROM roster_member ORDER BY id"
        ).fetchall()
        removed: list[str] = []
        for row in rows:
            player_name = str(row["player_name"] or "").strip()
            if not is_personnel_placeholder(player_name):
                continue
            member_id = int(row["id"])
            self.db.execute(
                "DELETE FROM roster_member_assignment WHERE roster_member_id = ?",
                (member_id,),
            )
            self.db.execute(
                "DELETE FROM team_member WHERE roster_member_id = ?",
                (member_id,),
            )
            self.db.execute("DELETE FROM roster_member WHERE id = ?", (member_id,))
            removed.append(player_name)
        if removed:
            self.db.commit()
        return tuple(removed)

    def list_members(self, *, include_archived: bool = False) -> list[RosterMember]:
        rows = self.db.execute("""
            SELECT
                rm.id,
                rm.player_name,
                rm.character_name,
                rm.eso_class,
                rm.primary_role,
                rm.secondary_role,
                rm.status,
                rm.canonical_player_id,
                rm.canonical_character_id,
                rm.discord_name,
                rm.youtube,
                rm.twitch,
                rm.personnel_notes,
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
            WHERE (? = 1 OR lower(trim(rm.status)) <> 'archived')
            ORDER BY
                rm.player_name COLLATE NOCASE,
                rm.character_name COLLATE NOCASE
        """, (1 if include_archived else 0,)).fetchall()
        return [self._row_to_member(row) for row in rows]

    def list_team_members(self, team_name: str) -> list[RosterMember]:
        """Return active Personnel assigned to one exact saved Team."""
        name = str(team_name or "").strip()
        if not name:
            return []
        rows = self.db.execute("""
            SELECT
                rm.id,
                rm.player_name,
                rm.character_name,
                rm.eso_class,
                rm.primary_role,
                rm.secondary_role,
                rm.status,
                rm.canonical_player_id,
                rm.canonical_character_id,
                rm.discord_name,
                rm.youtube,
                rm.twitch,
                rm.personnel_notes,
                t.name AS team_name
            FROM team t
            INNER JOIN team_member tm ON tm.team_id = t.id
            INNER JOIN roster_member rm ON rm.id = tm.roster_member_id
            WHERE t.name = ? COLLATE NOCASE
              AND lower(trim(rm.status)) <> 'archived'
            ORDER BY
                rm.player_name COLLATE NOCASE,
                rm.character_name COLLATE NOCASE
        """, (name,)).fetchall()
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
                rm.canonical_player_id,
                rm.canonical_character_id,
                rm.discord_name,
                rm.youtube,
                rm.twitch,
                rm.personnel_notes,
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

    def get_member_assignment(self, member_id: int) -> dict[str, str]:
        row = self.db.execute("""
            SELECT primary_assignment, secondary_assignment, gear_needed, notes
            FROM roster_member_assignment
            WHERE roster_member_id = ?
        """, (int(member_id),)).fetchone()
        if row is None:
            return {
                "primary_assignment": "",
                "secondary_assignment": "",
                "gear_needed": "",
                "notes": "",
            }
        return {
            "primary_assignment": row["primary_assignment"] or "",
            "secondary_assignment": row["secondary_assignment"] or "",
            "gear_needed": row["gear_needed"] or "",
            "notes": row["notes"] or "",
        }

    def set_member_assignment_field(self, member_id: int, field: str, value: str) -> None:
        if field not in self._ASSIGNMENT_FIELDS:
            raise ValueError(f"unsupported roster assignment field: {field}")
        member_id = int(member_id)
        if self.get_member(member_id) is None:
            raise ValueError(f"roster member {member_id} does not exist")
        self.db.execute(
            "INSERT OR IGNORE INTO roster_member_assignment (roster_member_id) VALUES (?)",
            (member_id,),
        )
        self.db.execute(
            f"UPDATE roster_member_assignment SET {field} = ? WHERE roster_member_id = ?",
            (str(value or "").strip(), member_id),
        )
        self.db.commit()

    def ensure_team_name(self, team_name: str) -> str:
        """Ensure one durable Roster team identity exists for ``team_name``."""
        name = str(team_name or "").strip()
        if not name:
            raise ValueError("team name is required")
        self.db.execute("INSERT OR IGNORE INTO team (name) VALUES (?)", (name,))
        row = self.db.execute(
            "SELECT name FROM team WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        self.db.commit()
        if row is None:
            raise RuntimeError("team identity could not be reloaded after save")
        return str(row["name"])

    def list_team_names(self) -> list[str]:
        rows = self.db.execute("SELECT name FROM team ORDER BY name COLLATE NOCASE").fetchall()
        return [row["name"] for row in rows]

    @staticmethod
    def _schedule_from_row(row) -> TeamSchedule:
        slots: tuple[TeamScheduleSlot, ...] = ()
        raw_json = row["raid_schedule_json"] if "raid_schedule_json" in row.keys() else ""
        if raw_json:
            try:
                payload = json.loads(raw_json)
                slots = tuple(
                    TeamScheduleSlot(
                        Day=str(item.get("Day") or "").strip(),
                        StartTime=str(item.get("StartTime") or "").strip(),
                        EndTime=str(item.get("EndTime") or "").strip(),
                    )
                    for item in payload
                    if isinstance(item, dict)
                    and str(item.get("Day") or "").strip()
                    and str(item.get("StartTime") or "").strip()
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                slots = ()
        return TeamSchedule(
            TeamName=row["name"] or "",
            RaidDays=row["raid_days"] or "",
            RaidTime=row["raid_time"] or "",
            TimeZone=row["timezone"] or "",
            Slots=slots,
            CurrentFocus=(row["current_focus"] if "current_focus" in row.keys() else "") or "",
            DiscordUrl=(row["discord_url"] if "discord_url" in row.keys() else "") or "",
        )

    def list_team_schedules(self) -> list[TeamSchedule]:
        rows = self.db.execute("""
            SELECT name, raid_days, raid_time, timezone, raid_schedule_json, current_focus, discord_url
            FROM team ORDER BY name COLLATE NOCASE
        """).fetchall()
        return [self._schedule_from_row(row) for row in rows]

    def get_team_schedule(self, team_name: str) -> TeamSchedule | None:
        name = str(team_name or "").strip()
        if not name:
            return None
        row = self.db.execute("""
            SELECT name, raid_days, raid_time, timezone, raid_schedule_json, current_focus, discord_url
            FROM team WHERE name = ? COLLATE NOCASE
        """, (name,)).fetchone()
        if row is None:
            return None
        return self._schedule_from_row(row)

    def set_team_schedule(self, schedule: TeamSchedule) -> None:
        try:
            validated = validate_team_schedule_payload(
                {
                    "team_name": schedule.TeamName,
                    "raid_days": schedule.RaidDays,
                    "raid_time": schedule.RaidTime,
                    "timezone": schedule.TimeZone,
                    "slots": tuple(
                        {
                            "day": slot.Day,
                            "start_time": slot.StartTime,
                            "end_time": slot.EndTime,
                        }
                        for slot in schedule.Slots
                    ),
                    "current_focus": schedule.CurrentFocus,
                    "discord_url": schedule.DiscordUrl,
                }
            )
        except PersonnelValidationError as exc:
            raise ValueError(f"Team schedule save failed Pydantic validation: {exc}") from exc
        name = validated["team_name"]
        slots = tuple(
            TeamScheduleSlot(
                Day=row["day"],
                StartTime=row["start_time"],
                EndTime=row["end_time"],
            )
            for row in validated["slots"]
        )
        raid_days = validated["raid_days"]
        raid_time = validated["raid_time"]
        if slots:
            raid_days = ", ".join(slot.Day for slot in slots)
            raid_time = slots[0].StartTime
        slots_json = json.dumps([
            {"Day": slot.Day, "StartTime": slot.StartTime, "EndTime": slot.EndTime}
            for slot in slots
        ])
        self.db.execute("INSERT OR IGNORE INTO team (name) VALUES (?)", (name,))
        self.db.execute("""
            UPDATE team
            SET raid_days = ?, raid_time = ?, timezone = ?, raid_schedule_json = ?, current_focus = ?, discord_url = ?
            WHERE name = ? COLLATE NOCASE
        """, (
            raid_days,
            raid_time,
            validated["timezone"],
            slots_json,
            validated["current_focus"],
            validated["discord_url"],
            name,
        ))
        self.db.commit()
        saved = self.get_team_schedule(name)
        if saved is None:
            raise RuntimeError("Team schedule could not be reloaded after save")

    def delete_team(self, team_name: str) -> bool:
        name = str(team_name or "").strip()
        if not name:
            return False
        row = self.db.execute(
            "SELECT id FROM team WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        if row is None:
            return False
        team_id = int(row["id"])
        self.db.execute("DELETE FROM team_member WHERE team_id = ?", (team_id,))
        self.db.execute("DELETE FROM team WHERE id = ?", (team_id,))
        self.db.commit()
        return True

    def create_member(self, member: RosterMember) -> int:
        member = self._validated_member(member)
        if is_personnel_placeholder(member.PlayerName):
            raise ValueError(
                f"{member.PlayerName!r} is a planning placeholder, not a Personnel player"
            )
        cursor = self.db.execute("""
            INSERT INTO roster_member (
                player_name, character_name, eso_class,
                primary_role, secondary_role, status,
                canonical_player_id, canonical_character_id,
                discord_name, youtube, twitch, personnel_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            member.PlayerName, member.CharacterName, member.EsoClass,
            normalize_roster_role(member.PrimaryRole),
            normalize_roster_role(member.SecondaryRole),
            member.Status or "Active",
            str(member.CanonicalPlayerId or "").strip(),
            str(member.CanonicalCharacterId or "").strip(),
            str(member.DiscordName or "").strip(),
            str(member.YouTube or "").strip(),
            str(member.Twitch or "").strip(),
            str(member.PersonnelNotes or "").strip(),
        ))
        member_id = cursor.lastrowid
        self._set_member_teams(member_id, member.Team)
        self.db.commit()
        saved = self.get_member(int(member_id))
        if saved is None:
            raise RuntimeError("Personnel record could not be reloaded after create")
        return member_id

    def update_member(self, member: RosterMember):
        member = self._validated_member(member)
        if member.Id is None:
            raise ValueError("Cannot update a roster member with no Id.")
        if is_personnel_placeholder(member.PlayerName):
            raise ValueError(
                f"{member.PlayerName!r} is a planning placeholder, not a Personnel player"
            )
        self.db.execute("""
            UPDATE roster_member SET
                player_name = ?, character_name = ?, eso_class = ?,
                primary_role = ?, secondary_role = ?, status = ?,
                canonical_player_id = ?, canonical_character_id = ?,
                discord_name = ?, youtube = ?, twitch = ?,
                personnel_notes = ?
            WHERE id = ?
        """, (
            member.PlayerName, member.CharacterName, member.EsoClass,
            normalize_roster_role(member.PrimaryRole),
            normalize_roster_role(member.SecondaryRole),
            member.Status or "Active",
            str(member.CanonicalPlayerId or "").strip(),
            str(member.CanonicalCharacterId or "").strip(),
            str(member.DiscordName or "").strip(),
            str(member.YouTube or "").strip(),
            str(member.Twitch or "").strip(),
            str(member.PersonnelNotes or "").strip(),
            member.Id,
        ))
        self._set_member_teams(member.Id, member.Team)
        self.db.commit()
        saved = self.get_member(int(member.Id))
        if saved is None:
            raise RuntimeError("Personnel record could not be reloaded after update")

    def set_member_status(self, member_id: int, status: str) -> RosterMember:
        member_id = int(member_id)
        member = self.get_member(member_id)
        if member is None:
            raise ValueError(f"roster member {member_id} does not exist")
        value = str(status or "").strip() or "Active"
        self.db.execute(
            "UPDATE roster_member SET status = ? WHERE id = ?",
            (value, member_id),
        )
        self.db.commit()
        updated = self.get_member(member_id)
        if updated is None:
            raise RuntimeError(f"roster member {member_id} could not be reloaded")
        return updated

    def archive_member(self, member_id: int) -> RosterMember:
        """Retire a Personnel record without deleting identity or history."""
        return self.set_member_status(member_id, "Archived")

    def restore_member(self, member_id: int) -> RosterMember:
        """Return an archived Personnel record to active service."""
        member = self.get_member(int(member_id))
        if member is None:
            raise ValueError(f"roster member {member_id} does not exist")
        if str(member.Status or "").strip().casefold() != "archived":
            raise ValueError("only archived Personnel records can be restored")
        return self.set_member_status(int(member_id), "Active")

    def delete_member(self, member_id: int):
        """Permanently delete a Personnel record only after it has been archived."""
        member_id = int(member_id)
        member = self.get_member(member_id)
        if member is None:
            return
        if str(member.Status or "").strip().casefold() != "archived":
            raise ValueError(
                "Personnel must be archived before it can be permanently deleted"
            )
        self.db.execute(
            "DELETE FROM roster_member_assignment WHERE roster_member_id = ?",
            (member_id,),
        )
        optional_tables = {
            row["name"]
            for row in self.db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if "roster_assignment_context" in optional_tables:
            self.db.execute(
                "DELETE FROM roster_assignment_context WHERE roster_member_id = ?",
                (member_id,),
            )
        if "roster_player_alias" in optional_tables:
            self.db.execute(
                "DELETE FROM roster_player_alias WHERE roster_member_id = ?",
                (member_id,),
            )
        self.db.execute("DELETE FROM team_member WHERE roster_member_id = ?", (member_id,))
        self.db.execute("DELETE FROM roster_member WHERE id = ?", (member_id,))
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

    def add_member_to_team(self, member_id: int, team_name: str) -> None:
        """Add one Personnel record to one Team without disturbing other memberships."""
        member_id = int(member_id)
        name = str(team_name or "").strip()
        if member_id <= 0:
            raise ValueError("member_id must be positive")
        if not name:
            return
        if self.get_member(member_id) is None:
            raise ValueError(f"roster member {member_id} does not exist")
        self.db.execute("INSERT OR IGNORE INTO team (name) VALUES (?)", (name,))
        row = self.db.execute(
            "SELECT id FROM team WHERE name = ? COLLATE NOCASE",
            (name,),
        ).fetchone()
        if row is None:
            raise RuntimeError("team identity could not be resolved")
        self.db.execute(
            """
            INSERT OR IGNORE INTO team_member (roster_member_id, team_id)
            VALUES (?, ?)
            """,
            (member_id, int(row["id"])),
        )
        self.db.commit()

    def _set_member_teams(self, member_id: int, team_names: str):
        self.db.execute("DELETE FROM team_member WHERE roster_member_id = ?", (member_id,))
        for team_name in self._parse_team_names(team_names):
            self.db.execute("INSERT OR IGNORE INTO team (name) VALUES (?)", (team_name,))
            team_row = self.db.execute(
                "SELECT id FROM team WHERE name = ? COLLATE NOCASE", (team_name,)
            ).fetchone()
            if team_row is None:
                continue
            self.db.execute("""
                INSERT OR IGNORE INTO team_member (roster_member_id, team_id)
                VALUES (?, ?)
            """, (member_id, team_row["id"]))

    @staticmethod
    def _row_to_member(row) -> RosterMember:
        return RosterMember(
            Id=row["id"], PlayerName=row["player_name"] or "",
            CharacterName=row["character_name"] or "", EsoClass=row["eso_class"] or "",
            PrimaryRole=row["primary_role"] or "", SecondaryRole=row["secondary_role"] or "",
            Status=row["status"] or "Active", Team=row["team_name"] or "",
            CanonicalPlayerId=row["canonical_player_id"] or "",
            CanonicalCharacterId=row["canonical_character_id"] or "",
            DiscordName=row["discord_name"] or "",
            YouTube=row["youtube"] or "",
            Twitch=row["twitch"] or "",
            PersonnelNotes=row["personnel_notes"] or "",
        )
