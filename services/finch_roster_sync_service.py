from __future__ import annotations

"""Explicit Finch -> FoundryDock roster synchronization.

Only narrowly scoped operational data crosses this boundary. Finch never owns
Personnel, Teams, Builds, or Raid Plans. Pending gear-needs are applied to the
existing team-level roster assignment context only after exact identity/team
resolution succeeds.
"""

from dataclasses import dataclass
from pathlib import Path

from services.eso_database import EsoDatabase
from services.finch_api_client import FinchApiClient, FinchGearNeedRequest, FinchRegistration
from services.roster_assignment_context_service import RosterAssignmentContextService
from services.roster_player_identity_service import RosterPlayerIdentityService
from services.roster_service import RosterService
from services.settings_service import SettingsService


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _team_names(value: object) -> set[str]:
    return {
        _clean(piece).casefold()
        for piece in str(value or "").split(",")
        if _clean(piece)
    }


@dataclass(frozen=True, slots=True)
class FinchGearNeedSyncResult:
    request_id: int
    team_name: str
    player_name: str
    gear_needed: str
    status: str
    message: str
    roster_member_id: int | None = None


@dataclass(frozen=True, slots=True)
class FinchGearNeedSyncSummary:
    fetched: int
    applied: int
    rejected: int
    errors: int
    results: tuple[FinchGearNeedSyncResult, ...]
    registrations_fetched: int = 0
    registrations_applied: int = 0
    registrations_unresolved: int = 0


