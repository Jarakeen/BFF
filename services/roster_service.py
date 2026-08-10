# ==================================================
# Black Feather Foundry
#
# File:
# services/roster_service.py
#
# Purpose:
# Read/write access to the raid roster.
#
# Wraps the existing EsoDatabase connection -
# does not open a second connection to eso.db.
#
# Schema:
#
#   roster_member
#       id             INTEGER PRIMARY KEY
#       player_name    TEXT
#       character_name TEXT
#       eso_class      TEXT
#       primary_role   TEXT
#       secondary_role TEXT
#       status         TEXT
#
#   team
#       id     INTEGER PRIMARY KEY
#       name   TEXT UNIQUE
#
#   team_member
#       roster_member_id  INTEGER
#       team_id           INTEGER
#
# team_member is a many-to-many join, so a roster
# member can belong to more than one team later
# without a schema change. The current UI only
# manages a single team per member (set_member_team
# replaces whatever membership rows exist), but the
# schema does not assume that will always be true.
#
# ==================================================

from __future__ import annotations

from models.roster_model import RosterMember

from services.eso_database import EsoDatabase


class RosterService:
    """
    Roster read/write access.
    """

    def __init__(self, database: EsoDatabase):

        self.db = database

        self._ensure_schema()

    # --------------------------------------------------
    # Schema
    # --------------------------------------------------

    def _ensure_schema(self):

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS roster_member (

                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name     TEXT NOT NULL,
                character_name  TEXT,
                eso_class       TEXT,
                primary_role    TEXT,
                secondary_role  TEXT,
                status          TEXT NOT NULL DEFAULT 'Active'
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS team (

                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT NOT NULL UNIQUE
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS team_member (

                roster_member_id  INTEGER NOT NULL
                    REFERENCES roster_member(id)
                    ON DELETE CASCADE,

                team_id  INTEGER NOT NULL
                    REFERENCES team(id)
                    ON DELETE CASCADE,

                PRIMARY KEY (
                    roster_member_id,
                    team_id
                )
            )
        """)

        self.db.commit()

    # --------------------------------------------------
    # Read
    # --------------------------------------------------

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

                (
                    SELECT t.name
                    FROM team_member tm
                    INNER JOIN team t
                        ON t.id = tm.team_id
                    WHERE tm.roster_member_id = rm.id
                    ORDER BY t.name
                    LIMIT 1
                ) AS team_name

            FROM roster_member rm

            ORDER BY
                rm.player_name COLLATE NOCASE,
                rm.character_name COLLATE NOCASE
        """).fetchall()

        return [
            self._row_to_member(row)
            for row in rows
        ]

    def get_member(
        self,
        member_id: int,
    ) -> RosterMember | None:

        row = self.db.execute(
            """
            SELECT
                rm.id,
                rm.player_name,
                rm.character_name,
                rm.eso_class,
                rm.primary_role,
                rm.secondary_role,
                rm.status,

                (
                    SELECT t.name
                    FROM team_member tm
                    INNER JOIN team t
                        ON t.id = tm.team_id
                    WHERE tm.roster_member_id = rm.id
                    ORDER BY t.name
                    LIMIT 1
                ) AS team_name

            FROM roster_member rm
            WHERE rm.id = ?
            """,
            (member_id,),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_member(row)

    def list_team_names(self) -> list[str]:

        rows = self.db.execute("""
            SELECT name
            FROM team
            ORDER BY name COLLATE NOCASE
        """).fetchall()

        return [row["name"] for row in rows]

    # --------------------------------------------------
    # Write
    # --------------------------------------------------

    def create_member(
        self,
        member: RosterMember,
    ) -> int:

        cursor = self.db.execute(
            """
            INSERT INTO roster_member (
                player_name,
                character_name,
                eso_class,
                primary_role,
                secondary_role,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                member.PlayerName,
                member.CharacterName,
                member.EsoClass,
                member.PrimaryRole,
                member.SecondaryRole,
                member.Status or "Active",
            ),
        )

        member_id = cursor.lastrowid

        self._set_member_team(
            member_id,
            member.Team,
        )

        self.db.commit()

        return member_id

    def update_member(
        self,
        member: RosterMember,
    ):

        if member.Id is None:
            raise ValueError(
                "Cannot update a roster member "
                "with no Id."
            )

        self.db.execute(
            """
            UPDATE roster_member
            SET
                player_name = ?,
                character_name = ?,
                eso_class = ?,
                primary_role = ?,
                secondary_role = ?,
                status = ?
            WHERE id = ?
            """,
            (
                member.PlayerName,
                member.CharacterName,
                member.EsoClass,
                member.PrimaryRole,
                member.SecondaryRole,
                member.Status or "Active",
                member.Id,
            ),
        )

        self._set_member_team(
            member.Id,
            member.Team,
        )

        self.db.commit()

    def delete_member(
        self,
        member_id: int,
    ):

        self.db.execute(
            "DELETE FROM team_member WHERE roster_member_id = ?",
            (member_id,),
        )

        self.db.execute(
            "DELETE FROM roster_member WHERE id = ?",
            (member_id,),
        )

        self.db.commit()

    # --------------------------------------------------
    # Teams
    # --------------------------------------------------

    def _set_member_team(
        self,
        member_id: int,
        team_name: str,
    ):
        """
        Replaces this member's team membership rows with
        a single membership in `team_name` (creating the
        team if it doesn't exist yet). Passing an empty
        team_name just clears membership.

        This is a UI-level simplification, not a schema
        limitation - team_member supports multiple teams
        per member whenever the UI needs to expose that.
        """

        self.db.execute(
            "DELETE FROM team_member WHERE roster_member_id = ?",
            (member_id,),
        )

        team_name = (team_name or "").strip()

        if not team_name:
            return

        self.db.execute(
            "INSERT OR IGNORE INTO team (name) VALUES (?)",
            (team_name,),
        )

        team_row = self.db.execute(
            "SELECT id FROM team WHERE name = ?",
            (team_name,),
        ).fetchone()

        self.db.execute(
            """
            INSERT OR IGNORE INTO team_member (
                roster_member_id,
                team_id
            )
            VALUES (?, ?)
            """,
            (
                member_id,
                team_row["id"],
            ),
        )

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

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
