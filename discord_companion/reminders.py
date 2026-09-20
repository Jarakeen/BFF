from __future__ import annotations

"""Recurring raid reminder calculation from FoundryDock Team schedules."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from discord_companion.config import DiscordCompanionConfig
from services.roster_service import RosterService


_WEEKDAY = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

_TZ_ALIASES = {
    "est": "America/New_York",
    "edt": "America/New_York",
    "et": "America/New_York",
    "eastern": "America/New_York",
    "eastern time": "America/New_York",
    "cst": "America/Chicago",
    "cdt": "America/Chicago",
    "ct": "America/Chicago",
    "central": "America/Chicago",
    "mst": "America/Denver",
    "mdt": "America/Denver",
    "mt": "America/Denver",
    "mountain": "America/Denver",
    "pst": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",
    "pt": "America/Los_Angeles",
    "pacific": "America/Los_Angeles",
}


def _timezone(value: str) -> ZoneInfo:
    raw = str(value or "").strip()
    canonical = _TZ_ALIASES.get(raw.casefold(), raw or "America/New_York")
    try:
        return ZoneInfo(canonical)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/New_York")


def _clock(value: str) -> time:
    raw = str(value or "").strip().casefold().replace(".", "")
    raw = re.sub(r"\s+", " ", raw)
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)?", raw)
    if not match:
        raise ValueError(f"Unsupported raid start time: {value!r}")
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)
    if minute > 59:
        raise ValueError(f"Unsupported raid start time: {value!r}")
    if meridiem:
        if not 1 <= hour <= 12:
            raise ValueError(f"Unsupported raid start time: {value!r}")
        hour %= 12
        if meridiem == "pm":
            hour += 12
    elif hour > 23:
        raise ValueError(f"Unsupported raid start time: {value!r}")
    return time(hour=hour, minute=minute)


def next_occurrence(*, day: str, start_time: str, timezone: str, now: datetime) -> datetime:
    day_index = _WEEKDAY.get(str(day or "").strip().casefold())
    if day_index is None:
        raise ValueError(f"Unsupported raid day: {day!r}")
    tz = _timezone(timezone)
    local_now = now.astimezone(tz)
    clock = _clock(start_time)
    days_ahead = (day_index - local_now.weekday()) % 7
    candidate = datetime.combine(
        local_now.date() + timedelta(days=days_ahead),
        clock,
        tzinfo=tz,
    )
    if candidate <= local_now:
        candidate += timedelta(days=7)
    return candidate


@dataclass(frozen=True, slots=True)
class DueRaidReminder:
    key: str
    team_name: str
    channel_id: int
    raid_at: datetime
    minutes_before: int
    message: str


class RaidReminderService:
    def __init__(
        self,
        *,
        roster_service: RosterService,
        config: DiscordCompanionConfig,
    ) -> None:
        self.roster_service = roster_service
        self.config = config
        self._sent: dict[str, datetime] = {}

    def _prune(self, now: datetime) -> None:
        cutoff = now - timedelta(days=8)
        self._sent = {key: value for key, value in self._sent.items() if value >= cutoff}

    def due_reminders(self, *, now: datetime | None = None) -> tuple[DueRaidReminder, ...]:
        now = now or datetime.now(tz=ZoneInfo("UTC"))
        self._prune(now)
        due: list[DueRaidReminder] = []

        for schedule in self.roster_service.list_team_schedules():
            channel_id = self.config.channel_id_for_team(schedule.TeamName)
            if channel_id is None:
                continue
            for slot in schedule.effective_slots:
                try:
                    raid_at = next_occurrence(
                        day=slot.Day,
                        start_time=slot.StartTime,
                        timezone=schedule.TimeZone,
                        now=now - timedelta(minutes=1),
                    )
                except ValueError:
                    continue

                for minutes_before in self.config.reminder_minutes:
                    fire_at = raid_at - timedelta(minutes=minutes_before)
                    delta = (now - fire_at.astimezone(now.tzinfo)).total_seconds()
                    if not 0 <= delta < 30:
                        continue

                    key = (
                        f"{schedule.TeamName.casefold()}|{raid_at.isoformat()}|"
                        f"{minutes_before}|{channel_id}"
                    )
                    if key in self._sent:
                        continue
                    self._sent[key] = now

                    mention = self.config.mention_for_team(schedule.TeamName)
                    focus = str(schedule.CurrentFocus or "").strip()
                    when = f"<t:{int(raid_at.timestamp())}:F>"
                    relative = f"<t:{int(raid_at.timestamp())}:R>"
                    message_parts = [
                        part
                        for part in (
                            mention,
                            f"**{schedule.TeamName} raid reminder**",
                            f"{when} ({relative})",
                            f"Current focus: {focus}" if focus else "",
                        )
                        if part
                    ]
                    due.append(
                        DueRaidReminder(
                            key=key,
                            team_name=schedule.TeamName,
                            channel_id=channel_id,
                            raid_at=raid_at,
                            minutes_before=minutes_before,
                            message="\n".join(message_parts),
                        )
                    )
        return tuple(due)


__all__ = [
    "DueRaidReminder",
    "RaidReminderService",
    "next_occurrence",
]
