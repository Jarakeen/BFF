from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.roster_service import RosterService


def test_assignment_fields_persist_across_service_instances(tmp_path):
    db_path = tmp_path / "eso.db"
    service = RosterService(EsoDatabase(db_path))
    member_id = service.create_member(
        RosterMember(
            PlayerName="TestPlayer",
            CharacterName="TestCharacter",
            EsoClass="Warden",
            PrimaryRole="Healer",
            Status="Active",
            Team="Test Team",
        )
    )

    service.set_member_assignment_field(member_id, "primary_assignment", "Raid Healing / Support")
    service.set_member_assignment_field(member_id, "secondary_assignment", "Kite")
    service.set_member_assignment_field(member_id, "gear_needed", "Spell Power Cure")
    service.set_member_assignment_field(member_id, "notes", "Backup kite")

    reloaded = RosterService(EsoDatabase(db_path)).get_member_assignment(member_id)

    assert reloaded == {
        "primary_assignment": "Raid Healing / Support",
        "secondary_assignment": "Kite",
        "gear_needed": "Spell Power Cure",
        "notes": "Backup kite",
    }


def test_deleting_member_removes_assignment_row(tmp_path):
    db_path = tmp_path / "eso.db"
    service = RosterService(EsoDatabase(db_path))
    member_id = service.create_member(RosterMember(PlayerName="TestPlayer"))
    service.set_member_assignment_field(member_id, "primary_assignment", "Portal")

    service.delete_member(member_id)

    assert service.get_member_assignment(member_id) == {
        "primary_assignment": "",
        "secondary_assignment": "",
        "gear_needed": "",
        "notes": "",
    }
