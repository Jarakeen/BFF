from __future__ import annotations

"""Explicitly bind Personnel records to canonical Build Catalog player identities.

This service never guesses identity from names. A binding is accepted only when the caller
supplies a real Build Catalog ``player_id``. One canonical player may be bound to at most
one Personnel record; ambiguous or conflicting state fails closed.
"""

from dataclasses import dataclass

from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_service import RosterService


@dataclass(frozen=True)
class CanonicalPlayerBinding:
    roster_member_id: int
    canonical_player_id: str
    gamertag: str


class RosterCanonicalPlayerBindingService:
    def __init__(self, database: EsoDatabase, build_service: BuildService):
        self.database = database
        self.roster = RosterService(database)
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
        conflict = self.database.execute(
            """
            SELECT id
            FROM roster_member
            WHERE canonical_player_id = ? AND id <> ?
            """,
            (player_id, int(roster_member_id)),
        ).fetchone()
        if conflict is not None:
            raise ValueError(
                f"canonical player {player_id!r} is already bound to roster member {int(conflict['id'])}"
            )
        self.database.execute(
            "UPDATE roster_member SET canonical_player_id = ? WHERE id = ?",
            (player_id, int(roster_member_id)),
        )
        self.database.commit()
        return CanonicalPlayerBinding(
            roster_member_id=int(roster_member_id),
            canonical_player_id=player_id,
            gamertag=str(player.get("gamertag") or "").strip(),
        )

    def clear(self, *, roster_member_id: int) -> None:
        if self.roster.get_member(int(roster_member_id)) is None:
            raise ValueError(f"roster member {roster_member_id} does not exist")
        self.database.execute(
            "UPDATE roster_member SET canonical_player_id = '' WHERE id = ?",
            (int(roster_member_id),),
        )
        self.database.commit()


__all__ = ["CanonicalPlayerBinding", "RosterCanonicalPlayerBindingService"]
