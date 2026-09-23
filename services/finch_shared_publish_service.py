from __future__ import annotations

"""Explicit FoundryDock -> Finch shared operational publishing.

This module owns the outbound privacy boundary. Shared snapshots contain only the
small operational fields intentionally approved for collaboration. Local database
identity, private Personnel notes, draft state, URLs, and full build payloads do
not cross this boundary. Raid build handoff exposes only the small operational
subset needed to execute the selected seat: sets, weapons, skill bars, Mundus,
food, and potion.
"""

from dataclasses import dataclass
from pathlib import Path

from models.raid_plan import RaidPlan
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.finch_api_client import FinchApiClient, FinchSharedSnapshot
from services.raid_plan_repository import RaidPlanRepository
from services.raid_section_state_service import RaidSectionStateService
from services.raid_plan_saved_build_resolution_service import (
    RaidPlanSavedBuildResolutionService,
)
from services.roster_service import RosterService
from services.settings_service import SettingsService


_SHARED_TEAM_SCHEMA_VERSION = 2
_SHARED_RAID_PLAN_SCHEMA_VERSION = 5


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _house_stack_number(seat_id: object) -> int | None:
    seat = _clean(seat_id).casefold().replace("_", "-").replace(" ", "-")
    if not seat.startswith("dd-"):
        return None
    try:
        number = int(seat.split("-", 1)[1])
    except (TypeError, ValueError):
        return None
    return number if 1 <= number <= 8 else None


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


_TRIAL_ROLE_CAPACITY: dict[str, int] = {
    "Tank": 2,
    "Healer": 2,
    "Damage Dealer": 8,
}
_TRIAL_SEAT_CAPACITY = sum(_TRIAL_ROLE_CAPACITY.values())


def _team_seat_summary(members: list[dict[str, object]]) -> dict[str, object]:
    filled_by_role = {role: 0 for role in _TRIAL_ROLE_CAPACITY}
    for member in members:
        role = _shared_role(member.get("primary_role"))
        if role in filled_by_role:
            filled_by_role[role] += 1

    filled_by_role = {
        role: min(count, _TRIAL_ROLE_CAPACITY[role])
        for role, count in filled_by_role.items()
    }
    open_by_role = {
        role: _TRIAL_ROLE_CAPACITY[role] - filled_by_role[role]
        for role in _TRIAL_ROLE_CAPACITY
    }
    filled = sum(filled_by_role.values())
    return {
        "seat_capacity": _TRIAL_SEAT_CAPACITY,
        "filled_seats": filled,
        "open_seats": _TRIAL_SEAT_CAPACITY - filled,
        "open_seats_by_role": open_by_role,
    }


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

    members = _team_members(roster, canonical)
    return {
        "team_name": canonical,
        "schedule": {
            "slots": slots,
            "timezone": _clean(schedule.TimeZone) if schedule else "",
            "current_focus": _clean(schedule.CurrentFocus) if schedule else "",
        },
        "members": members,
        "roster": _team_seat_summary(members),
    }


def _weapon_label(primary, offhand) -> str:
    main_type = _clean(getattr(primary, "WeaponType", ""))
    off_type = _clean(getattr(offhand, "WeaponType", ""))
    if off_type.casefold() == "shield" and main_type:
        return "Sword & Board" if main_type.casefold() == "sword" else f"{main_type} & Shield"
    if main_type and off_type:
        return f"{main_type} + {off_type}"
    return main_type or off_type


def _operational_build_summary(plan: RaidPlan, member, saved_builds) -> dict[str, object]:
    summary: dict[str, object] = {
        "name": member.selected_build_name or "",
        "source_kind": member.build_source_kind or "",
        "source_name": member.build_source_name or "",
        "planned_gear_sets": list(member.planned_gear_sets),
        "planned_mundus": member.planned_mundus or "",
        "front_weapon": "",
        "back_weapon": "",
        "front_skills": [],
        "back_skills": [],
        "food": "",
        "potion": "",
    }
    resolution = RaidPlanSavedBuildResolutionService().resolve(
        raid_plan=plan,
        seat_id=member.seat_id,
        saved_builds=saved_builds,
    )
    if not resolution.resolved or resolution.build is None:
        if member.planned_skills:
            summary["front_skills"] = list(member.planned_skills)
        return summary

    build = resolution.build
    summary["front_weapon"] = _weapon_label(
        build.FrontBarWeapon,
        build.FrontBarOffHand,
    )
    summary["back_weapon"] = _weapon_label(
        build.BackBarWeapon,
        build.BackBarOffHand,
    )
    summary["front_skills"] = [
        _clean(value) for value in build.FrontBarSkills if _clean(value)
    ]
    summary["back_skills"] = [
        _clean(value) for value in build.BackBarSkills if _clean(value)
    ]
    summary["food"] = _clean(build.Food)
    summary["potion"] = _clean(build.Potion)
    if not summary["planned_mundus"]:
        summary["planned_mundus"] = _clean(build.Mundus)
    return summary


def shared_raid_plan_payload(
    plan: RaidPlan,
    *,
    saved_builds=(),
    raid_maps: dict[str, str] | None = None,
) -> dict[str, object]:
    if not isinstance(plan, RaidPlan):
        raise TypeError("plan must be a RaidPlan")
    saved = tuple(saved_builds or ())
    return {
        "plan_id": plan.plan_id,
        "name": plan.name,
        "trial_id": plan.trial_id,
        "team_name": plan.team_name or "",
        "difficulty": plan.difficulty or "",
        "status": plan.status,
        "raid_maps": dict(raid_maps or {}),
        "members": [
            {
                "seat_id": member.seat_id,
                "house_stack_number": _house_stack_number(member.seat_id),
                "gamertag": member.gamertag,
                "character_name": member.character_name or "",
                "role": _shared_role(member.role),
                "eso_class": member.eso_class or "",
                "primary_assignment": member.primary_assignment or "",
                "secondary_assignment": member.secondary_assignment or "",
                "utility_assignments": list(member.utility_assignments),
                "build_summary": _operational_build_summary(plan, member, saved),
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
    def __init__(
        self,
        *,
        client: FinchApiClient,
        roster: RosterService,
        build_service: BuildService | None = None,
    ) -> None:
        self.client = client
        self.roster = roster
        self.build_service = build_service

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

    def publish_raid_plan(self, plan: RaidPlan, *, raid_maps: dict[str, str] | None = None) -> FinchPublishResult:
        saved_builds = ()
        if self.build_service is not None:
            saved_builds = tuple(self.build_service.load().Members)
        payload = shared_raid_plan_payload(plan, saved_builds=saved_builds, raid_maps=raid_maps)
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
            build_service=BuildService(Path(database_path).with_name("builds.json")),
        ).publish_raid_plan(
            plan,
            raid_maps=RaidSectionStateService().raid_map_links(plan.plan_id),
        )
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
