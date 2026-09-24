from __future__ import annotations

"""Read and explicitly import versioned Finch shared operational snapshots.

Shared Team import creates/updates only Team metadata and recurring schedule. It
never creates Personnel rows from remote member names.

Shared Raid Plan import writes only a RaidPlan snapshot keyed by stable plan_id.
It never creates Personnel, Characters, Saved Builds, or local build identity.
"""

from dataclasses import dataclass, replace
from pathlib import Path

from engine.config import get_data_dir, get_settings_path, get_user_database_path
from models.raid_plan import RaidPlan, RaidPlanMember
from models.team_schedule import TeamSchedule, TeamScheduleSlot
from services.eso_database import EsoDatabase
from services.finch_api_client import FinchApiClient, FinchSharedSnapshot
from services.finch_shared_provenance_service import FinchSharedProvenanceService
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
    allowed_versions = {1, 2, 3} if kind == "team" else {1, 2, 3, 4, 5, 6, 7}
    if snapshot.schema_version not in allowed_versions:
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
    provenance: str
    local_key: str


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
    provenance: str
    local_key: str


class FinchSharedImportService:
    def __init__(
        self,
        *,
        client: FinchApiClient,
        roster: RosterService,
        raid_plans: RaidPlanRepository,
        provenance: FinchSharedProvenanceService | None = None,
    ) -> None:
        self.client = client
        self.roster = roster
        self.raid_plans = raid_plans
        self.provenance = provenance or FinchSharedProvenanceService(
            raid_plans.path.parent / "finch_shared_provenance.json"
        )

    def team_preview(
        self,
        snapshot: FinchSharedSnapshot,
    ) -> FinchSharedTeamPreview:
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
            provenance=self.provenance.relation_for(snapshot),
            local_key=(
                self.provenance.latest_copy_for(
                    kind=snapshot.kind,
                    snapshot_key=snapshot.snapshot_key,
                ).local_key
                if self.provenance.latest_copy_for(
                    kind=snapshot.kind,
                    snapshot_key=snapshot.snapshot_key,
                ) is not None
                else ""
            ),
        )

    def raid_plan_preview(
        self,
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
            provenance=self.provenance.relation_for(snapshot),
            local_key=(
                self.provenance.latest_copy_for(
                    kind=snapshot.kind,
                    snapshot_key=snapshot.snapshot_key,
                ).local_key
                if self.provenance.latest_copy_for(
                    kind=snapshot.kind,
                    snapshot_key=snapshot.snapshot_key,
                ) is not None
                else ""
            ),
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

        existing_names = {name.casefold() for name in self.roster.list_team_names()}
        local_team_name = f"{team_name} (Shared Copy)"
        suffix = 2
        while local_team_name.casefold() in existing_names:
            local_team_name = f"{team_name} (Shared Copy) {suffix}"
            suffix += 1

        canonical = self.roster.ensure_team_name(local_team_name)
        self.roster.set_team_schedule(
            TeamSchedule(
                TeamName=canonical,
                TimeZone=_clean(schedule_raw.get("timezone")),
                CurrentFocus=_clean(schedule_raw.get("current_focus")),
                Slots=tuple(slots),
            )
        )
        self.provenance.record_copy(snapshot=snapshot, local_key=canonical)
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
                build_summary = raw.get("build_summary")
                if not isinstance(build_summary, dict):
                    build_summary = {}
                planned_gear_sets = build_summary.get("planned_gear_sets")
                members.append(
                    RaidPlanMember(
                        seat_id=seat_id,
                        gamertag=_clean(raw.get("gamertag")),
                        character_name=_clean(raw.get("character_name")) or None,
                        role=_clean(raw.get("role")) or None,
                        eso_class=_clean(raw.get("eso_class")) or None,
                        primary_assignment=_clean(raw.get("primary_assignment")) or None,
                        secondary_assignment=_clean(raw.get("secondary_assignment")) or None,
                        utility_assignments=tuple(
                            _clean(value)
                            for value in (
                                raw.get("utility_assignments")
                                if isinstance(raw.get("utility_assignments"), list)
                                else []
                            )
                            if _clean(value)
                        ),
                        selected_build_name=_clean(build_summary.get("name")) or None,
                        build_source_kind=_clean(build_summary.get("source_kind")) or None,
                        build_source_name=_clean(build_summary.get("source_name")) or None,
                        planned_gear_sets=tuple(
                            _clean(value)
                            for value in (
                                planned_gear_sets
                                if isinstance(planned_gear_sets, list)
                                else []
                            )
                            if _clean(value)
                        ),
                        planned_skills=tuple(
                            _clean(value)
                            for value in (
                                build_summary.get("front_skills")
                                if isinstance(build_summary.get("front_skills"), list)
                                else []
                            )
                            if _clean(value)
                        ),
                        planned_mundus=_clean(build_summary.get("planned_mundus")) or None,
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

        base_id = f"{plan.plan_id}-shared-copy"
        local_plan_id = base_id
        suffix = 2
        while self.raid_plans.get(local_plan_id) is not None:
            local_plan_id = f"{base_id}-{suffix}"
            suffix += 1

        existing_names = {row.name.casefold() for row in self.raid_plans.list_plans()}
        base_name = f"{plan.name} (Shared Copy)"
        local_name = base_name
        suffix = 2
        while local_name.casefold() in existing_names:
            local_name = f"{base_name} {suffix}"
            suffix += 1

        saved = self.raid_plans.save(
            replace(plan, plan_id=local_plan_id, name=local_name)
        )
        snapshot = self.client.shared_raid_plan(snapshot_key)
        self.provenance.record_copy(snapshot=snapshot, local_key=saved.plan_id)
        return saved


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
    settings_path: Path = get_settings_path(),
    timeout: float = 10.0,
) -> tuple[FinchSharedTeamPreview, ...]:
    db_path = Path(database_path or get_user_database_path())
    plans_path = Path(raid_plans_path or get_user_database_path())
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
    settings_path: Path = get_settings_path(),
    timeout: float = 10.0,
) -> tuple[FinchSharedRaidPlanPreview, ...]:
    db_path = Path(database_path or get_user_database_path())
    plans_path = Path(raid_plans_path or get_user_database_path())
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
    settings_path: Path = get_settings_path(),
    timeout: float = 10.0,
) -> str:
    db_path = Path(database_path or get_user_database_path())
    plans_path = Path(raid_plans_path or get_user_database_path())
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
    settings_path: Path = get_settings_path(),
    timeout: float = 10.0,
) -> RaidPlan:
    db_path = Path(database_path or get_user_database_path())
    plans_path = Path(raid_plans_path or get_user_database_path())
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
