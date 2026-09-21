from __future__ import annotations

"""Explicit Finch -> FoundryDock roster synchronization.

Only narrowly scoped operational data crosses this boundary. Finch never owns
Personnel, Teams, Builds, or Raid Plans. Pending gear-needs are applied to the
existing team-level roster assignment context only after exact identity/team
resolution succeeds.
"""

from dataclasses import dataclass

from services.finch_api_client import FinchApiClient, FinchGearNeedRequest
from services.roster_assignment_context_service import RosterAssignmentContextService
from services.roster_player_identity_service import RosterPlayerIdentityService
from services.roster_service import RosterService


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
        )


__all__ = [
    "FinchGearNeedSyncResult",
    "FinchGearNeedSyncSummary",
    "FinchRosterSyncService",
]
