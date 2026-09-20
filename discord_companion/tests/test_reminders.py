from datetime import datetime
from zoneinfo import ZoneInfo

from discord_companion.reminders import next_occurrence


def test_next_occurrence_uses_team_timezone() -> None:
    now = datetime(2026, 9, 20, 13, 0, tzinfo=ZoneInfo("America/Detroit"))
    result = next_occurrence(
        day="Monday",
        start_time="9 PM",
        timezone="EST",
        now=now,
    )
    assert result.weekday() == 0
    assert result.hour == 21
    assert result.tzinfo is not None


def test_next_occurrence_rolls_same_day_past_time_to_next_week() -> None:
    now = datetime(2026, 9, 21, 22, 0, tzinfo=ZoneInfo("America/New_York"))
    result = next_occurrence(
        day="Monday",
        start_time="9 PM",
        timezone="America/New_York",
        now=now,
    )
    assert (result.date() - now.date()).days == 7
