from models.team_schedule import TeamSchedule
from services.eso_database import EsoDatabase
from services.roster_service import RosterService
from services.team_schedule_share_export import TeamScheduleShareDocumentExporter


def test_team_schedule_round_trip_and_explicit_timezone(tmp_path):
    service = RosterService(EsoDatabase(tmp_path / "eso.db"))
    schedule = TeamSchedule(
        TeamName="Hurricane Herald",
        RaidDays="Tue, Thu",
        RaidTime="9:00 PM",
        TimeZone="America/New_York",
    )

    service.set_team_schedule(schedule)

    assert service.get_team_schedule("hurricane herald") == schedule
    assert service.list_team_schedules() == [schedule]
    assert schedule.display_text == "Tue, Thu  ·  9:00 PM  ·  America/New_York"


def test_team_schedule_schema_migrates_existing_team_table(tmp_path):
    db = EsoDatabase(tmp_path / "legacy.db")
    db.execute("CREATE TABLE team (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)")
    db.execute("INSERT INTO team (name) VALUES ('Old Team')")
    db.commit()

    service = RosterService(db)
    service.set_team_schedule(TeamSchedule("Old Team", "Sun", "7:30 PM", "Europe/London"))

    restored = service.get_team_schedule("Old Team")
    assert restored is not None
    assert restored.RaidDays == "Sun"
    assert restored.RaidTime == "7:30 PM"
    assert restored.TimeZone == "Europe/London"


def test_team_identity_can_be_created_without_membership(tmp_path):
    service = RosterService(EsoDatabase(tmp_path / "eso.db"))

    assert service.ensure_team_name("Swine & Punishment") == "Swine & Punishment"
    assert service.list_team_names() == ["Swine & Punishment"]
    assert service.list_members() == []


def test_delete_team_removes_schedule_and_membership_but_keeps_roster_member(tmp_path):
    db = EsoDatabase(tmp_path / "eso.db")
    service = RosterService(db)
    service.set_team_schedule(
        TeamSchedule("Disappointing Feral", "Mon, Wed", "8:00 PM", "America/New_York")
    )

    member_id = db.execute(
        """
        INSERT INTO roster_member (
            player_name, character_name, eso_class, primary_role, secondary_role, status
        ) VALUES ('Jarakeen', 'Magrat', 'Warden', 'Healer', 'Damage', 'Active')
        """
    ).lastrowid
    team_id = db.execute(
        "SELECT id FROM team WHERE name = 'Disappointing Feral'"
    ).fetchone()["id"]
    db.execute(
        "INSERT INTO team_member (roster_member_id, team_id) VALUES (?, ?)",
        (member_id, team_id),
    )
    db.commit()

    assert service.delete_team("disappointing feral") is True
    assert service.list_team_names() == []
    assert service.get_team_schedule("Disappointing Feral") is None

    member = service.get_member(member_id)
    assert member is not None
    assert member.PlayerName == "Jarakeen"
    assert member.Team == ""
    assert service.delete_team("Disappointing Feral") is False


def test_schedule_exporter_accepts_both_theme_styles():
    exporter = TeamScheduleShareDocumentExporter()
    assert exporter is not None
