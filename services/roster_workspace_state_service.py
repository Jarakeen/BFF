from __future__ import annotations

"""Durable user-owned state for the rebuilt Roster workspace.

This service deliberately owns only user workflow state that is not canonical ESO
reference data and is not already owned by BuildCatalog or RosterService:

* weekly availability notes/status per roster member;
* recruitment candidates and their lifecycle;
* archive records for retired roster/team planning objects.

All schema changes are additive. The service never resets or replaces ``eso.db``.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json

from services.eso_database import EsoDatabase
from services.user_database import user_database_for
from services.roster_workspace_pydantic_schema import (
    validate_recruitment_candidate,
    validate_roster_archive,
    validate_roster_availability,
)


_AVAILABILITY_STATES = frozenset({"available", "unavailable", "maybe", "late", "tentative", "unknown"})
_RECRUITMENT_STATES = frozenset({"new", "review", "interview", "trial", "accepted", "declined", "archived"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class MemberAvailability:
    roster_member_id: int
    monday: str = "unknown"
    tuesday: str = "unknown"
    wednesday: str = "unknown"
    thursday: str = "unknown"
    friday: str = "unknown"
    saturday: str = "unknown"
    sunday: str = "unknown"
    preferred_times: str = ""
    notes: str = ""

    def normalized(self) -> "MemberAvailability":
        def state(value: str) -> str:
            key = _clean(value).casefold()
            return key if key in _AVAILABILITY_STATES else "unknown"

        return MemberAvailability(
            roster_member_id=int(self.roster_member_id),
            monday=state(self.monday),
            tuesday=state(self.tuesday),
            wednesday=state(self.wednesday),
            thursday=state(self.thursday),
            friday=state(self.friday),
            saturday=state(self.saturday),
            sunday=state(self.sunday),
            preferred_times=_clean(self.preferred_times),
            notes=_clean(self.notes),
        )


@dataclass(frozen=True)
class RecruitmentCandidate:
    id: int | None = None
    player_name: str = ""
    character_name: str = ""
    desired_role: str = ""
    eso_class: str = ""
    target_team: str = ""
    availability: str = ""
    status: str = "new"
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    def normalized(self) -> "RecruitmentCandidate":
        status = _clean(self.status).casefold()
        if status not in _RECRUITMENT_STATES:
            status = "new"
        return RecruitmentCandidate(
            id=self.id,
            player_name=_clean(self.player_name),
            character_name=_clean(self.character_name),
            desired_role=_clean(self.desired_role),
            eso_class=_clean(self.eso_class),
            target_team=_clean(self.target_team),
            availability=_clean(self.availability),
            status=status,
            notes=_clean(self.notes),
            created_at=_clean(self.created_at),
            updated_at=_clean(self.updated_at),
        )


@dataclass(frozen=True)
class ArchiveRecord:
    id: int | None = None
    entity_type: str = ""
    entity_key: str = ""
    display_name: str = ""
    reason: str = ""
    related_team: str = ""
    archived_at: str = ""
    payload: dict | None = None


class RosterWorkspaceStateService:
    """Additive persistence for roster workflow state."""

    def __init__(self, db: EsoDatabase) -> None:
        self.db = user_database_for(db)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS roster_member_availability (
                roster_member_id INTEGER PRIMARY KEY,
                monday TEXT NOT NULL DEFAULT 'unknown',
                tuesday TEXT NOT NULL DEFAULT 'unknown',
                wednesday TEXT NOT NULL DEFAULT 'unknown',
                thursday TEXT NOT NULL DEFAULT 'unknown',
                friday TEXT NOT NULL DEFAULT 'unknown',
                saturday TEXT NOT NULL DEFAULT 'unknown',
                sunday TEXT NOT NULL DEFAULT 'unknown',
                preferred_times TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(roster_member_id) REFERENCES roster_member(id) ON DELETE CASCADE
            )
            """
        )
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS roster_recruitment_candidate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL DEFAULT '',
                character_name TEXT NOT NULL DEFAULT '',
                desired_role TEXT NOT NULL DEFAULT '',
                eso_class TEXT NOT NULL DEFAULT '',
                target_team TEXT NOT NULL DEFAULT '',
                availability TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'new',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS roster_archive_record (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_key TEXT NOT NULL DEFAULT '',
                display_name TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                related_team TEXT NOT NULL DEFAULT '',
                archived_at TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        self.db.commit()

    def availability_for(self, roster_member_id: int) -> MemberAvailability:
        row = self.db.execute(
            """
            SELECT roster_member_id, monday, tuesday, wednesday, thursday,
                   friday, saturday, sunday, preferred_times, notes
            FROM roster_member_availability
            WHERE roster_member_id = ?
            """,
            (int(roster_member_id),),
        ).fetchone()
        if row is None:
            return MemberAvailability(roster_member_id=int(roster_member_id))
        return MemberAvailability(
            roster_member_id=int(row["roster_member_id"]),
            monday=row["monday"],
            tuesday=row["tuesday"],
            wednesday=row["wednesday"],
            thursday=row["thursday"],
            friday=row["friday"],
            saturday=row["saturday"],
            sunday=row["sunday"],
            preferred_times=row["preferred_times"],
            notes=row["notes"],
        ).normalized()

    def set_availability(self, value: MemberAvailability) -> None:
        item = value.normalized()
        payload = validate_roster_availability({
            "roster_member_id": item.roster_member_id,
            "monday": item.monday, "tuesday": item.tuesday, "wednesday": item.wednesday,
            "thursday": item.thursday, "friday": item.friday, "saturday": item.saturday,
            "sunday": item.sunday, "preferred_times": item.preferred_times, "notes": item.notes,
        })
        db = self.db.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                """INSERT INTO roster_member_availability (
                    roster_member_id, monday, tuesday, wednesday, thursday, friday,
                    saturday, sunday, preferred_times, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(roster_member_id) DO UPDATE SET
                    monday=excluded.monday, tuesday=excluded.tuesday,
                    wednesday=excluded.wednesday, thursday=excluded.thursday,
                    friday=excluded.friday, saturday=excluded.saturday,
                    sunday=excluded.sunday, preferred_times=excluded.preferred_times,
                    notes=excluded.notes, updated_at=excluded.updated_at""",
                (payload["roster_member_id"], payload["monday"], payload["tuesday"],
                 payload["wednesday"], payload["thursday"], payload["friday"],
                 payload["saturday"], payload["sunday"], payload["preferred_times"],
                 payload["notes"], _now()),
            )
            row = db.execute(
                """SELECT roster_member_id, monday, tuesday, wednesday, thursday,
                          friday, saturday, sunday, preferred_times, notes
                   FROM roster_member_availability WHERE roster_member_id = ?""",
                (payload["roster_member_id"],),
            ).fetchone()
            read_back = validate_roster_availability(dict(row)) if row is not None else None
            if read_back != payload:
                raise RuntimeError("Roster availability did not round-trip exactly")
            db.commit()
        except Exception:
            db.rollback()
            raise

    def list_recruits(self, *, include_archived: bool = False) -> tuple[RecruitmentCandidate, ...]:
        where = "" if include_archived else "WHERE status <> 'archived'"
        rows = self.db.execute(
            f"""
            SELECT id, player_name, character_name, desired_role, eso_class,
                   target_team, availability, status, notes, created_at, updated_at
            FROM roster_recruitment_candidate
            {where}
            ORDER BY CASE status
                WHEN 'trial' THEN 0
                WHEN 'interview' THEN 1
                WHEN 'review' THEN 2
                WHEN 'new' THEN 3
                WHEN 'accepted' THEN 4
                WHEN 'declined' THEN 5
                ELSE 6 END,
                player_name COLLATE NOCASE,
                id
            """
        ).fetchall()
        return tuple(
            RecruitmentCandidate(
                id=int(row["id"]),
                player_name=row["player_name"],
                character_name=row["character_name"],
                desired_role=row["desired_role"],
                eso_class=row["eso_class"],
                target_team=row["target_team"],
                availability=row["availability"],
                status=row["status"],
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            ).normalized()
            for row in rows
        )

    def save_recruit(self, candidate: RecruitmentCandidate) -> int:
        item = candidate.normalized()
        payload = validate_recruitment_candidate({
            "id": item.id, "player_name": item.player_name,
            "character_name": item.character_name, "desired_role": item.desired_role,
            "eso_class": item.eso_class, "target_team": item.target_team,
            "availability": item.availability, "status": item.status, "notes": item.notes,
        })
        now = _now()
        db = self.db.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            if payload["id"] is None:
                cursor = db.execute(
                    """INSERT INTO roster_recruitment_candidate (
                        player_name, character_name, desired_role, eso_class,
                        target_team, availability, status, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (payload["player_name"], payload["character_name"], payload["desired_role"],
                     payload["eso_class"], payload["target_team"], payload["availability"],
                     payload["status"], payload["notes"], now, now),
                )
                candidate_id = int(cursor.lastrowid)
            else:
                candidate_id = int(payload["id"])
                cursor = db.execute(
                    """UPDATE roster_recruitment_candidate
                       SET player_name=?, character_name=?, desired_role=?, eso_class=?,
                           target_team=?, availability=?, status=?, notes=?, updated_at=?
                       WHERE id=?""",
                    (payload["player_name"], payload["character_name"], payload["desired_role"],
                     payload["eso_class"], payload["target_team"], payload["availability"],
                     payload["status"], payload["notes"], now, candidate_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError(f"recruitment candidate {candidate_id} does not exist")
            row = db.execute(
                """SELECT id, player_name, character_name, desired_role, eso_class,
                          target_team, availability, status, notes
                   FROM roster_recruitment_candidate WHERE id=?""",
                (candidate_id,),
            ).fetchone()
            expected = dict(payload)
            expected["id"] = candidate_id
            read_back = validate_recruitment_candidate(dict(row)) if row is not None else None
            if read_back != expected:
                raise RuntimeError("Recruitment candidate did not round-trip exactly")
            db.commit()
            return candidate_id
        except Exception:
            db.rollback()
            raise

    def set_recruit_status(self, candidate_id: int, status: str) -> None:
        key = _clean(status).casefold()
        if key not in _RECRUITMENT_STATES:
            raise ValueError(f"Unsupported recruitment status: {status}")
        self.db.execute(
            "UPDATE roster_recruitment_candidate SET status=?, updated_at=? WHERE id=?",
            (key, _now(), int(candidate_id)),
        )
        self.db.commit()

    def archive(
        self,
        *,
        entity_type: str,
        entity_key: str = "",
        display_name: str,
        reason: str = "",
        related_team: str = "",
        payload: dict | None = None,
    ) -> int:
        cursor = self.db.execute(
            """
            INSERT INTO roster_archive_record (
                entity_type, entity_key, display_name, reason,
                related_team, archived_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _clean(entity_type),
                _clean(entity_key),
                _clean(display_name),
                _clean(reason),
                _clean(related_team),
                _now(),
                json.dumps(payload or {}, sort_keys=True),
            ),
        )
        self.db.commit()
        return int(cursor.lastrowid)

    def list_archive(self) -> tuple[ArchiveRecord, ...]:
        rows = self.db.execute(
            """
            SELECT id, entity_type, entity_key, display_name, reason,
                   related_team, archived_at, payload_json
            FROM roster_archive_record
            ORDER BY archived_at DESC, id DESC
            """
        ).fetchall()
        result: list[ArchiveRecord] = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except json.JSONDecodeError:
                payload = {}
            result.append(
                ArchiveRecord(
                    id=int(row["id"]),
                    entity_type=row["entity_type"],
                    entity_key=row["entity_key"],
                    display_name=row["display_name"],
                    reason=row["reason"],
                    related_team=row["related_team"],
                    archived_at=row["archived_at"],
                    payload=payload if isinstance(payload, dict) else {},
                )
            )
        return tuple(result)


__all__ = [
    "ArchiveRecord",
    "MemberAvailability",
    "RecruitmentCandidate",
    "RosterWorkspaceStateService",
]
