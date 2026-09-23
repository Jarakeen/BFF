from __future__ import annotations

"""Explicitly bind Personnel rows to canonical Build Catalog character identities.

Character binding is the one-to-one identity bridge for the current player+character
Personnel model. The caller supplies a real ``character_id``; no name matching is used.
The character's canonical player owner is derived from Build Catalog and kept consistent
with the Personnel row's canonical player binding.
"""

from dataclasses import dataclass

from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_service import RosterService


@dataclass(frozen=True)
class CanonicalCharacterBinding:
    roster_member_id: int
    canonical_character_id: str
    canonical_player_id: str
    character_name: str


class RosterCanonicalCharacterBindingService:
    def __init__(self, database: EsoDatabase, build_service: BuildService):
        self.roster = RosterService(database)
        self.database = self.roster.db
        self.build_service = build_service

    def _canonical_character(self, character_id: str) -> dict:
        key = str(character_id or "").strip()
        if not key:
            raise ValueError("canonical character_id is required")
        character = self.build_service.canonical.catalog_service.get_character(key)
        if character is None:
            raise ValueError(f"canonical character {key!r} does not exist")
        player_id = str(character.get("player_id") or "").strip()
        if not player_id:
            raise ValueError(f"canonical character {key!r} has no player owner")
        if self.build_service.canonical.catalog_service.get_player(player_id) is None:
            raise ValueError(
                f"canonical character {key!r} references missing player {player_id!r}"
            )
        return character

    def binding_for_member(self, roster_member_id: int) -> CanonicalCharacterBinding | None:
        member = self.roster.get_member(int(roster_member_id))
        if member is None:
            raise ValueError(f"roster member {roster_member_id} does not exist")
        character_id = str(member.CanonicalCharacterId or "").strip()
        if not character_id:
            return None
        character = self._canonical_character(character_id)
        player_id = str(character.get("player_id") or "").strip()
        member_player_id = str(member.CanonicalPlayerId or "").strip()
        if member_player_id and member_player_id != player_id:
            raise ValueError(
                "roster member canonical player binding conflicts with canonical character owner"
            )
        return CanonicalCharacterBinding(
            roster_member_id=int(member.Id),
            canonical_character_id=character_id,
            canonical_player_id=player_id,
            character_name=str(character.get("name") or "").strip(),
        )

    def bind(
        self,
        *,
        roster_member_id: int,
        canonical_character_id: str,
    ) -> CanonicalCharacterBinding:
        member = self.roster.get_member(int(roster_member_id))
        if member is None:
            raise ValueError(f"roster member {roster_member_id} does not exist")
        character = self._canonical_character(canonical_character_id)
        character_id = str(character.get("character_id") or "").strip()
        player_id = str(character.get("player_id") or "").strip()

        existing_player_id = str(member.CanonicalPlayerId or "").strip()
        if existing_player_id and existing_player_id != player_id:
            raise ValueError(
                "canonical character owner conflicts with the member's canonical player binding"
            )

        conflict = self.database.execute(
            """
            SELECT id
            FROM roster_member
            WHERE canonical_character_id = ? AND id <> ?
            """,
            (character_id, int(roster_member_id)),
        ).fetchone()
        if conflict is not None:
            raise ValueError(
                f"canonical character {character_id!r} is already bound to roster member {int(conflict['id'])}"
            )

        self.database.execute(
            """
            UPDATE roster_member
            SET canonical_player_id = ?, canonical_character_id = ?
            WHERE id = ?
            """,
            (player_id, character_id, int(roster_member_id)),
        )
        self.database.commit()
        return CanonicalCharacterBinding(
            roster_member_id=int(roster_member_id),
            canonical_character_id=character_id,
            canonical_player_id=player_id,
            character_name=str(character.get("name") or "").strip(),
        )

    def clear(self, *, roster_member_id: int) -> None:
        if self.roster.get_member(int(roster_member_id)) is None:
            raise ValueError(f"roster member {roster_member_id} does not exist")
        self.database.execute(
            "UPDATE roster_member SET canonical_character_id = '' WHERE id = ?",
            (int(roster_member_id),),
        )
        self.database.commit()


__all__ = [
    "CanonicalCharacterBinding",
    "RosterCanonicalCharacterBindingService",
]
