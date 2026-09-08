from datetime import datetime
from zoneinfo import ZoneInfo

from models.team_schedule import TeamSchedule
from services.team_schedule_ics import render_team_schedule_ics


def test_render_team_schedule_ics_uses_timezone_and_weekly_recurrence() -> None:
    schedule = TeamSchedule(
        TeamName="Swine & Punishment",
        RaidDays="Wed, Sun",
        RaidTime="8:00 PM",
        TimeZone="America/New_York",
    )
    now = datetime(2026, 9, 8, 1, 0, tzinfo=ZoneInfo("America/New_York"))

    text = render_team_schedule_ics(schedule, now=now)

    assert "SUMMARY:Swine & Punishment Raid" in text
    assert "DTSTART;TZID=America/New_York:20260909T200000" in text
    assert "RRULE:FREQ=WEEKLY;BYDAY=WE,SU" in text


def test_render_team_schedule_ics_keeps_local_wall_clock_across_timezone() -> None:
    schedule = TeamSchedule(
        TeamName="Late Crew",
        RaidDays="Fri",
        RaidTime="19:30",
        TimeZone="Europe/London",
    )
    now = datetime(2026, 9, 8, 12, 0, tzinfo=ZoneInfo("UTC"))

    text = render_team_schedule_ics(schedule, now=now)

    assert "DTSTART;TZID=Europe/London:20260911T193000" in text
    assert "DTEND;TZID=Europe/London:20260911T223000" in text


def test_render_team_schedule_ics_rejects_missing_timezone() -> None:
    schedule = TeamSchedule(
        TeamName="No Clock Math",
        RaidDays="Tue",
        RaidTime="8:00 PM",
        TimeZone="",
    )

    try:
        render_team_schedule_ics(schedule)
    except ValueError as exc:
        assert "time zone" in str(exc).lower()
    else:
        raise AssertionError("Expected missing timezone to be rejected")
