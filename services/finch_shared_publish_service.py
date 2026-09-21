from __future__ import annotations

"""Explicit FoundryDock -> Finch shared operational publishing.

This module owns the outbound privacy boundary. Shared snapshots contain only the
small operational fields intentionally approved for collaboration. Local database
identity, private Personnel notes, draft state, URLs, and full build payloads do
not cross this boundary.
"""

from dataclasses import dataclass
from pathlib import Path

from models.raid_plan import RaidPlan
from services.eso_database import EsoDatabase
from services.finch_api_client import FinchApiClient, FinchSharedSnapshot
from services.raid_plan_repository import RaidPlanRepository
from services.roster_service import RosterService
from services.settings_service import SettingsService


_SHARED_TEAM_SCHEMA_VERSION = 1
_SHARED_RAID_PLAN_SCHEMA_VERSION = 1


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _shared_role(value: object) -> str:
    """Return stable human-facing role labels for cross-client snapshots."""
    role = _clean(value)
    folded = role.casefold()
    if folded in {"dd", "dps", "damage", "damage dealer"}:
        return "Damage Dealer"
    if folded in {"tank"}:
        return "Tank"
    if folded in {"healer", "heal", "heals", "healing"}:
        return "Healer"
    return role


def _team_members(roster: RosterService, team_name: str) -> list[dict[str, object]]:
    wanted = _clean(team_name).casefold()
    members: list[dict[str, object]] = []
    for member in roster.list_members():
        teams = {
            _clean(piece).casefold()
            for piece in str(member.Team or "").split(",")
            if _clean(piece)
        }
        if wanted not in teams:
            continue
        members.append(
            {
                "player_name": _clean(member.PlayerName),
                "character_name": _clean(member.CharacterName),
                "eso_class": _clean(member.EsoClass),
                "primary_role": _shared_role(member.PrimaryRole),
                "secondary_role": _shared_role(member.SecondaryRole),
                "status": _clean(member.Status),
            }
        )
    members.sort(
        key=lambda row: (
            str(row["player_name"]).casefold(),
            str(row["character_name"]).casefold(),
        )
    )
    return members


def shared_team_payload(roster: RosterService, team_name: str) -> dict[str, object]:
    name = _clean(team_name)
    if not name:
        raise ValueError("Team name is required before publishing.")
    canonical = next(
        (
            existing
            for existing in roster.list_team_names()
            if existing.casefold() == name.casefold()
        ),
        None,
    )
    if canonical is None:
        raise ValueError(f"Team {name!r} does not exist in FoundryDock.")

    schedule = roster.get_team_schedule(canonical)
    slots: list[dict[str, str]] = []
    if schedule is not None:
        slots = [
            {
                "day": _clean(slot.Day),
                "start_time": _clean(slot.StartTime),
                "end_time": _clean(slot.EndTime),
            }
            for slot in schedule.effective_slots
        ]

    return {
        "team_name": canonical,
        "schedule": {
            "slots": slots,
            "timezone": _clean(schedule.TimeZone) if schedule else "",
            "current_focus": _clean(schedule.CurrentFocus) if schedule else "",
        },
        "members": _team_members(roster, canonical),
    }


def shared_raid_plan_payload(plan: RaidPlan) -> dict[str, object]:
    if not isinstance(plan, RaidPlan):
        raise TypeError("plan must be a RaidPlan")
    return {
        "plan_id": plan.plan_id,
        "name": plan.name,
        "trial_id": plan.trial_id,
        "team_name": plan.team_name or "",
        "difficulty": plan.difficulty or "",
        "status": plan.status,
        "members": [
            {
                "seat_id": member.seat_id,
                "gamertag": member.gamertag,
                "character_name": member.character_name or "",
                "role": _shared_role(member.role),
                "eso_class": member.eso_class or "",
            }
            for member in plan.members
        ],
    }


@dataclass(frozen=True, slots=True)
class FinchPublishResult:
    kind: str
    snapshot_key: str
    published_by: str
    updated_at: str


class FinchSharedPublishService:
    def __init__(self, *, client: FinchApiClient, roster: RosterService) -> None:
        self.client = client
        self.roster = roster

    @staticmethod
    def _result(snapshot: FinchSharedSnapshot) -> FinchPublishResult:
        return FinchPublishResult(
            kind=snapshot.kind,
            snapshot_key=snapshot.snapshot_key,
            published_by=snapshot.published_by,
            updated_at=snapshot.updated_at,
        )

    def publish_team(self, team_name: str) -> FinchPublishResult:
        payload = shared_team_payload(self.roster, team_name)
        snapshot = self.client.publish_shared_team(
            snapshot_key=str(payload["team_name"]),
            payload=payload,
            schema_version=_SHARED_TEAM_SCHEMA_VERSION,
        )
        return self._result(snapshot)

    def publish_raid_plan(self, plan: RaidPlan) -> FinchPublishResult:
        payload = shared_raid_plan_payload(plan)
        snapshot = self.client.publish_shared_raid_plan(
            snapshot_key=plan.plan_id,
            payload=payload,
            schema_version=_SHARED_RAID_PLAN_SCHEMA_VERSION,
        )
        return self._result(snapshot)


def _configured_client(
    *,
    settings_path: Path,
    timeout: float,
) -> FinchApiClient:
    settings = SettingsService(Path(settings_path)).load()
    return FinchApiClient(
        base_url=str(settings.get("FinchApiUrl") or ""),
        api_key=str(settings.get("FinchApiKey") or ""),
        timeout=timeout,
    )


def publish_team_to_finch(
    *,
    database_path: Path,
    team_name: str,
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> FinchPublishResult:
    database = EsoDatabase(Path(database_path))
    try:
        roster = RosterService(database)
        return FinchSharedPublishService(
            client=_configured_client(settings_path=settings_path, timeout=timeout),
            roster=roster,
        ).publish_team(team_name)
    finally:
        database.close()


def publish_raid_plan_to_finch(
    *,
    database_path: Path,
    raid_plans_path: Path,
    plan_id: str,
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> FinchPublishResult:
    repository = RaidPlanRepository(Path(raid_plans_path))
    plan = repository.get(plan_id)
    if plan is None:
        raise ValueError(f"Saved Raid Plan {plan_id!r} does not exist.")

    database = EsoDatabase(Path(database_path))
    try:
        roster = RosterService(database)
        return FinchSharedPublishService(
            client=_configured_client(settings_path=settings_path, timeout=timeout),
            roster=roster,
        ).publish_raid_plan(plan)
    finally:
        database.close()


__all__ = [
    "FinchPublishResult",
    "FinchSharedPublishService",
    "publish_raid_plan_to_finch",
    "publish_team_to_finch",
    "shared_raid_plan_payload",
    "shared_team_payload",
]
