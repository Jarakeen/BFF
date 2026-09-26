from __future__ import annotations

"""Explicitly bind Personnel rows to canonical Build Catalog player identities.

This service never guesses identity from names. A binding is accepted only when the caller
supplies a real Build Catalog ``player_id``. Multiple Personnel rows may reference the same
player because the current roster model is still player+character shaped. Character binding
owns the one-to-one row identity and must remain consistent with its canonical player.
"""

from dataclasses import dataclass

from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_service import RosterService
from services.roster_workspace_pydantic_schema import validate_canonical_personnel_binding


@dataclass(frozen=True)
class CanonicalPlayerBinding:
    roster_member_id: int
    canonical_player_id: str
    gamertag: str


class RosterCanonicalPlayerBindingService:
    def __init__(self, database: EsoDatabase, build_service: BuildService):
        self.roster = RosterService(database)
        self.database = self.roster.db
        self.build_service = build_service

    def _canonical_player(self, player_id: str) -> dict:
        key = str(player_id or "").strip()
        if not key:
            raise ValueError("canonical player_id is required")
        player = self.build_service.canonical.catalog_service.get_player(key)
        if player is None:
            raise ValueError(f"canonical player {key!r} does not exist")
        return player

    def binding_for_member(self, roster_member_id: int) -> CanonicalPlayerBinding | None:
        member = self.roster.get_member(int(roster_member_id))
        if member is None:
            raise ValueError(f"roster member {roster_member_id} does not exist")
        player_id = str(member.CanonicalPlayerId or "").strip()
        if not player_id:
            return None
        player = self._canonical_player(player_id)
        return CanonicalPlayerBinding(
            roster_member_id=int(member.Id),
            canonical_player_id=player_id,
            gamertag=str(player.get("gamertag") or "").strip(),
        )

    def bind(self, *, roster_member_id: int, canonical_player_id: str) -> CanonicalPlayerBinding:
        member = self.roster.get_member(int(roster_member_id))
        if member is None:
            raise ValueError(f"roster member {roster_member_id} does not exist")
        player = self._canonical_player(canonical_player_id)
        player_id = str(player.get("player_id") or "").strip()

        character_id = str(member.CanonicalCharacterId or "").strip()
        if character_id:
            character = self.build_service.canonical.catalog_service.get_character(character_id)
            if character is None:
                raise ValueError(
                    f"roster member references missing canonical character {character_id!r}"
                )
            character_player_id = str(character.get("player_id") or "").strip()
            if character_player_id != player_id:
                raise ValueError(
                    "canonical player binding conflicts with the member's canonical character owner"
                )

        payload = validate_canonical_personnel_binding({
            "roster_member_id": int(roster_member_id),
            "canonical_player_id": player_id,
            "canonical_character_id": character_id,
        })
        self.database.execute("BEGIN IMMEDIATE")
        try:
            self.database.execute(
                "UPDATE roster_member SET canonical_player_id = ? WHERE id = ?",
                (payload["canonical_player_id"], payload["roster_member_id"]),
            )
            row = self.database.execute(
                "SELECT canonical_player_id, canonical_character_id FROM roster_member WHERE id = ?",
                (payload["roster_member_id"],),
            ).fetchone()
            if row is None or str(row["canonical_player_id"] or "") != payload["canonical_player_id"] or str(row["canonical_character_id"] or "") != payload["canonical_character_id"]:
                raise RuntimeError("canonical player binding did not round-trip exactly")
            self.database.commit()
        except Exception:
            self.database.rollback()
            raise
        return CanonicalPlayerBinding(
            roster_member_id=int(roster_member_id),
            canonical_player_id=player_id,
            gamertag=str(player.get("gamertag") or "").strip(),
        )

    def clear(self, *, roster_member_id: int) -> None:
        member = self.roster.get_member(int(roster_member_id))
        if member is None:
            raise ValueError(f"roster member {roster_member_id} does not exist")
        if str(member.CanonicalCharacterId or "").strip():
            raise ValueError("clear the canonical character binding before clearing its player")
        member_id = int(roster_member_id)
        self.database.execute("BEGIN IMMEDIATE")
        try:
            self.database.execute(
                "UPDATE roster_member SET canonical_player_id = '' WHERE id = ?",
                (member_id,),
            )
            row = self.database.execute(
                "SELECT canonical_player_id FROM roster_member WHERE id = ?", (member_id,)
            ).fetchone()
            if row is None or str(row["canonical_player_id"] or "") != "":
                raise RuntimeError("canonical player binding clear did not round-trip exactly")
            self.database.commit()
        except Exception:
            self.database.rollback()
            raise


__all__ = ["CanonicalPlayerBinding", "RosterCanonicalPlayerBindingService"]
