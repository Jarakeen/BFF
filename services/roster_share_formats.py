from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from models.roster_model import RosterMember
from models.team_schedule import TeamSchedule
from services.team_schedule_share_export import _public_assignment_build


CSV_COLUMNS = (
    "Player",
    "Character",
    "Class",
    "Role",
    "Build",
    "Primary",
    "Secondary",
    "Gear",
    "Notes",
    "Ready",
    "Team",
    "Raid Days",
    "Raid Time",
    "Time Zone",
    "Status",
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _member_lookup(members: Iterable[RosterMember]) -> dict[str, RosterMember]:
    lookup: dict[str, RosterMember] = {}
    for member in members:
        for value in (member.PlayerName, member.CharacterName):
            key = _clean(value).casefold()
            if key and key not in lookup:
                lookup[key] = member
    return lookup


def _schedule_lookup(schedules: Sequence[TeamSchedule]) -> dict[str, TeamSchedule]:
    return {
        _clean(schedule.TeamName).casefold(): schedule
        for schedule in schedules
        if _clean(schedule.TeamName)
    }


def roster_share_rows(
    members: Iterable[RosterMember],
    *,
    assignments: Sequence[Mapping[str, object]] = (),
    team_schedules: Sequence[TeamSchedule] = (),
) -> list[dict[str, str]]:
    member_rows = list(members)
    people = _member_lookup(member_rows)
    schedules = _schedule_lookup(team_schedules)
    rows: list[dict[str, str]] = []

    if assignments:
        for item in assignments:
            player = _clean(item.get("player"))
            member = people.get(player.casefold())
            team = _clean(member.Team) if member else ""
            schedule = schedules.get(team.casefold())
            rows.append({
                "Player": player,
                "Character": _clean(member.CharacterName) if member else "",
                "Class": _clean(item.get("class")) or (_clean(member.EsoClass) if member else ""),
                "Role": _clean(item.get("role")) or (_clean(member.PrimaryRole) if member else ""),
                "Build": _clean(_public_assignment_build(item)),
                "Primary": _clean(item.get("primary")),
                "Secondary": _clean(item.get("secondary")),
                "Gear": _clean(item.get("gear")),
                "Notes": _clean(item.get("notes")),
                "Ready": _clean(item.get("ready")),
                "Team": team,
                "Raid Days": _clean(schedule.RaidDays) if schedule else "",
                "Raid Time": _clean(schedule.RaidTime) if schedule else "",
                "Time Zone": _clean(schedule.TimeZone) if schedule else "",
                "Status": _clean(member.Status) if member else "",
            })
        return rows

    for member in member_rows:
        team = _clean(member.Team)
        schedule = schedules.get(team.casefold())
        rows.append({
            "Player": _clean(member.PlayerName),
            "Character": _clean(member.CharacterName),
            "Class": _clean(member.EsoClass),
            "Role": _clean(member.PrimaryRole),
            "Build": "",
            "Primary": "",
            "Secondary": _clean(member.SecondaryRole),
            "Gear": "",
            "Notes": "",
            "Ready": "",
            "Team": team,
            "Raid Days": _clean(schedule.RaidDays) if schedule else "",
            "Raid Time": _clean(schedule.RaidTime) if schedule else "",
            "Time Zone": _clean(schedule.TimeZone) if schedule else "",
            "Status": _clean(member.Status),
        })
    return rows


def export_roster_csv(
    path: str | Path,
    members: Iterable[RosterMember],
    *,
    assignments: Sequence[Mapping[str, object]] = (),
    team_schedules: Sequence[TeamSchedule] = (),
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = roster_share_rows(
        members,
        assignments=assignments,
        team_schedules=team_schedules,
    )
    # utf-8-sig makes Excel/Sheets behave nicely with punctuation and names.
    with target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return target


def _role_bucket(role: str) -> str:
    lowered = _clean(role).casefold()
    if "tank" in lowered:
        return "Tanks"
    if "heal" in lowered:
        return "Healers"
    if "damage" in lowered or "dps" in lowered or "dd" == lowered:
        return "Damage"
    return "Other"


def _schedule_line(schedules: Sequence[TeamSchedule], title: str) -> str:
    configured = [schedule for schedule in schedules if schedule.is_configured]
    if not configured:
        return ""
    wanted = _clean(title).casefold()
    schedule = next(
        (item for item in configured if _clean(item.TeamName).casefold() == wanted),
        configured[0],
    )
    return " · ".join(
        value for value in (
            _clean(schedule.RaidDays),
            _clean(schedule.RaidTime),
            _clean(schedule.TimeZone),
        )
        if value
    )


def discord_roster_text(
    members: Iterable[RosterMember],
    *,
    assignments: Sequence[Mapping[str, object]] = (),
    team_schedules: Sequence[TeamSchedule] = (),
    title: str = "Raid Roster",
) -> str:
    rows = roster_share_rows(
        members,
        assignments=assignments,
        team_schedules=team_schedules,
    )
    lines = [f"## {_clean(title) or 'Raid Roster'}"]
    schedule = _schedule_line(team_schedules, title)
    if schedule:
        lines.append(f"**{schedule}**")
    lines.append("")

    buckets: dict[str, list[dict[str, str]]] = {
        "Tanks": [],
        "Healers": [],
        "Damage": [],
        "Other": [],
    }
    for row in rows:
        buckets[_role_bucket(row["Role"])].append(row)

    for heading in ("Tanks", "Healers", "Damage", "Other"):
        bucket = buckets[heading]
        if not bucket:
            continue
        lines.append(f"### {heading}")
        for row in bucket:
            player = row["Player"] or "Open Slot"
            summary = [row["Class"], row["Role"]]
            if row["Build"]:
                summary.append(row["Build"])
            details = " · ".join(value for value in summary if value)
            lines.append(f"• **{player}**" + (f" · {details}" if details else ""))
            assignment_bits = []
            if row["Primary"]:
                assignment_bits.append(row["Primary"])
            if row["Secondary"]:
                assignment_bits.append(row["Secondary"])
            if assignment_bits:
                lines.append(f"  ↳ {' / '.join(assignment_bits)}")
            if row["Gear"]:
                lines.append(f"  Gear: {row['Gear']}")
            if row["Notes"]:
                lines.append(f"  Note: {row['Notes']}")
        lines.append("")

    text = "\n".join(lines).strip()
    # Discord's normal message limit is 2000 chars. Prefer a compact fallback
    # instead of copying text that cannot be pasted as one message.
    if len(text) <= 1950:
        return text

    compact = [f"## {_clean(title) or 'Raid Roster'}"]
    if schedule:
        compact.append(f"**{schedule}**")
    compact.append("")
    for heading in ("Tanks", "Healers", "Damage", "Other"):
        bucket = buckets[heading]
        if not bucket:
            continue
        compact.append(f"### {heading}")
        for row in bucket:
            player = row["Player"] or "Open Slot"
            summary = " · ".join(value for value in (row["Class"], row["Build"]) if value)
            compact.append(f"• **{player}**" + (f" · {summary}" if summary else ""))
        compact.append("")
    return "\n".join(compact).strip()[:1950]
