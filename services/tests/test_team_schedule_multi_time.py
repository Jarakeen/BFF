from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from models.team_schedule import TeamSchedule, TeamScheduleSlot
from services.eso_database import EsoDatabase
from services.roster_service import RosterService
from services.team_schedule_ics import render_team_schedule_ics


def _swine_schedule() -> TeamSchedule:
    return TeamSchedule(
        TeamName="Swine & Punishment",
        TimeZone="America/New_York",
        Slots=(
            TeamScheduleSlot(Day="Tue", StartTime="8:00 PM", EndTime="10:00 PM"),
            TeamScheduleSlot(Day="Fri", StartTime="9:00 PM", EndTime="11:00 PM"),
        ),
    )


def test_team_schedule_round_trips_distinct_per_day_times(tmp_path):
    service = RosterService(EsoDatabase(tmp_path / "eso.db"))
    service.set_team_schedule(_swine_schedule())

    loaded = service.get_team_schedule("Swine & Punishment")

    assert loaded is not None
    assert [(slot.Day, slot.StartTime, slot.EndTime) for slot in loaded.effective_slots] == [
        ("Tue", "8:00 PM", "10:00 PM"),
        ("Fri", "9:00 PM", "11:00 PM"),
    ]
    assert loaded.TimeZone == "America/New_York"


def test_display_text_keeps_each_day_next_to_its_own_time():
    text = _swine_schedule().display_text

    assert "Tue 8:00 PM–10:00 PM" in text
    assert "Fri 9:00 PM–11:00 PM" in text
    assert "America/New_York" in text


def test_ics_exports_separate_weekly_events_for_distinct_times():
    rendered = render_team_schedule_ics(
        _swine_schedule(),
        now=datetime(2026, 9, 7, 12, 0, tzinfo=ZoneInfo("America/New_York")),
    )

    assert rendered.count("BEGIN:VEVENT") == 2
    assert "RRULE:FREQ=WEEKLY;BYDAY=TU" in rendered
    assert "RRULE:FREQ=WEEKLY;BYDAY=FR" in rendered
    assert "DTSTART;TZID=America/New_York:20260908T200000" in rendered
    assert "DTEND;TZID=America/New_York:20260908T220000" in rendered
    assert "DTSTART;TZID=America/New_York:20260911T210000" in rendered
    assert "DTEND;TZID=America/New_York:20260911T230000" in rendered


def test_legacy_same_time_schedule_still_expands_to_slots():
    schedule = TeamSchedule(
        TeamName="Legacy Team",
        RaidDays="Tue, Fri",
        RaidTime="8:00 PM",
        TimeZone="America/New_York",
    )

    assert [(slot.Day, slot.StartTime) for slot in schedule.effective_slots] == [
        ("Tue", "8:00 PM"),
        ("Fri", "8:00 PM"),
    ]
