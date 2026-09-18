from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.roster_placeholder_identity import is_personnel_placeholder
from services.roster_service import RosterService


def test_roster_service_rejects_placeholder_player_creation(tmp_path) -> None:
    service = RosterService(EsoDatabase(tmp_path / "eso.db"))

    for name in ("Tank 1", "Healer 2", "DD 8", "Recruitment Needed"):
        assert is_personnel_placeholder(name)
        try:
            service.create_member(RosterMember(PlayerName=name))
        except ValueError as exc:
            assert "planning placeholder" in str(exc)
        else:
            raise AssertionError(f"{name} was incorrectly accepted as Personnel")


def test_roster_service_removes_existing_placeholder_rows_on_init(tmp_path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    service = RosterService(database)
    real_id = service.create_member(RosterMember(PlayerName="RealPlayer"))

    database.execute(
        "INSERT INTO roster_member (player_name, status) VALUES (?, 'Active')",
        ("DD 1",),
    )
    database.execute(
        "INSERT INTO roster_member (player_name, status) VALUES (?, 'Active')",
        ("Recruitment Needed",),
    )
    database.commit()

    reloaded = RosterService(database)
    names = [member.PlayerName for member in reloaded.list_members()]

    assert names == ["RealPlayer"]
    assert reloaded.get_member(real_id) is not None
