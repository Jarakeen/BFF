from __future__ import annotations

"""Discord-to-Personnel registration for Finch.

This store contains only Discord identity bindings. Personnel, Team membership,
Raid Plans, and Builds remain authoritative in FoundryDock.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable

from services.roster_service import RosterService


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _teams(value: object) -> tuple[str, ...]:
    return tuple(
        part.strip()
        for part in str(value or "").split(",")
        if part.strip()
    )


@dataclass(frozen=True, slots=True)
class FinchRegistration:
    discord_user_id: int
    guild_id: int
    team_name: str
    roster_member_id: int
    player_name: str
    canonical_player_id: str = ""
    registered_at: str = ""


class FinchRegistrationStore:
    """Persist lightweight Discord identity bindings outside canonical raid data."""

    def __init__(self, *, path: Path, roster_service: RosterService) -> None:
        self.path = Path(path)
        self.roster_service = roster_service

    def _load(self) -> list[FinchRegistration]:
        if not self.path.is_file():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []
        rows = payload.get("registrations", []) if isinstance(payload, dict) else []
        result: list[FinchRegistration] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                result.append(
                    FinchRegistration(
                        discord_user_id=int(row.get("discord_user_id") or 0),
                        guild_id=int(row.get("guild_id") or 0),
                        team_name=_clean(row.get("team_name")),
                        roster_member_id=int(row.get("roster_member_id") or 0),
                        player_name=_clean(row.get("player_name")),
                        canonical_player_id=_clean(row.get("canonical_player_id")),
                        registered_at=_clean(row.get("registered_at")),
                    )
                )
            except (TypeError, ValueError):
                continue
        return [row for row in result if row.discord_user_id and row.guild_id]

    def _save(self, rows: Iterable[FinchRegistration]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "registrations": [asdict(row) for row in rows],
        }
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

    def get(self, *, discord_user_id: int, guild_id: int) -> FinchRegistration | None:
        for row in self._load():
            if row.discord_user_id == int(discord_user_id) and row.guild_id == int(guild_id):
                return row
        return None

    def register(
        self,
        *,
        discord_user_id: int,
        guild_id: int,
        team_name: str,
        player_ref: str,
    ) -> FinchRegistration:
        wanted_team = _clean(team_name)
        wanted_player = _clean(player_ref).casefold()
        if not wanted_team or not wanted_player:
            raise LookupError("Team and player name are both required.")

        team_matches = [
            name
            for name in self.roster_service.list_team_names()
            if _clean(name).casefold() == wanted_team.casefold()
        ]
        if len(team_matches) != 1:
            raise LookupError(f"Could not uniquely match team {team_name!r}.")
        team = team_matches[0]

        matches = []
        for member in self.roster_service.list_members():
            member_teams = {_clean(name).casefold() for name in _teams(member.Team)}
            if _clean(team).casefold() not in member_teams:
                continue
            aliases = {
                _clean(member.PlayerName).casefold(),
                _clean(member.DiscordName).casefold(),
            }
            if wanted_player in aliases:
                matches.append(member)

        if not matches:
            raise LookupError(
                f"Could not match {player_ref!r} to a Personnel player on {team}."
            )

        distinct_players = {_clean(member.PlayerName).casefold() for member in matches}
        if len(distinct_players) != 1:
            raise LookupError(
                f"{player_ref!r} matches more than one Personnel player on {team}."
            )

        member = sorted(matches, key=lambda item: int(item.Id or 0))[0]
        registration = FinchRegistration(
            discord_user_id=int(discord_user_id),
            guild_id=int(guild_id),
            team_name=team,
            roster_member_id=int(member.Id or 0),
            player_name=_clean(member.PlayerName),
            canonical_player_id=_clean(member.CanonicalPlayerId),
            registered_at=datetime.now(timezone.utc).isoformat(),
        )

        rows = [
            row
            for row in self._load()
            if not (
                row.discord_user_id == registration.discord_user_id
                and row.guild_id == registration.guild_id
            )
        ]
        rows.append(registration)
        self._save(rows)
        return registration

    def unregister(self, *, discord_user_id: int, guild_id: int) -> bool:
        rows = self._load()
        kept = [
            row
            for row in rows
            if not (
                row.discord_user_id == int(discord_user_id)
                and row.guild_id == int(guild_id)
            )
        ]
        if len(kept) == len(rows):
            return False
        self._save(kept)
        return True


__all__ = ["FinchRegistration", "FinchRegistrationStore"]
