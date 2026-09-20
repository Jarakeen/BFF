from models.roster_model import RosterMember
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_service import RosterService
from services.team_deletion_service import delete_team_everywhere


def test_delete_team_everywhere_removes_team_memberships_and_build_assignments(tmp_path):
    db_path = tmp_path / "eso.db"
    roster = RosterService(EsoDatabase(db_path))
    team = roster.ensure_team_name("Performance Mode")

    member_id = roster.create_member(
        RosterMember(
            PlayerName="Jarakeen",
            Team=team,
        )
    )

    build_service = BuildService(tmp_path / "builds.json")
    catalog_service = build_service.canonical.catalog_service
    catalog = catalog_service.new_catalog()
    catalog["players"] = [
        {"player_id": "player-1", "gamertag": "Jarakeen", "status": "Active"}
    ]
    catalog["characters"] = [
        {
            "character_id": "char-1",
            "player_id": "player-1",
            "name": "Magrat",
            "gamertag": "Jarakeen",
        }
    ]
    catalog["builds"] = [
        {
            "build_id": "build-1",
            "character_id": "char-1",
            "name": "RoJo",
            "legacy": {},
            "payload": {},
        }
    ]
    catalog["team_assignments"] = [
        {
            "assignment_id": "assignment-1",
            "team_name": "Performance Mode",
            "build_id": "build-1",
            "raid_role": "Healer",
            "slot_name": "Healer 1",
            "status": "Active",
            "notes": "",
        }
    ]
    catalog_service.save(catalog)

    result = delete_team_everywhere(
        roster,
        build_service,
        "Performance Mode",
    )

    assert result.team_name == "Performance Mode"
    assert result.removed_memberships == 1
    assert result.removed_build_assignments == 1
    assert "Performance Mode" not in roster.list_team_names()

    member = roster.get_member(member_id)
    assert member is not None
    assert member.PlayerName == "Jarakeen"
    assert member.Team == ""

    after = catalog_service.load()
    assert after["players"]
    assert after["characters"]
    assert after["builds"]
    assert after["team_assignments"] == []


def test_delete_team_everywhere_leaves_other_team_assignments_alone(tmp_path):
    roster = RosterService(EsoDatabase(tmp_path / "eso.db"))
    roster.ensure_team_name("Performance Mode")
    roster.ensure_team_name("Disappointing Feral")

    build_service = BuildService(tmp_path / "builds.json")
    catalog_service = build_service.canonical.catalog_service
    catalog = catalog_service.new_catalog()
    catalog["builds"] = [
        {"build_id": "build-1", "character_id": "char-1", "name": "A", "legacy": {}, "payload": {}},
        {"build_id": "build-2", "character_id": "char-2", "name": "B", "legacy": {}, "payload": {}},
    ]
    catalog["team_assignments"] = [
        {
            "assignment_id": "a1",
            "team_name": "Performance Mode",
            "build_id": "build-1",
            "raid_role": "",
            "slot_name": "",
            "status": "Active",
            "notes": "",
        },
        {
            "assignment_id": "a2",
            "team_name": "Disappointing Feral",
            "build_id": "build-2",
            "raid_role": "",
            "slot_name": "",
            "status": "Active",
            "notes": "",
        },
    ]
    catalog_service.save(catalog)

    delete_team_everywhere(roster, build_service, "Performance Mode")

    remaining = catalog_service.assignments_for_team("Disappointing Feral")
    assert len(remaining) == 1
    assert remaining[0]["build_id"] == "build-2"
