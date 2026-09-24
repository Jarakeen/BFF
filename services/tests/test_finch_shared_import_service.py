from __future__ import annotations

from models.raid_plan import RaidPlan
from services.eso_database import EsoDatabase
from services.finch_api_client import FinchSharedSnapshot
from services.finch_shared_import_service import FinchSharedImportService
from services.raid_plan_repository import RaidPlanRepository
from services.roster_service import RosterService


class FakeClient:
    def __init__(self) -> None:
        self.team = FinchSharedSnapshot(
            kind="team",
            snapshot_key="performance mode",
            schema_version=1,
            payload={
                "team_name": "Performance Mode",
                "schedule": {
                    "timezone": "America/New_York",
                    "current_focus": "Swashbuckler Supreme",
                    "slots": [
                        {"day": "Mon", "start_time": "9:00 PM", "end_time": "11:00 PM"},
                        {"day": "Wed", "start_time": "9:00 PM", "end_time": "11:00 PM"},
                    ],
                },
                "members": [
                    {
                        "player_name": "Rylo",
                        "character_name": "Rylos Arcanist",
                        "eso_class": "Arcanist",
                        "primary_role": "Damage Dealer",
                        "secondary_role": "",
                        "status": "Active",
                    }
                ],
            },
            published_by="Jarakeen",
            updated_at="2026-09-20T00:00:00+00:00",
        )
        self.plan = FinchSharedSnapshot(
            kind="raid_plan",
            snapshot_key="rg-pm",
            schema_version=3,
            payload={
                "plan_id": "rg-pm",
                "name": "Performance Mode RG",
                "trial_id": "rockgrove",
                "team_name": "Performance Mode",
                "difficulty": "Veteran",
                "status": "planning",
                "members": [
                    {
                        "seat_id": "dd-1",
                        "gamertag": "Rylo",
                        "character_name": "Rylos Arcanist",
                        "role": "Damage Dealer",
                        "eso_class": "Arcanist",
                        "primary_assignment": "Major Courage",
                        "secondary_assignment": "Minor Toughness",
                        "utility_assignments": ["Portal", "Interrupt"],
                        "build_summary": {
                            "name": "Corpsebuster Support",
                            "source_kind": "comp",
                            "source_name": "Performance Mode RG",
                            "planned_gear_sets": ["Corpsebuster", "Null Arca"],
                            "planned_mundus": "The Thief",
                        },
                    }
                ],
            },
            published_by="Jarakeen",
            updated_at="2026-09-20T00:00:00+00:00",
        )

    def shared_teams(self):
        return (self.team,)

    def shared_raid_plans(self):
        return (self.plan,)

    def shared_team(self, snapshot_key):
        assert snapshot_key == "performance mode"
        return self.team

    def shared_raid_plan(self, snapshot_key):
        assert snapshot_key == "rg-pm"
        return self.plan


def _service(tmp_path):
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    repository = RaidPlanRepository(tmp_path / "raid_plans.json")
    return database, roster, repository, FinchSharedImportService(
        client=FakeClient(),
        roster=roster,
        raid_plans=repository,
    )


def test_shared_team_preview_does_not_mutate_local_state(tmp_path) -> None:
    _db, roster, _repo, service = _service(tmp_path)

    previews = service.list_shared_teams()

    assert previews[0].team_name == "Performance Mode"
    assert previews[0].member_count == 1
    assert roster.list_team_names() == []
    assert roster.list_members() == []


def test_explicit_team_import_creates_collision_safe_local_copy_only(tmp_path) -> None:
    _db, roster, _repo, service = _service(tmp_path)
    roster.ensure_team_name("Performance Mode")

    imported = service.import_team_metadata("performance mode")

    assert imported == "Performance Mode (Shared Copy)"
    assert roster.list_team_names() == ["Performance Mode", "Performance Mode (Shared Copy)"]
    assert roster.list_members() == []
    schedule = roster.get_team_schedule("Performance Mode (Shared Copy)")
    assert schedule is not None
    assert schedule.TimeZone == "America/New_York"
    assert schedule.CurrentFocus == "Swashbuckler Supreme"
    assert [slot.Day for slot in schedule.Slots] == ["Mon", "Wed"]


def test_shared_raid_plan_decodes_without_local_identity_or_build_state(tmp_path) -> None:
    _db, roster, repository, service = _service(tmp_path)

    plan = service.decoded_raid_plan("rg-pm")

    assert isinstance(plan, RaidPlan)
    assert plan.plan_id == "rg-pm"
    assert plan.team_name == "Performance Mode"
    assert plan.members[0].gamertag == "Rylo"
    assert plan.members[0].roster_member_id is None
    assert plan.members[0].player_id is None
    assert plan.members[0].character_id is None
    assert plan.members[0].selected_build_id is None
    assert plan.members[0].primary_assignment == "Major Courage"
    assert plan.members[0].secondary_assignment == "Minor Toughness"
    assert plan.members[0].utility_assignments == ("Portal", "Interrupt")
    assert plan.members[0].selected_build_id is None
    assert plan.members[0].selected_build_name == "Corpsebuster Support"
    assert plan.members[0].build_source_kind == "comp"
    assert plan.members[0].build_source_name == "Performance Mode RG"
    assert plan.members[0].planned_gear_sets == ("Corpsebuster", "Null Arca")
    assert plan.members[0].planned_mundus == "The Thief"
    assert repository.list_plans() == ()
    assert roster.list_members() == []


