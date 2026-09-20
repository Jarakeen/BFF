from __future__ import annotations

"""Merge duplicate Personnel rows that represent the same player/gamertag.

Roster identity is player-level. Characters and builds live in the canonical
Player -> Character -> Build catalog, so importing another toon must not create a
second Personnel row for the same gamertag.

This service repairs older duplicates conservatively:
- choose one durable Personnel survivor;
- union team memberships;
- preserve legacy and team/boss assignment data field-by-field;
- preserve the survivor's visible character/class/primary-role identity unless blank;
- retain a distinct donor role as SecondaryRole when that slot is blank;
- leave canonical characters/builds untouched;
- delete only the redundant roster_member rows after their roster state is moved.
"""

from dataclasses import dataclass
from pathlib import Path
import shutil

from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.roster_assignment_context_service import RosterAssignmentContextService
from services.roster_service import RosterService


_ASSIGNMENT_FIELDS = (
    "primary_assignment",
    "secondary_assignment",
    "gear_needed",
    "notes",
)


@dataclass(frozen=True)
class RosterDuplicateMergeResult:
    groups_merged: int = 0
    rows_removed: int = 0
    survivor_ids: tuple[int, ...] = ()
    backup_path: str = ""


def _identity_key(value: object) -> str:
    return " ".join(str(value or "").strip().split()).lstrip("@").casefold()


def _team_count(member: RosterMember) -> int:
    return len({piece.strip().casefold() for piece in str(member.Team or "").split(",") if piece.strip()})


def _survivor_sort_key(member: RosterMember) -> tuple[int, int, int, int]:
    # Prefer the row already carrying the broadest roster history. For ties,
    # prefer a real visible character label, then the shorter label (older human
    # names such as "Magrat" beat generated/import labels such as "Magrat SW Hlz"),
    # then the oldest row for deterministic stability.
    character = str(member.CharacterName or "").strip()
    return (
        -_team_count(member),
        0 if character else 1,
        len(character) if character else 10_000,
        int(member.Id or 10_000_000),
    )


def _merge_text(existing: object, incoming: object) -> str:
    current = str(existing or "").strip()
    return current or str(incoming or "").strip()


def _merge_personnel_identity(survivor: RosterMember, donors: list[RosterMember]) -> None:
    for donor in donors:
        survivor.CharacterName = _merge_text(survivor.CharacterName, donor.CharacterName)
        survivor.EsoClass = _merge_text(survivor.EsoClass, donor.EsoClass)
        survivor.PrimaryRole = _merge_text(survivor.PrimaryRole, donor.PrimaryRole)
        survivor.SecondaryRole = _merge_text(survivor.SecondaryRole, donor.SecondaryRole)
        survivor.DiscordName = _merge_text(survivor.DiscordName, donor.DiscordName)
        survivor.YouTube = _merge_text(survivor.YouTube, donor.YouTube)
        survivor.Twitch = _merge_text(survivor.Twitch, donor.Twitch)

        if not str(survivor.SecondaryRole or "").strip():
            donor_primary = str(donor.PrimaryRole or "").strip()
            if donor_primary and donor_primary.casefold() != str(survivor.PrimaryRole or "").strip().casefold():
                survivor.SecondaryRole = donor_primary

        if str(donor.Status or "").strip().casefold() == "active":
            survivor.Status = "Active"


def _merge_legacy_assignment(db: EsoDatabase, survivor_id: int, donor_id: int) -> None:
    donor = db.execute(
        """
        SELECT primary_assignment, secondary_assignment, gear_needed, notes
        FROM roster_member_assignment WHERE roster_member_id = ?
        """,
        (donor_id,),
    ).fetchone()
    if donor is None:
        return

    db.execute(
        "INSERT OR IGNORE INTO roster_member_assignment (roster_member_id) VALUES (?)",
        (survivor_id,),
    )
    current = db.execute(
        """
        SELECT primary_assignment, secondary_assignment, gear_needed, notes
        FROM roster_member_assignment WHERE roster_member_id = ?
        """,
        (survivor_id,),
    ).fetchone()
    for field in _ASSIGNMENT_FIELDS:
        existing = str(current[field] or "").strip() if current is not None else ""
        incoming = str(donor[field] or "").strip()
        if not existing and incoming:
            db.execute(
                f"UPDATE roster_member_assignment SET {field} = ? WHERE roster_member_id = ?",
                (incoming, survivor_id),
            )


