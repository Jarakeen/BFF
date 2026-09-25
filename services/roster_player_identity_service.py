from __future__ import annotations

"""Durable roster player aliases and explicit cross-name identity merging.

Raid leads often know the same human by several unrelated names over time: old
Xbox gamertags, Discord names, character names, and long-lived raid-sheet labels.
Those names are useful history, but they are not safe to guess as equivalent.
This service records aliases only from explicit user action or an explicit player
merge, then reuses that evidence for future exact identity matching.
"""

from dataclasses import dataclass, replace
from pathlib import Path
import shutil

from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_assignment_context_service import RosterAssignmentContextService
from services.roster_duplicate_player_merge_service import (
    _merge_context_assignments,
    _merge_legacy_assignment,
    _merge_personnel_identity,
)
from services.raid_plan_repository import RaidPlanRepository
from services.roster_service import RosterService


def _text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _identity_key(value: object) -> str:
    return _text(value).lstrip("@").casefold()


@dataclass(frozen=True)
class PlayerAlias:
    roster_member_id: int
    alias: str
    source: str = "manual"
    notes: str = ""
    first_seen: str = ""
    last_seen: str = ""


@dataclass(frozen=True)
class PlayerIdentityMergeResult:
    survivor_id: int
    donor_id: int
    canonical_name: str
    learned_aliases: tuple[str, ...]
    database_backup: str = ""
    build_backup: str = ""
    catalog_backup: str = ""