class FinchRosterSyncService:
    """Apply Finch operational requests to canonical local roster state."""

    def __init__(
        self,
        *,
        client: FinchApiClient,
        roster: RosterService,
        identity: RosterPlayerIdentityService,
        assignments: RosterAssignmentContextService,
    ) -> None:
        self.client = client
        self.roster = roster
        self.identity = identity
        self.assignments = assignments
        self._ensure_identity_binding_schema()

    def _ensure_identity_binding_schema(self) -> None:
        self.roster.db.execute(
            """
            CREATE TABLE IF NOT EXISTS finch_discord_identity_binding (
                discord_user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                roster_member_id INTEGER NOT NULL,
                first_seen TEXT NOT NULL DEFAULT (datetime('now')),
                last_seen TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (discord_user_id, guild_id)
            )
            """
        )
        self.roster.db.commit()

    def _bound_member(self, registration: FinchRegistration):
        row = self.roster.db.execute(
            """
            SELECT roster_member_id
            FROM finch_discord_identity_binding
            WHERE discord_user_id = ? AND guild_id = ?
            """,
            (registration.discord_user_id, registration.guild_id),
        ).fetchone()
        if row is None:
            return None
        member = self.roster.get_member(int(row["roster_member_id"]))
        if member is None:
            return None
        return member

    def _bind_registration(self, registration: FinchRegistration, member_id: int) -> None:
        self.roster.db.execute(
            """
            INSERT INTO finch_discord_identity_binding (
                discord_user_id, guild_id, roster_member_id
            ) VALUES (?, ?, ?)
            ON CONFLICT(discord_user_id, guild_id) DO UPDATE SET
                roster_member_id=excluded.roster_member_id,
                last_seen=datetime('now')
            """,
            (registration.discord_user_id, registration.guild_id, int(member_id)),
        )
        self.roster.db.commit()

    @staticmethod
    def _public_discord_name(registration: FinchRegistration) -> str:
        return (
            _clean(registration.discord_display_name)
            or _clean(registration.discord_global_name)
            or _clean(registration.discord_username)
        )

    def _resolve_registration_member(self, registration: FinchRegistration):
        bound = self._bound_member(registration)
        if bound is not None:
            return bound

        resolution, _problem = self._resolve_member(registration)
        if resolution is not None:
            member, _canonical_team = resolution
            return member

        seen_values = [
            _clean(item.value)
            for item in registration.identity_history
            if _clean(item.value)
        ]
        matches = {}
        for value in seen_values:
            for member in self.identity.matching_members(value):
                if member.Id is not None:
                    matches[int(member.Id)] = member
        if len(matches) == 1:
            return next(iter(matches.values()))
        return None

    def sync_registration_identities(self) -> tuple[int, int, int]:
        registrations = self.client.registrations_private()
        applied = 0
        unresolved = 0

        for registration in registrations:
            member = self._resolve_registration_member(registration)
            if member is None or member.Id is None:
                unresolved += 1
                continue

            member_id = int(member.Id)
            self._bind_registration(registration, member_id)

            current_discord = self._public_discord_name(registration)
            if current_discord and _clean(member.DiscordName) != current_discord:
                member.DiscordName = current_discord
                self.roster.update_member(member)

            for item in registration.identity_history:
                value = _clean(item.value)
                if not value:
                    continue
                source = (
                    "finch_gamertag_history"
                    if item.kind == "gamertag"
                    else "finch_discord_history"
                )
                note_bits = [item.kind]
                if item.first_seen:
                    note_bits.append(f"first seen {item.first_seen}")
                if item.last_seen:
                    note_bits.append(f"last seen {item.last_seen}")
                self.identity.add_alias(
                    member_id,
                    value,
                    source=source,
                    notes=" · ".join(note_bits),
                )
            applied += 1

        return len(registrations), applied, unresolved


    def _reject(
        self,
        request: FinchGearNeedRequest,
        message: str,
    ) -> FinchGearNeedSyncResult:
        self.client.acknowledge_gear_need(
            request.request_id,
            status="rejected",
            message=message,
        )
        return FinchGearNeedSyncResult(
            request_id=request.request_id,
            team_name=request.team_name,
            player_name=request.player_name,
            gear_needed=request.gear_needed,
            status="rejected",
            message=message,
        )

    def _resolve_member(self, request: FinchGearNeedRequest):
        team = _clean(request.team_name)
        player = _clean(request.player_name)
        if not team:
            return None, "Finch request has no Team name."
        if not player:
            return None, "Finch request has no Personnel player name."

        known_teams = {
            _clean(name).casefold(): _clean(name)
            for name in self.roster.list_team_names()
            if _clean(name)
        }
        canonical_team = known_teams.get(team.casefold())
        if canonical_team is None:
            return None, f"Team '{team}' does not exist in this FoundryDock roster."

        active_matches = [
            member
            for member in self.identity.matching_members(player)
            if canonical_team.casefold() in _team_names(member.Team)
        ]
        if len(active_matches) == 1:
            return (active_matches[0], canonical_team), ""

        if len(active_matches) > 1:
            return None, (
                f"Personnel identity '{player}' is ambiguous on team "
                f"'{canonical_team}'; FoundryDock did not guess."
            )

        all_matches = self.identity.matching_members(player, include_archived=True)
        archived_matches = [
            member
            for member in all_matches
            if str(member.Status or "").strip().casefold() == "archived"
        ]
        if archived_matches:
            return None, (
                f"Personnel identity '{player}' resolves only to archived Personnel; "
                "restore or re-register the active identity before syncing."
            )

        active_identity_matches = self.identity.matching_members(player)
        if active_identity_matches:
            return None, (
                f"Personnel identity '{player}' exists, but is not assigned to "
                f"team '{canonical_team}'."
            )

        return None, (
            f"Personnel identity '{player}' is not known by current gamertag or "
            "an explicit alias."
        )

    def sync_gear_needs(self) -> FinchGearNeedSyncSummary:
        registrations_fetched = 0
        registrations_applied = 0
        registrations_unresolved = 0
        try:
            (
                registrations_fetched,
                registrations_applied,
                registrations_unresolved,
            ) = self.sync_registration_identities()
        except Exception:
            # Gear-needs synchronization remains useful even when an older Finch
            # server does not yet expose the private registration feed.
            pass

        requests = self.client.pending_gear_needs()
        results: list[FinchGearNeedSyncResult] = []

        for request in requests:
            try:
                resolution, problem = self._resolve_member(request)
                if resolution is None:
                    results.append(self._reject(request, problem))
                    continue

                member, canonical_team = resolution
                member_id = int(member.Id)
                self.assignments.set_field(
                    member_id,
                    team_name=canonical_team,
                    encounter_id="",
                    field="gear_needed",
                    value=request.gear_needed,
                )
                self.client.acknowledge_gear_need(
                    request.request_id,
                    status="applied",
                    message=(
                        f"Applied to {member.PlayerName} / {canonical_team} "
                        "team-level Gear Needed."
                    ),
                )
                results.append(
                    FinchGearNeedSyncResult(
                        request_id=request.request_id,
                        team_name=canonical_team,
                        player_name=str(member.PlayerName or request.player_name),
                        gear_needed=request.gear_needed,
                        status="applied",
                        message="Applied to team-level Gear Needed.",
                        roster_member_id=member_id,
                    )
                )
            except Exception as exc:
                results.append(
                    FinchGearNeedSyncResult(
                        request_id=request.request_id,
                        team_name=request.team_name,
                        player_name=request.player_name,
                        gear_needed=request.gear_needed,
                        status="error",
                        message=str(exc),
                    )
                )

        return FinchGearNeedSyncSummary(
            fetched=len(requests),
            applied=sum(1 for row in results if row.status == "applied"),
            rejected=sum(1 for row in results if row.status == "rejected"),
            errors=sum(1 for row in results if row.status == "error"),
            results=tuple(results),
            registrations_fetched=registrations_fetched,
            registrations_applied=registrations_applied,
            registrations_unresolved=registrations_unresolved,
        )


def sync_finch_gear_needs(
    *,
    database_path: Path,
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> FinchGearNeedSyncSummary:
    """Run one explicit Finch sync using a worker-owned SQLite connection."""
    settings = SettingsService(Path(settings_path)).load()
    client = FinchApiClient(
        base_url=str(settings.get("FinchApiUrl") or ""),
        api_key=str(settings.get("FinchApiKey") or ""),
        timeout=timeout,
    )
    database = EsoDatabase(Path(database_path))
    try:
        roster = RosterService(database)
        service = FinchRosterSyncService(
            client=client,
            roster=roster,
            identity=RosterPlayerIdentityService(database),
            assignments=RosterAssignmentContextService(database),
        )
        return service.sync_gear_needs()
    finally:
        database.close()


__all__ = [
    "FinchGearNeedSyncResult",
    "FinchGearNeedSyncSummary",
    "FinchRosterSyncService",
    "sync_finch_gear_needs",
]