def _merge_context_assignments(db: EsoDatabase, survivor_id: int, donor_id: int) -> None:
    rows = db.execute(
        """
        SELECT team_id, encounter_id, primary_assignment, secondary_assignment, gear_needed, notes
        FROM roster_assignment_context
        WHERE roster_member_id = ?
        ORDER BY team_id, encounter_id
        """,
        (donor_id,),
    ).fetchall()

    for donor in rows:
        team_id = int(donor["team_id"])
        encounter_id = str(donor["encounter_id"] or "")
        current = db.execute(
            """
            SELECT primary_assignment, secondary_assignment, gear_needed, notes
            FROM roster_assignment_context
            WHERE roster_member_id = ? AND team_id = ? AND encounter_id = ?
            """,
            (survivor_id, team_id, encounter_id),
        ).fetchone()
        if current is None:
            db.execute(
                """
                INSERT INTO roster_assignment_context (
                    roster_member_id, team_id, encounter_id,
                    primary_assignment, secondary_assignment, gear_needed, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    survivor_id,
                    team_id,
                    encounter_id,
                    donor["primary_assignment"] or "",
                    donor["secondary_assignment"] or "",
                    donor["gear_needed"] or "",
                    donor["notes"] or "",
                ),
            )
            continue

        for field in _ASSIGNMENT_FIELDS:
            existing = str(current[field] or "").strip()
            incoming = str(donor[field] or "").strip()
            if not existing and incoming:
                db.execute(
                    f"""
                    UPDATE roster_assignment_context SET {field} = ?
                    WHERE roster_member_id = ? AND team_id = ? AND encounter_id = ?
                    """,
                    (incoming, survivor_id, team_id, encounter_id),
                )


def _backup_database(database_path: Path) -> str:
    backup = database_path.with_name(f"{database_path.stem}.before-roster-duplicate-merge{database_path.suffix}")
    if database_path.is_file() and not backup.exists():
        shutil.copy2(database_path, backup)
    return str(backup) if backup.exists() else ""


def merge_duplicate_roster_players(database: EsoDatabase, *, create_backup: bool = True) -> RosterDuplicateMergeResult:
    """Merge all duplicate Personnel rows sharing a normalized gamertag.

    The operation is idempotent. If no duplicate gamertags exist, nothing is
    written and no backup is created.
    """
    roster = RosterService(database)
    RosterAssignmentContextService(database)  # ensure context table/triggers exist
    members = roster.list_members()

    groups: dict[str, list[RosterMember]] = {}
    for member in members:
        key = _identity_key(member.PlayerName)
        if key:
            groups.setdefault(key, []).append(member)

    duplicates = [rows for rows in groups.values() if len(rows) > 1]
    if not duplicates:
        return RosterDuplicateMergeResult()

    backup_path = _backup_database(Path(database.database)) if create_backup else ""
    survivor_ids: list[int] = []
    rows_removed = 0

    try:
        for rows in duplicates:
            ordered = sorted(rows, key=_survivor_sort_key)
            survivor = ordered[0]
            donors = ordered[1:]
            if survivor.Id is None:
                continue
            survivor_id = int(survivor.Id)
            _merge_personnel_identity(survivor, donors)

            # Preserve the survivor's existing team memberships and union donor teams.
            for donor in donors:
                if donor.Id is None:
                    continue
                donor_id = int(donor.Id)
                database.execute(
                    """
                    INSERT OR IGNORE INTO team_member (roster_member_id, team_id)
                    SELECT ?, team_id FROM team_member WHERE roster_member_id = ?
                    """,
                    (survivor_id, donor_id),
                )
                _merge_legacy_assignment(database, survivor_id, donor_id)
                _merge_context_assignments(database, survivor_id, donor_id)

            database.execute(
                """
                UPDATE roster_member SET
                    player_name = ?, character_name = ?, eso_class = ?,
                    primary_role = ?, secondary_role = ?, status = ?,
                    discord_name = ?, youtube = ?, twitch = ?
                WHERE id = ?
                """,
                (
                    str(survivor.PlayerName or "").strip(),
                    str(survivor.CharacterName or "").strip(),
                    str(survivor.EsoClass or "").strip(),
                    str(survivor.PrimaryRole or "").strip(),
                    str(survivor.SecondaryRole or "").strip(),
                    str(survivor.Status or "Active").strip() or "Active",
                    str(survivor.DiscordName or "").strip(),
                    str(survivor.YouTube or "").strip(),
                    str(survivor.Twitch or "").strip(),
                    survivor_id,
                ),
            )

            for donor in donors:
                if donor.Id is None:
                    continue
                donor_id = int(donor.Id)
                database.execute("DELETE FROM roster_assignment_context WHERE roster_member_id = ?", (donor_id,))
                database.execute("DELETE FROM roster_member_assignment WHERE roster_member_id = ?", (donor_id,))
                database.execute("DELETE FROM team_member WHERE roster_member_id = ?", (donor_id,))
                database.execute("DELETE FROM roster_member WHERE id = ?", (donor_id,))
                rows_removed += 1

            survivor_ids.append(survivor_id)

        database.commit()
    except Exception:
        database.rollback()
        raise

    return RosterDuplicateMergeResult(
        groups_merged=len(survivor_ids),
        rows_removed=rows_removed,
        survivor_ids=tuple(survivor_ids),
        backup_path=backup_path,
    )


__all__ = ["RosterDuplicateMergeResult", "merge_duplicate_roster_players"]
