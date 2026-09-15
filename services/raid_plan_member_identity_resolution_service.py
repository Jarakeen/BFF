from __future__ import annotations

"""Validate stable RaidPlan player, character, and build identity relationships.

This service deliberately does not infer identity from gamertag, character name, or build
name. Stable IDs are authoritative when present; names remain display and legacy evidence.
"""

from dataclasses import dataclass

from models.raid_plan import RaidPlanMember
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_service import RosterService


def _clean(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class RaidPlanMemberIdentityResolution:
    roster_member_id: int | None
    player_id: str | None
    character_id: str | None
    selected_build_id: str | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class RaidPlanMemberIdentityResolutionService:
    """Fail closed when one stable RaidPlan identity contradicts another."""

    def __init__(self, database: EsoDatabase, build_service: BuildService):
        self.roster = RosterService(database)
        self.catalog = build_service.canonical.catalog_service

    def _roster_members_for_character(self, character_id: str):
        key = _clean(character_id)
        if not key:
            return ()
        return tuple(
            member
            for member in self.roster.list_members()
            if _clean(member.CanonicalCharacterId) == key
        )

    def resolve(self, member: RaidPlanMember) -> RaidPlanMemberIdentityResolution:
        if not isinstance(member, RaidPlanMember):
            raise TypeError("raid plan member identity resolution requires RaidPlanMember")

        unresolved: list[str] = []
        roster_member_id = member.roster_member_id
        player_id = _clean(member.player_id) or None
        character_id = _clean(member.character_id) or None
        build_id = _clean(member.selected_build_id) or None

        roster_member = None
        if roster_member_id is not None:
            roster_member = self.roster.get_member(roster_member_id)
            if roster_member is None:
                unresolved.append(f"roster member {roster_member_id} does not exist")
            else:
                roster_player_id = _clean(roster_member.CanonicalPlayerId) or None
                roster_character_id = _clean(roster_member.CanonicalCharacterId) or None
                if player_id and roster_player_id and player_id != roster_player_id:
                    unresolved.append(
                        "RaidPlan player_id disagrees with Personnel canonical player identity"
                    )
                elif not player_id and roster_player_id:
                    player_id = roster_player_id
                if character_id and roster_character_id and character_id != roster_character_id:
                    unresolved.append(
                        "RaidPlan character_id disagrees with Personnel canonical character identity"
                    )
                elif not character_id and roster_character_id:
                    character_id = roster_character_id

        player = None
        if player_id:
            player = self.catalog.get_player(player_id)
            if player is None:
                unresolved.append(f"canonical player {player_id!r} does not exist")

        character = None
        if character_id:
            character = self.catalog.get_character(character_id)
            if character is None:
                unresolved.append(f"canonical character {character_id!r} does not exist")
            else:
                character_player_id = _clean(character.get("player_id")) or None
                if player_id and character_player_id and character_player_id != player_id:
                    unresolved.append(
                        "canonical character does not belong to RaidPlan player_id"
                    )
                elif not player_id and character_player_id:
                    player_id = character_player_id
                    player = self.catalog.get_player(player_id)
                    if player is None:
                        unresolved.append(
                            f"canonical player {player_id!r} for character does not exist"
                        )

        if build_id:
            build = self.catalog.get_build(build_id)
            if build is None:
                unresolved.append(f"canonical build {build_id!r} does not exist")
            else:
                build_character_id = _clean(build.get("character_id")) or None
                if character_id and build_character_id and build_character_id != character_id:
                    unresolved.append(
                        "selected build does not belong to RaidPlan character_id"
                    )
                elif not character_id and build_character_id:
                    character_id = build_character_id
                    character = self.catalog.get_character(character_id)
                    if character is None:
                        unresolved.append(
                            f"canonical character {character_id!r} for selected build does not exist"
                        )
                    else:
                        character_player_id = _clean(character.get("player_id")) or None
                        if player_id and character_player_id and character_player_id != player_id:
                            unresolved.append(
                                "selected build character does not belong to RaidPlan player_id"
                            )
                        elif not player_id and character_player_id:
                            player_id = character_player_id
                            if self.catalog.get_player(player_id) is None:
                                unresolved.append(
                                    f"canonical player {player_id!r} for selected build does not exist"
                                )

        # A canonical character may identify one Personnel row because Personnel enforces
        # unique non-empty CanonicalCharacterId values. This is a stable-ID join, not a
        # character-name or gamertag inference. Do not attempt the inverse player-only join:
        # one player may legitimately own multiple roster characters.
        if roster_member_id is None and character_id:
            roster_matches = self._roster_members_for_character(character_id)
            if len(roster_matches) > 1:
                unresolved.append(
                    f"multiple Personnel rows claim canonical character {character_id!r}"
                )
            elif len(roster_matches) == 1:
                roster_member = roster_matches[0]
                roster_member_id = int(roster_member.Id)
                roster_player_id = _clean(roster_member.CanonicalPlayerId) or None
                if player_id and roster_player_id and player_id != roster_player_id:
                    unresolved.append(
                        "canonical character Personnel owner disagrees with RaidPlan player_id"
                    )
                elif not player_id and roster_player_id:
                    player_id = roster_player_id

        return RaidPlanMemberIdentityResolution(
            roster_member_id=roster_member_id,
            player_id=player_id,
            character_id=character_id,
            selected_build_id=build_id,
            unresolved=tuple(unresolved),
        )


__all__ = [
    "RaidPlanMemberIdentityResolution",
    "RaidPlanMemberIdentityResolutionService",
]
