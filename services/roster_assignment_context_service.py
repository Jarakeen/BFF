from __future__ import annotations

"""Durable team- and encounter-scoped raid-lead assignment planning.

This state is deliberately separate from canonical player/character/build identity and
from rotation/provider assignments. A roster member can have one team default and
optional per-encounter overrides without duplicating the member or build.
"""

from services.eso_database import EsoDatabase
from services.roster_service import RosterService


_ASSIGNMENT_FIELDS = {
    "primary_assignment",
    "secondary_assignment",
    "gear_needed",
    "notes",
}

_EMPTY = {
    "primary_assignment": "",
    "secondary_assignment": "",
    "gear_needed": "",
    "notes": "",
}


class RosterAssignmentContextService:
    def __init__(self, database: EsoDatabase):
        self.db = database
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS roster_assignment_context (
                roster_member_id INTEGER NOT NULL
                    REFERENCES roster_member(id)
                    ON DELETE CASCADE,
                team_id INTEGER NOT NULL
                    REFERENCES team(id)
                    ON DELETE CASCADE,
                encounter_id TEXT NOT NULL DEFAULT '',
                primary_assignment TEXT NOT NULL DEFAULT '',
                secondary_assignment TEXT NOT NULL DEFAULT '',
                gear_needed TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (roster_member_id, team_id, encounter_id)
            )
            """
        )
        # EsoDatabase does not globally enable SQLite foreign_keys, so keep the
        # context table tidy even in older/local databases where cascades are inert.
        self.db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS roster_assignment_context_member_cleanup
            AFTER DELETE ON roster_member
            BEGIN
                DELETE FROM roster_assignment_context
                WHERE roster_member_id = OLD.id;
            END
            """
        )
        self.db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS roster_assignment_context_team_cleanup
            AFTER DELETE ON team
            BEGIN
                DELETE FROM roster_assignment_context
                WHERE team_id = OLD.id;
            END
            """
        )
        self.db.commit()

    @staticmethod
    def _clean(value: object) -> str:
        return str(value or "").strip()

    def _team_id(self, team_name: str, *, create: bool = False) -> int | None:
        name = self._clean(team_name)
        if not name:
            return None
        if create:
            self.db.execute("INSERT OR IGNORE INTO team (name) VALUES (?)", (name,))
        row = self.db.execute(
            "SELECT id FROM team WHERE name = ? COLLATE NOCASE",
            (name,),
        ).fetchone()
        return int(row["id"]) if row is not None else None

    def _row(self, member_id: int, team_id: int, encounter_id: str):
        return self.db.execute(
            """
            SELECT primary_assignment, secondary_assignment, gear_needed, notes
            FROM roster_assignment_context
            WHERE roster_member_id = ? AND team_id = ? AND encounter_id = ?
            """,
            (int(member_id), int(team_id), self._clean(encounter_id)),
        ).fetchone()

    @staticmethod
    def _payload(row) -> dict[str, str]:
        if row is None:
            return dict(_EMPTY)
        return {
            "primary_assignment": row["primary_assignment"] or "",
            "secondary_assignment": row["secondary_assignment"] or "",
            "gear_needed": row["gear_needed"] or "",
            "notes": row["notes"] or "",
        }

    @staticmethod
    def _overlay_nonempty(base: dict[str, str], overlay: dict[str, str]) -> tuple[dict[str, str], tuple[str, ...]]:
        result = dict(base)
        changed: list[str] = []
        for field in _ASSIGNMENT_FIELDS:
            value = str(overlay.get(field, "") or "").strip()
            if value:
                result[field] = value
                changed.append(field)
        return result, tuple(sorted(changed))

    def get_effective_assignment(
        self,
        member_id: int,
        *,
        team_name: str,
        encounter_id: str = "",
        legacy_service: RosterService | None = None,
    ) -> dict[str, object]:
        """Resolve each field as boss override -> team default -> legacy value.

        Blank override fields mean inherit. Metadata keys beginning with ``_`` are
        presentation hints only and are never assignment authority.
        """
        effective = dict(_EMPTY)
        if legacy_service is not None:
            legacy = legacy_service.get_member_assignment(int(member_id))
            effective, _ = self._overlay_nonempty(effective, legacy)

        team_id = self._team_id(team_name)
        team_fields: tuple[str, ...] = ()
        encounter_fields: tuple[str, ...] = ()
        if team_id is not None:
            team_payload = self._payload(self._row(member_id, team_id, ""))
            effective, team_fields = self._overlay_nonempty(effective, team_payload)

            encounter = self._clean(encounter_id)
            if encounter:
                encounter_payload = self._payload(self._row(member_id, team_id, encounter))
                effective, encounter_fields = self._overlay_nonempty(effective, encounter_payload)

        encounter = self._clean(encounter_id)
        if encounter_fields:
            source = "encounter"
        elif team_fields:
            source = "team"
        elif any(effective.values()):
            source = "legacy"
        else:
            source = "none"

        result: dict[str, object] = dict(effective)
        result.update(
            {
                "_source": source,
                "_inherited": bool(encounter) and not bool(encounter_fields),
                "_team_fields": team_fields,
                "_encounter_fields": encounter_fields,
            }
        )
        return result

    def set_field(
        self,
        member_id: int,
        *,
        team_name: str,
        encounter_id: str = "",
        field: str,
        value: str,
    ) -> None:
        if field not in _ASSIGNMENT_FIELDS:
            raise ValueError(f"unsupported roster assignment field: {field}")
        member_id = int(member_id)
        roster = RosterService(self.db)
        if roster.get_member(member_id) is None:
            raise ValueError(f"roster member {member_id} does not exist")
        team_id = self._team_id(team_name, create=True)
        if team_id is None:
            raise ValueError("choose a team before editing assignments")
        encounter = self._clean(encounter_id)
        self.db.execute(
            """
            INSERT OR IGNORE INTO roster_assignment_context
                (roster_member_id, team_id, encounter_id)
            VALUES (?, ?, ?)
            """,
            (member_id, team_id, encounter),
        )
        self.db.execute(
            f"""
            UPDATE roster_assignment_context
            SET {field} = ?
            WHERE roster_member_id = ? AND team_id = ? AND encounter_id = ?
            """,
            (self._clean(value), member_id, team_id, encounter),
        )
        self.db.commit()

    def clear_encounter_override(
        self,
        member_id: int,
        *,
        team_name: str,
        encounter_id: str,
    ) -> None:
        team_id = self._team_id(team_name)
        encounter = self._clean(encounter_id)
        if team_id is None or not encounter:
            return
        self.db.execute(
            """
            DELETE FROM roster_assignment_context
            WHERE roster_member_id = ? AND team_id = ? AND encounter_id = ?
            """,
            (int(member_id), team_id, encounter),
        )
        self.db.commit()


__all__ = ["RosterAssignmentContextService"]
