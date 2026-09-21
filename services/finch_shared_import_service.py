from __future__ import annotations

"""Read and explicitly import versioned Finch shared operational snapshots.

Shared Team import creates/updates only Team metadata and recurring schedule. It
never creates Personnel rows from remote member names.

Shared Raid Plan import writes only a RaidPlan snapshot keyed by stable plan_id.
It never creates Personnel, Characters, Saved Builds, or local build identity.
"""

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from models.raid_plan import RaidPlan, RaidPlanMember
from models.team_schedule import TeamSchedule, TeamScheduleSlot
from services.eso_database import EsoDatabase
from services.finch_api_client import FinchApiClient, FinchSharedSnapshot
from services.raid_plan_repository import RaidPlanRepository
from services.roster_service import RosterService
from services.settings_service import SettingsService


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _payload(snapshot: FinchSharedSnapshot, *, kind: str) -> dict[str, object]:
    if snapshot.kind != kind:
        raise ValueError(
            f"Expected Finch shared {kind!r} snapshot, got {snapshot.kind!r}."
        )
    if snapshot.schema_version != 1:
        raise ValueError(
            f"Unsupported Finch shared {kind} schema version: {snapshot.schema_version}"
        )
    return dict(snapshot.payload)


@dataclass(frozen=True, slots=True)
class FinchSharedTeamPreview:
    snapshot_key: str
    team_name: str
    member_count: int
    timezone: str
    current_focus: str
    published_by: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class FinchSharedRaidPlanPreview:
    snapshot_key: str
    plan_id: str
    name: str
    trial_id: str
    team_name: str
    difficulty: str
    member_count: int
    published_by: str
    updated_at: str


class FinchSharedImportService:
    def __init__(
        self,
        *,
        client: FinchApiClient,
        roster: RosterService,
        raid_plans: RaidPlanRepository,
    ) -> None:
        self.client = client
        self.roster = roster
        self.raid_plans = raid_plans

    @staticmethod
    def team_preview(snapshot: FinchSharedSnapshot) -> FinchSharedTeamPreview:
        body = _payload(snapshot, kind="team")
        schedule = body.get("schedule")
        if not isinstance(schedule, dict):
            schedule = {}
        members = body.get("members")
        if not isinstance(members, list):
            members = []
        return FinchSharedTeamPreview(
            snapshot_key=snapshot.snapshot_key,
            team_name=_clean(body.get("team_name")),
            member_count=len(members),
            timezone=_clean(schedule.get("timezone")),
            current_focus=_clean(schedule.get("current_focus")),
            published_by=snapshot.published_by,
            updated_at=snapshot.updated_at,
        )

    @staticmethod
    def raid_plan_preview(
        snapshot: FinchSharedSnapshot,
    ) -> FinchSharedRaidPlanPreview:
        body = _payload(snapshot, kind="raid_plan")
        members = body.get("members")
        if not isinstance(members, list):
            members = []
        return FinchSharedRaidPlanPreview(
            snapshot_key=snapshot.snapshot_key,
            plan_id=_clean(body.get("plan_id")),
            name=_clean(body.get("name")),
            trial_id=_clean(body.get("trial_id")),
            team_name=_clean(body.get("team_name")),
            difficulty=_clean(body.get("difficulty")),
            member_count=len(members),
            published_by=snapshot.published_by,
            updated_at=snapshot.updated_at,
        )

    def list_shared_teams(self) -> tuple[FinchSharedTeamPreview, ...]:
        return tuple(
            self.team_preview(snapshot)
            for snapshot in self.client.shared_teams()
        )

    def list_shared_raid_plans(self) -> tuple[FinchSharedRaidPlanPreview, ...]:
        return tuple(
            self.raid_plan_preview(snapshot)
            for snapshot in self.client.shared_raid_plans()
        )

    def import_team_metadata(self, snapshot_key: str) -> str:
        snapshot = self.client.shared_team(snapshot_key)
        body = _payload(snapshot, kind="team")
        team_name = _clean(body.get("team_name"))
        if not team_name:
            raise ValueError("Shared Team snapshot has no Team name.")

        schedule_raw = body.get("schedule")
        if not isinstance(schedule_raw, dict):
            schedule_raw = {}
        raw_slots = schedule_raw.get("slots")
        slots: list[TeamScheduleSlot] = []
        if isinstance(raw_slots, list):
            for raw in raw_slots:
                if not isinstance(raw, dict):
                    continue
                day = _clean(raw.get("day"))
                start = _clean(raw.get("start_time"))
                end = _clean(raw.get("end_time"))
                if day and start:
                    slots.append(
                        TeamScheduleSlot(
                            Day=day,
                            StartTime=start,
                            EndTime=end,
                        )
                    )

        canonical = self.roster.ensure_team_name(team_name)
        self.roster.set_team_schedule(
            TeamSchedule(
                TeamName=canonical,
                TimeZone=_clean(schedule_raw.get("timezone")),
                CurrentFocus=_clean(schedule_raw.get("current_focus")),
                Slots=tuple(slots),
            )
        )
        return canonical

    def decoded_raid_plan(self, snapshot_key: str) -> RaidPlan:
        snapshot = self.client.shared_raid_plan(snapshot_key)
        body = _payload(snapshot, kind="raid_plan")
        plan_id = _clean(body.get("plan_id"))
        trial_id = _clean(body.get("trial_id"))
        name = _clean(body.get("name"))
        if not plan_id or not trial_id or not name:
            raise ValueError(
                "Shared Raid Plan must include plan_id, trial_id, and name."
            )

        raw_members = body.get("members")
        members: list[RaidPlanMember] = []
        if isinstance(raw_members, list):
            for raw in raw_members:
                if not isinstance(raw, dict):
                    continue
                seat_id = _clean(raw.get("seat_id"))
                if not seat_id:
                    continue
                members.append(
                    RaidPlanMember(
                        seat_id=seat_id,
                        gamertag=_clean(raw.get("gamertag")),
                        character_name=_clean(raw.get("character_name")) or None,
                        role=_clean(raw.get("role")) or None,
                        eso_class=_clean(raw.get("eso_class")) or None,
                    )
                )

        return RaidPlan(
            plan_id=plan_id,
            trial_id=trial_id,
            name=name,
            team_name=_clean(body.get("team_name")) or None,
            difficulty=_clean(body.get("difficulty")) or None,
            status=_clean(body.get("status")) or "planning",
            members=tuple(members),
        )

    def import_raid_plan(self, snapshot_key: str) -> RaidPlan:
        plan = self.decoded_raid_plan(snapshot_key)
        return self.raid_plans.save(plan)


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