def test_explicit_raid_plan_import_saves_collision_safe_local_copy_only(tmp_path) -> None:
    _db, roster, repository, service = _service(tmp_path)
    repository.save(service.decoded_raid_plan("rg-pm"))

    imported = service.import_raid_plan("rg-pm")

    assert imported.plan_id == "rg-pm-shared-copy"
    assert imported.name == "Performance Mode RG (Shared Copy)"
    assert repository.get("rg-pm") is not None
    assert repository.get("rg-pm-shared-copy") == imported
    assert roster.list_members() == []
    assert roster.list_team_names() == []


def test_repeated_shared_imports_increment_local_copy_identity(tmp_path) -> None:
    _db, roster, repository, service = _service(tmp_path)

    first_team = service.import_team_metadata("performance mode")
    second_team = service.import_team_metadata("performance mode")
    first_plan = service.import_raid_plan("rg-pm")
    second_plan = service.import_raid_plan("rg-pm")

    assert first_team == "Performance Mode (Shared Copy)"
    assert second_team == "Performance Mode (Shared Copy) 2"
    assert first_plan.plan_id == "rg-pm-shared-copy"
    assert second_plan.plan_id == "rg-pm-shared-copy-2"
    assert repository.get("rg-pm-shared-copy") == first_plan
    assert repository.get("rg-pm-shared-copy-2") == second_plan


def test_current_team_schema_v3_is_readable(tmp_path) -> None:
    _db, _roster, _repository, service = _service(tmp_path)
    service.client.team = FinchSharedSnapshot(
        kind="team",
        snapshot_key="performance mode",
        schema_version=3,
        payload={
            "team_name": "Performance Mode",
            "schedule": {"timezone": "EST", "slots": []},
            "members": [],
            "group_type": "trial",
            "group_capacity": 12,
        },
        published_by="BFF",
        updated_at="2026-09-23T00:00:00+00:00",
    )

    preview = service.team_preview(service.client.team)

    assert preview.team_name == "Performance Mode"


def test_current_raid_plan_schema_v7_is_readable(tmp_path) -> None:
    _db, _roster, _repository, service = _service(tmp_path)
    service.client.plan = FinchSharedSnapshot(
        kind="raid_plan",
        snapshot_key="current-plan",
        schema_version=7,
        payload={
            "plan_id": "current-plan",
            "name": "Current Shared Plan",
            "trial_id": "sunspire",
            "team_name": "Performance Mode",
            "difficulty": "Veteran",
            "status": "planning",
            "group_type": "trial",
            "group_capacity": 12,
            "raid_maps": {},
            "raid_map_previews": [],
            "members": [],
        },
        published_by="BFF",
        updated_at="2026-09-23T00:00:00+00:00",
    )

    plan = service.decoded_raid_plan("rg-pm")

    assert plan.plan_id == "current-plan"
    assert plan.team_name == "Performance Mode"


def test_legacy_v1_shared_raid_plan_remains_readable(tmp_path) -> None:
    _db, _roster, _repository, service = _service(tmp_path)
    service.client.plan = FinchSharedSnapshot(
        kind="raid_plan",
        snapshot_key="legacy-plan",
        schema_version=1,
        payload={
            "plan_id": "legacy-plan",
            "name": "Legacy Shared Plan",
            "trial_id": "sunspire",
            "members": [
                {
                    "seat_id": "healer-1",
                    "gamertag": "LegacyHealer",
                    "role": "Healer",
                    "eso_class": "Warden",
                }
            ],
        },
        published_by="BFF",
        updated_at="2026-09-20T00:00:00+00:00",
    )

    plan = service.decoded_raid_plan("rg-pm")

    assert plan.plan_id == "legacy-plan"
    assert plan.members[0].primary_assignment is None
    assert plan.members[0].utility_assignments == ()


def test_v2_shared_raid_plan_without_build_summary_remains_readable(tmp_path) -> None:
    _db, _roster, _repository, service = _service(tmp_path)
    service.client.plan = FinchSharedSnapshot(
        kind="raid_plan",
        snapshot_key="v2-plan",
        schema_version=2,
        payload={
            "plan_id": "v2-plan",
            "name": "Assignment Only Plan",
            "trial_id": "dreadsail-reef",
            "members": [
                {
                    "seat_id": "tank-1",
                    "gamertag": "Tank",
                    "role": "Tank",
                    "eso_class": "Dragonknight",
                    "primary_assignment": "Main Tank",
                    "utility_assignments": ["Interrupt"],
                }
            ],
        },
        published_by="BFF",
        updated_at="2026-09-20T00:00:00+00:00",
    )

    plan = service.decoded_raid_plan("rg-pm")

    assert plan.plan_id == "v2-plan"
    assert plan.members[0].primary_assignment == "Main Tank"
    assert plan.members[0].selected_build_name is None
    assert plan.members[0].planned_gear_sets == ()
