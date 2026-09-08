from __future__ import annotations

"""Export recurring TeamSchedule entries as portable iCalendar (.ics) events."""

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from models.team_schedule import TeamSchedule, TeamScheduleSlot

_DAY_CODES = {
    "mon": (0, "MO"),
    "monday": (0, "MO"),
    "tue": (1, "TU"),
    "tues": (1, "TU"),
    "tuesday": (1, "TU"),
    "wed": (2, "WE"),
    "wednesday": (2, "WE"),
    "thu": (3, "TH"),
    "thur": (3, "TH"),
    "thurs": (3, "TH"),
    "thursday": (3, "TH"),
    "fri": (4, "FR"),
    "friday": (4, "FR"),
    "sat": (5, "SA"),
    "saturday": (5, "SA"),
    "sun": (6, "SU"),
    "sunday": (6, "SU"),
}


def _escape_ics(value: str) -> str:
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _parse_days(value: str) -> tuple[tuple[int, str], ...]:
    rows: list[tuple[int, str]] = []
    seen: set[int] = set()
    for raw in str(value or "").replace("/", ",").split(","):
        key = raw.strip().casefold().rstrip(".")
        if not key:
            continue
        row = _DAY_CODES.get(key)
        if row is None:
            raise ValueError(f"Unsupported raid day: {raw.strip()}")
        if row[0] not in seen:
            seen.add(row[0])
            rows.append(row)
    if not rows:
        raise ValueError("At least one raid day is required for calendar export.")
    return tuple(rows)


def _parse_time(value: str) -> tuple[int, int]:
    text = str(value or "").strip()
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.hour, parsed.minute
        except ValueError:
            pass
    raise ValueError(f"Unsupported raid time: {text or 'blank'}")


def _zone(schedule: TeamSchedule) -> ZoneInfo:
    zone_name = str(schedule.TimeZone or "").strip()
    if not zone_name:
        raise ValueError("A time zone is required for calendar export.")
    try:
        return ZoneInfo(zone_name)
    except Exception as exc:
        raise ValueError(f"Unknown time zone: {zone_name}") from exc


def _slot_day(slot: TeamScheduleSlot) -> tuple[int, str]:
    key = str(slot.Day or "").strip().casefold().rstrip(".")
    row = _DAY_CODES.get(key)
    if row is None:
        raise ValueError(f"Unsupported raid day: {slot.Day}")
    return row


def _first_slot_occurrence(
    schedule: TeamSchedule,
    slot: TeamScheduleSlot,
    *,
    now: datetime | None = None,
) -> datetime:
    zone = _zone(schedule)
    current = now.astimezone(zone) if now is not None else datetime.now(zone)
    weekday, _code = _slot_day(slot)
    hour, minute = _parse_time(slot.StartTime)
    delta = (weekday - current.weekday()) % 7
    candidate_date = current.date() + timedelta(days=delta)
    candidate = datetime(
        candidate_date.year,
        candidate_date.month,
        candidate_date.day,
        hour,
        minute,
        tzinfo=zone,
    )
    if candidate <= current:
        candidate += timedelta(days=7)
    return candidate


def _first_occurrence(schedule: TeamSchedule, *, now: datetime | None = None) -> datetime:
    """Backward-compatible helper returning the earliest configured slot."""
    slots = schedule.effective_slots
    if slots:
        return min(_first_slot_occurrence(schedule, slot, now=now) for slot in slots)

    zone = _zone(schedule)
    current = now.astimezone(zone) if now is not None else datetime.now(zone)
    hour, minute = _parse_time(schedule.RaidTime)
    days = _parse_days(schedule.RaidDays)
    candidates: list[datetime] = []
    for weekday, _code in days:
        delta = (weekday - current.weekday()) % 7
        candidate_date = current.date() + timedelta(days=delta)
        candidate = datetime(
            candidate_date.year,
            candidate_date.month,
            candidate_date.day,
            hour,
            minute,
            tzinfo=zone,
        )
        if candidate <= current:
            candidate += timedelta(days=7)
        candidates.append(candidate)
    return min(candidates)


def _slot_end(
    start: datetime,
    slot: TeamScheduleSlot,
    *,
    duration_minutes: int,
) -> datetime:
    if not str(slot.EndTime or "").strip():
        return start + timedelta(minutes=duration_minutes)
    end_hour, end_minute = _parse_time(slot.EndTime)
    end = start.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    if end <= start:
        end += timedelta(days=1)
    return end


def render_team_schedule_ics(
    schedule: TeamSchedule,
    *,
    duration_minutes: int = 180,
    now: datetime | None = None,
) -> str:
    if not str(schedule.TeamName or "").strip():
        raise ValueError("Team name is required for calendar export.")
    if duration_minutes <= 0:
        raise ValueError("Calendar event duration must be positive.")

    slots = schedule.effective_slots
    if not slots:
        raise ValueError("At least one raid day and start time are required for calendar export.")

    zone_name = str(schedule.TimeZone or "").strip()
    _zone(schedule)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Black Feather Foundry//FoundryDock Team Schedule//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for index, slot in enumerate(slots, start=1):
        start = _first_slot_occurrence(schedule, slot, now=now)
        end = _slot_end(start, slot, duration_minutes=duration_minutes)
        _weekday, day_code = _slot_day(slot)
        uid_seed = "-".join(
            piece
            for piece in (
                schedule.TeamName.strip().casefold().replace(" ", "-"),
                str(slot.Day or "").strip().casefold(),
                str(slot.StartTime or "").strip().casefold().replace(" ", ""),
                str(index),
            )
            if piece
        )
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{_escape_ics(uid_seed)}@foundrydock",
            f"SUMMARY:{_escape_ics(schedule.TeamName)} Raid",
            f"DTSTART;TZID={zone_name}:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID={zone_name}:{end.strftime('%Y%m%dT%H%M%S')}",
            f"RRULE:FREQ=WEEKLY;BYDAY={day_code}",
            "DESCRIPTION:Recurring ESO raid schedule exported from Black Feather Foundry.",
            "END:VEVENT",
        ])

    lines.extend(["END:VCALENDAR", ""])
    return "\r\n".join(lines)


def export_team_schedule_ics(
    schedule: TeamSchedule,
    path: str | Path,
    *,
    duration_minutes: int = 180,
) -> Path:
    target = Path(path)
    if target.suffix.casefold() != ".ics":
        target = target.with_suffix(".ics")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        render_team_schedule_ics(schedule, duration_minutes=duration_minutes),
        encoding="utf-8",
        newline="",
    )
    return target
