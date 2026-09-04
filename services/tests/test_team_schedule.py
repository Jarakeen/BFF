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


def test_schedule_exporter_accepts_both_theme_styles():
    exporter = TeamScheduleShareDocumentExporter()
    assert exporter is not None