def list_shared_teams_from_finch(
    *,
    database_path: Path | None = None,
    raid_plans_path: Path | None = None,
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> tuple[FinchSharedTeamPreview, ...]:
    db_path = Path(database_path or (get_data_dir() / "eso.db"))
    plans_path = Path(raid_plans_path or (get_data_dir() / "raid_plans.json"))
    database = EsoDatabase(db_path)
    try:
        service = FinchSharedImportService(
            client=_configured_client(settings_path=settings_path, timeout=timeout),
            roster=RosterService(database),
            raid_plans=RaidPlanRepository(plans_path),
        )
        return service.list_shared_teams()
    finally:
        database.close()


def list_shared_raid_plans_from_finch(
    *,
    database_path: Path | None = None,
    raid_plans_path: Path | None = None,
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> tuple[FinchSharedRaidPlanPreview, ...]:
    db_path = Path(database_path or (get_data_dir() / "eso.db"))
    plans_path = Path(raid_plans_path or (get_data_dir() / "raid_plans.json"))
    database = EsoDatabase(db_path)
    try:
        service = FinchSharedImportService(
            client=_configured_client(settings_path=settings_path, timeout=timeout),
            roster=RosterService(database),
            raid_plans=RaidPlanRepository(plans_path),
        )
        return service.list_shared_raid_plans()
    finally:
        database.close()


def import_shared_team_from_finch(
    *,
    snapshot_key: str,
    database_path: Path | None = None,
    raid_plans_path: Path | None = None,
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> str:
    db_path = Path(database_path or (get_data_dir() / "eso.db"))
    plans_path = Path(raid_plans_path or (get_data_dir() / "raid_plans.json"))
    database = EsoDatabase(db_path)
    try:
        service = FinchSharedImportService(
            client=_configured_client(settings_path=settings_path, timeout=timeout),
            roster=RosterService(database),
            raid_plans=RaidPlanRepository(plans_path),
        )
        return service.import_team_metadata(snapshot_key)
    finally:
        database.close()


def import_shared_raid_plan_from_finch(
    *,
    snapshot_key: str,
    database_path: Path | None = None,
    raid_plans_path: Path | None = None,
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> RaidPlan:
    db_path = Path(database_path or (get_data_dir() / "eso.db"))
    plans_path = Path(raid_plans_path or (get_data_dir() / "raid_plans.json"))
    database = EsoDatabase(db_path)
    try:
        service = FinchSharedImportService(
            client=_configured_client(settings_path=settings_path, timeout=timeout),
            roster=RosterService(database),
            raid_plans=RaidPlanRepository(plans_path),
        )
        return service.import_raid_plan(snapshot_key)
    finally:
        database.close()


__all__ = [
    "FinchSharedImportService",
    "FinchSharedRaidPlanPreview",
    "FinchSharedTeamPreview",
    "import_shared_raid_plan_from_finch",
    "import_shared_team_from_finch",
    "list_shared_raid_plans_from_finch",
    "list_shared_teams_from_finch",
]