class RosterPlayerIdentityService:
    """Own exact aliases and explicit Personnel/player identity merges."""

    def __init__(self, database: EsoDatabase, build_service: BuildService | None = None):
        self.roster = RosterService(database)
        self.database = self.roster.db
        self.build_service = build_service
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS roster_player_alias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roster_member_id INTEGER NOT NULL,
                alias TEXT NOT NULL,
                alias_key TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                notes TEXT NOT NULL DEFAULT '',
                first_seen TEXT NOT NULL DEFAULT (datetime('now')),
                last_seen TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(roster_member_id, alias_key)
            )
            """
        )
        # EsoDatabase intentionally does not globally force SQLite FK behavior.
        # Keep aliases clean even when another roster path deletes Personnel rows.
        self.database.execute(
            """
            CREATE TRIGGER IF NOT EXISTS roster_player_alias_cleanup
            AFTER DELETE ON roster_member
            BEGIN
                DELETE FROM roster_player_alias WHERE roster_member_id = OLD.id;
            END
            """
        )
        self.database.commit()


    def canonical_player_label(self, member_or_player_id, *, fallback: object = "") -> str:
        """Return the current human-facing player name for one canonical identity.

        Stable ids own identity. Stored roster/build text is only a display fallback.
        Raw ids are never returned as a user-facing label.
        """
        player_id = ""
        fallback_text = _text(fallback)
        if hasattr(member_or_player_id, "CanonicalPlayerId"):
            player_id = _text(getattr(member_or_player_id, "CanonicalPlayerId", ""))
            fallback_text = _text(getattr(member_or_player_id, "PlayerName", "")) or fallback_text
        else:
            player_id = _text(member_or_player_id)

        if player_id and self.build_service is not None:
            try:
                player = self.build_service.canonical.catalog_service.get_player(player_id)
            except Exception:
                player = None
            if isinstance(player, dict):
                label = _text(player.get("gamertag") or player.get("display_name"))
                if label:
                    return label
        return fallback_text or "Unnamed Player"

    def canonical_character_label(self, member_or_character_id, *, fallback: object = "") -> str:
        """Return the current human-facing character name for one canonical identity."""
        character_id = ""
        fallback_text = _text(fallback)
        if hasattr(member_or_character_id, "CanonicalCharacterId"):
            character_id = _text(getattr(member_or_character_id, "CanonicalCharacterId", ""))
            fallback_text = _text(getattr(member_or_character_id, "CharacterName", "")) or fallback_text
        else:
            character_id = _text(member_or_character_id)

        if character_id and self.build_service is not None:
            try:
                character = self.build_service.canonical.catalog_service.get_character(character_id)
            except Exception:
                character = None
            if isinstance(character, dict):
                label = _text(character.get("name"))
                if label:
                    return label
        return fallback_text

    def deduplicated_members_for_pickers(self, *, include_archived: bool = False):
        """Collapse Personnel presentation rows by canonical player id.

        This is presentation-only. Rows lacking stable ids remain distinct so the UI
        never guesses that unrelated people are duplicates from name similarity.
        """
        members = list(self.roster.list_members(include_archived=include_archived))
        result = []
        seen_player_ids: set[str] = set()
        for member in members:
            player_id = _text(getattr(member, "CanonicalPlayerId", ""))
            if player_id:
                key = player_id.casefold()
                if key in seen_player_ids:
                    continue
                seen_player_ids.add(key)
            result.append(member)
        return result

    def aliases_for_member(self, roster_member_id: int) -> tuple[PlayerAlias, ...]:
        rows = self.database.execute(
            """
            SELECT roster_member_id, alias, source, notes, first_seen, last_seen
            FROM roster_player_alias
            WHERE roster_member_id = ?
            ORDER BY first_seen, id
            """,
            (int(roster_member_id),),
        ).fetchall()
        return tuple(
            PlayerAlias(
                roster_member_id=int(row["roster_member_id"]),
                alias=str(row["alias"] or ""),
                source=str(row["source"] or "manual"),
                notes=str(row["notes"] or ""),
                first_seen=str(row["first_seen"] or ""),
                last_seen=str(row["last_seen"] or ""),
            )
            for row in rows
        )

    def add_alias(
        self,
        roster_member_id: int,
        alias: object,
        *,
        source: str = "manual",
        notes: str = "",
    ) -> bool:
        member = self.roster.get_member(int(roster_member_id))
        if member is None:
            raise ValueError(f"roster member {roster_member_id} does not exist")
        value = _text(alias)
        key = _identity_key(value)
        if not key:
            raise ValueError("alias is required")
        if key == _identity_key(member.PlayerName):
            return False
        existing = self.database.execute(
            """
            SELECT id FROM roster_player_alias
            WHERE roster_member_id = ? AND alias_key = ?
            """,
            (int(roster_member_id), key),
        ).fetchone()
        if existing is not None:
            self.database.execute(
                """
                UPDATE roster_player_alias
                SET alias = ?, source = ?, notes = ?, last_seen = datetime('now')
                WHERE id = ?
                """,
                (value, _text(source) or "manual", _text(notes), int(existing["id"])),
            )
            self.database.commit()
            return False
        self.database.execute(
            """
            INSERT INTO roster_player_alias (
                roster_member_id, alias, alias_key, source, notes
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (int(roster_member_id), value, key, _text(source) or "manual", _text(notes)),
        )
        self.database.commit()
        return True

    def matching_members(
        self,
        identity: object,
        *,
        exclude_id: int | None = None,
        include_archived: bool = False,
    ):
        """Return exact current-name or explicitly learned-alias matches.

        Archived Personnel remain excluded by default. Callers that need to
        distinguish an archived identity from a genuinely unknown one may opt
        in explicitly; no fuzzy or similarity matching is ever performed.
        """
        key = _identity_key(identity)
        if not key:
            return []
        matched_ids: set[int] = set()
        members = self.roster.list_members(include_archived=include_archived)
        by_id = {int(member.Id): member for member in members if member.Id is not None}
        for member_id, member in by_id.items():
            if exclude_id is not None and member_id == int(exclude_id):
                continue
            if _identity_key(member.PlayerName) == key:
                matched_ids.add(member_id)
        rows = self.database.execute(
            "SELECT roster_member_id FROM roster_player_alias WHERE alias_key = ?",
            (key,),
        ).fetchall()
        for row in rows:
            member_id = int(row["roster_member_id"])
            if exclude_id is None or member_id != int(exclude_id):
                matched_ids.add(member_id)
        return [by_id[member_id] for member_id in sorted(matched_ids) if member_id in by_id]

    def _backup_file(self, path: Path, suffix: str) -> str:
        if not path.is_file():
            return ""
        backup = path.with_name(f"{path.stem}.{suffix}{path.suffix}")
        if not backup.exists():
            shutil.copy2(path, backup)
        return str(backup)

    def _merge_canonical_players(self, survivor_name: str, donor_name: str) -> None:
        if self.build_service is None:
            return
        catalog_service = self.build_service.canonical.catalog_service
        catalog = catalog_service.load_strict()
        survivor_key = _identity_key(survivor_name)
        donor_key = _identity_key(donor_name)
        players = [row for row in catalog.get("players", []) if isinstance(row, dict)]
        survivor = next(
            (row for row in players if _identity_key(row.get("gamertag")) == survivor_key),
            None,
        )
        donor = next(
            (row for row in players if _identity_key(row.get("gamertag")) == donor_key),
            None,
        )
        if survivor is None and donor is None:
            return
        if survivor is None:
            survivor = donor
            survivor["gamertag"] = survivor_name
        survivor_id = _text(survivor.get("player_id"))
        donor_id = _text(donor.get("player_id")) if donor is not None else ""
        affected_character_ids: set[str] = set()
        for character in catalog.get("characters", []):
            if not isinstance(character, dict):
                continue
            character_player_id = _text(character.get("player_id"))
            if character_player_id in {survivor_id, donor_id}:
                character["player_id"] = survivor_id
                character["gamertag"] = survivor_name
                character_id = _text(character.get("character_id"))
                if character_id:
                    affected_character_ids.add(character_id)
        for build in catalog.get("builds", []):
            if not isinstance(build, dict):
                continue
            if _text(build.get("character_id")) not in affected_character_ids:
                continue
            for field in ("legacy", "payload"):
                payload = build.get(field)
                if isinstance(payload, dict):
                    payload["Gamertag"] = survivor_name
        survivor["gamertag"] = survivor_name
        if donor is not None and donor is not survivor:
            catalog["players"] = [
                row
                for row in catalog.get("players", [])
                if not (isinstance(row, dict) and _text(row.get("player_id")) == donor_id)
            ]
        catalog_service.save(catalog)
        # Rebuild the compatibility mirror from canonical state so older pages do
        # not resurrect the discarded player name on their next save.
        roster = self.build_service.load()
        self.build_service.save(roster)

    def _rewrite_raid_plan_player_identity(
        self,
        *,
        survivor_id: int,
        donor_id: int,
        survivor_name: str,
        donor_name: str,
        survivor_player_id: str,
        donor_player_id: str,
    ) -> None:
        """Move persisted Raid Plan chairs from a merged donor to the survivor.

        Personnel merges are identity changes, not roster deletions. Any saved Raid
        Plan that still points at the donor roster/player id must therefore follow
        the survivor while preserving the chair's character/build/assignment state.
        """
        repository = RaidPlanRepository(Path(self.database.database))
        donor_key = _identity_key(donor_name)
        for plan in repository.list_plans():
            changed = False
            members = []
            for member in plan.members:
                donor_roster = member.roster_member_id == donor_id
                donor_player = bool(
                    donor_player_id
                    and _text(member.player_id) == donor_player_id
                )
                donor_label = _identity_key(member.gamertag) == donor_key
                if donor_roster or donor_player or donor_label:
                    member = member.with_selection(
                        gamertag=survivor_name,
                        roster_member_id=survivor_id,
                        player_id=survivor_player_id or None,
                    )
                    changed = True
                members.append(member)
            if changed:
                repository.save(replace(plan, members=tuple(members)))

    def merge_players(
        self,
        *,
        survivor_id: int,
        donor_id: int,
        source: str = "manual_merge",
        notes: str = "",
        create_backups: bool = True,
    ) -> PlayerIdentityMergeResult:
        survivor_id = int(survivor_id)
        donor_id = int(donor_id)
        if survivor_id == donor_id:
            raise ValueError("survivor and donor must be different Personnel records")
        survivor = self.roster.get_member(survivor_id)
        donor = self.roster.get_member(donor_id)
        if survivor is None or donor is None:
            raise ValueError("both Personnel records must exist before they can be merged")

        database_backup = ""
        build_backup = ""
        catalog_backup = ""
        if create_backups:
            database_backup = self._backup_file(
                Path(self.database.database), "before-player-identity-merge"
            )
            if self.build_service is not None:
                build_backup = self._backup_file(
                    Path(self.build_service.builds_path), "before-player-identity-merge"
                )
                catalog_backup = self._backup_file(
                    Path(self.build_service.canonical.catalog_path),
                    "before-player-identity-merge",
                )

        RosterAssignmentContextService(self.database)
        donor_aliases = self.aliases_for_member(donor_id)
        learned: list[str] = []
        donor_name = _text(donor.PlayerName)
        survivor_name = _text(survivor.PlayerName)
        survivor_player_id = _text(getattr(survivor, "CanonicalPlayerId", ""))
        donor_player_id = _text(getattr(donor, "CanonicalPlayerId", ""))

        try:
            # Alias writes are staged directly here so the entire Personnel merge
            # can remain one SQLite transaction.
            alias_candidates = [(donor_name, source, notes)] + [
                (alias.alias, alias.source or source, alias.notes)
                for alias in donor_aliases
            ]
            for alias_name, alias_source, alias_notes in alias_candidates:
                alias_key = _identity_key(alias_name)
                if not alias_key or alias_key == _identity_key(survivor_name):
                    continue
                existing = self.database.execute(
                    """
                    SELECT id FROM roster_player_alias
                    WHERE roster_member_id = ? AND alias_key = ?
                    """,
                    (survivor_id, alias_key),
                ).fetchone()
                if existing is None:
                    self.database.execute(
                        """
                        INSERT INTO roster_player_alias (
                            roster_member_id, alias, alias_key, source, notes
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            survivor_id,
                            _text(alias_name),
                            alias_key,
                            _text(alias_source) or source,
                            _text(alias_notes),
                        ),
                    )
                    learned.append(_text(alias_name))

            self.database.execute(
                """
                INSERT OR IGNORE INTO team_member (roster_member_id, team_id)
                SELECT ?, team_id FROM team_member WHERE roster_member_id = ?
                """,
                (survivor_id, donor_id),
            )
            _merge_legacy_assignment(self.database, survivor_id, donor_id)
            _merge_context_assignments(self.database, survivor_id, donor_id)
            _merge_personnel_identity(survivor, [donor])
            self.database.execute(
                """
                UPDATE roster_member SET
                    player_name = ?, character_name = ?, eso_class = ?,
                    primary_role = ?, secondary_role = ?, status = ?
                WHERE id = ?
                """,
                (
                    survivor_name,
                    _text(survivor.CharacterName),
                    _text(survivor.EsoClass),
                    _text(survivor.PrimaryRole),
                    _text(survivor.SecondaryRole),
                    _text(survivor.Status) or "Active",
                    survivor_id,
                ),
            )
            self.database.execute(
                "DELETE FROM roster_assignment_context WHERE roster_member_id = ?",
                (donor_id,),
            )
            self.database.execute(
                "DELETE FROM roster_member_assignment WHERE roster_member_id = ?",
                (donor_id,),
            )
            self.database.execute(
                "DELETE FROM team_member WHERE roster_member_id = ?",
                (donor_id,),
            )
            self.database.execute(
                "DELETE FROM roster_player_alias WHERE roster_member_id = ?",
                (donor_id,),
            )
            self.database.execute("DELETE FROM roster_member WHERE id = ?", (donor_id,))
            self.database.commit()
        except Exception:
            self.database.rollback()
            raise

        # Canonical user-build identity is stored outside SQLite. Do this only
        # after the roster transaction commits; backups above make the operation
        # reversible if a later filesystem write fails.
        self._merge_canonical_players(survivor_name, donor_name)
        self._rewrite_raid_plan_player_identity(
            survivor_id=survivor_id,
            donor_id=donor_id,
            survivor_name=survivor_name,
            donor_name=donor_name,
            survivor_player_id=survivor_player_id,
            donor_player_id=donor_player_id,
        )

        return PlayerIdentityMergeResult(
            survivor_id=survivor_id,
            donor_id=donor_id,
            canonical_name=survivor_name,
            learned_aliases=tuple(learned),
            database_backup=database_backup,
            build_backup=build_backup,
            catalog_backup=catalog_backup,
        )


__all__ = [
    "PlayerAlias",
    "PlayerIdentityMergeResult",
    "RosterPlayerIdentityService",
]
