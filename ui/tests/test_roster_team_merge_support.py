from __future__ import annotations

from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from models.roster_model import RosterMember
from models.team_schedule import TeamSchedule, TeamScheduleSlot
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_service import RosterService
from ui.roster_team_merge_support import merge_teams, preview_team_merge


def _services(tmp_path: Path) -> tuple[RosterService, BuildService]:
    roster = RosterService(EsoDatabase(tmp_path / "eso.db"))
    builds = BuildService(tmp_path / "builds.json")
    builds.load()
    return roster, builds


def test_team_merge_moves_memberships_and_build_assignments_without_deleting_identity(tmp_path: Path) -> None:
    roster, builds = _services(tmp_path)
    source = roster.ensure_team_name("Swine and Punishment")
    destination = roster.ensure_team_name("Swine & Punishment")

    roster.create_member(
        RosterMember(
            PlayerName="Jarakeen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
            Team=source,
        )
    )
    roster.create_member(
        RosterMember(
            PlayerName="Rylo",
            CharacterName="Rylonia",
            EsoClass="Necromancer",
            PrimaryRole="Damage Dealer",
            Team=f"{source}, {destination}",
        )
    )

    roster.set_team_schedule(
        TeamSchedule(
            TeamName=source,
            TimeZone="America/Chicago",
            Slots=(TeamScheduleSlot(Day="Mon", StartTime="8:00 PM", EndTime="10:00 PM"),),
            CurrentFocus="Imported U50 plan",
        )
    )
    roster.set_team_schedule(
        TeamSchedule(
            TeamName=destination,
            TimeZone="America/New_York",
            Slots=(TeamScheduleSlot(Day="Wed", StartTime="9:00 PM", EndTime="11:00 PM"),),
            CurrentFocus="Existing team focus",
        )
    )

    builds.save(
        BuildRoster(
            Members=[
                PlayerBuild(
                    Name="Magrat",
                    Gamertag="Jarakeen",
                    BuildName="HH Healer",
                    EsoClass="Warden",
                    Role="Healer",
                    Food="Clockwork Citrus Filet",
                ),
                PlayerBuild(
                    Name="Rylonia",
                    Gamertag="Rylo",
                    BuildName="Corpsebuster DD",
                    EsoClass="Necromancer",
                    Role="Damage Dealer",
                    Food="Lava Foot Soup-and-Saltrice",
                ),
            ]
        )
    )
    catalog = builds.canonical.catalog_service
    records = {row["name"]: row for row in catalog.load()["builds"]}
    catalog.assign_build_to_team(
        build_id=records["HH Healer"]["build_id"],
        team_name=source,
        raid_role="Healer",
        slot_name="Pillager",
        notes="Imported workbook assignment",
    )
    catalog.assign_build_to_team(
        build_id=records["Corpsebuster DD"]["build_id"],
        team_name=source,
        raid_role="Damage Dealer",
        slot_name="Left Stack",
        notes="Source note",
    )
    catalog.assign_build_to_team(
        build_id=records["Corpsebuster DD"]["build_id"],
        team_name=destination,
        raid_role="Damage Dealer",
        slot_name="Right Stack",
        notes="Destination note",
    )

    preview = preview_team_merge(roster, builds, source, destination)
    assert preview.source_memberships == 2
    assert preview.duplicate_memberships == 1
    assert preview.source_build_assignments == 2
    assert preview.duplicate_build_assignments == 1
    assert any("raid schedule differs" in line.lower() for line in preview.conflicts)
    assert any("slot/assignment" in line.lower() for line in preview.conflicts)

    before = catalog.load()
    result = merge_teams(roster, builds, source, destination)
    after = catalog.load()

    assert result.moved_memberships == 1
    assert result.collapsed_memberships == 1
    assert result.moved_build_assignments == 1
    assert result.collapsed_build_assignments == 1

    assert source not in roster.list_team_names()
    assert destination in roster.list_team_names()
    members = {member.PlayerName: member for member in roster.list_members()}
    assert destination in members["Jarakeen"].Team
    assert destination in members["Rylo"].Team
    assert source not in members["Jarakeen"].Team
    assert source not in members["Rylo"].Team

    assert len(after["players"]) == len(before["players"])
    assert len(after["characters"]) == len(before["characters"])
    assert len(after["builds"]) == len(before["builds"])
    assert catalog.assignments_for_team(source) == []
    destination_assignments = catalog.assignments_for_team(destination)
    assert len(destination_assignments) == 2

    duplicate = next(
        row for row in destination_assignments if row["build_id"] == records["Corpsebuster DD"]["build_id"]
    )
    assert duplicate["slot_name"] == "Right Stack"
    assert "Destination note" in duplicate["notes"]
    assert "Source note" in duplicate["notes"]

    schedule = roster.get_team_schedule(destination)
    assert schedule is not None
    assert schedule.CurrentFocus == "Existing team focus"
    assert schedule.TimeZone == "America/New_York"
    assert tuple((slot.Day, slot.StartTime, slot.EndTime) for slot in schedule.effective_slots) == (
        ("Wed", "9:00 PM", "11:00 PM"),
    )


def test_team_merge_installs_after_multi_time_team_schedule_surface() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")
    assert source.index("install_team_schedule_multi_time_support()") < source.index(
        "install_roster_team_merge_support()"
    )
    merge_source = Path("ui/roster_team_merge_support.py").read_text(encoding="utf-8")
    assert 'QPushButton("Merge Teams…")' in merge_source
    assert "People, characters, and saved builds are never deleted" in merge_source
