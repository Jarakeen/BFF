from __future__ import annotations

import csv

from models.roster_model import RosterMember
from models.team_schedule import TeamSchedule
from services.roster_share_formats import discord_roster_text, export_roster_csv


def _members():
    return [
        RosterMember(
            PlayerName="Keen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
            SecondaryRole="Damage Dealer",
            Status="Active",
            Team="GH Prog",
        ),
        RosterMember(
            PlayerName="Tank One",
            CharacterName="Brick",
            EsoClass="Dragonknight",
            PrimaryRole="Tank",
            Status="Active",
            Team="GH Prog",
        ),
    ]


def _assignments():
    return [
        {
            "player": "Keen",
            "role": "Healer",
            "class": "Warden",
            "build": "DF Healer",
            "primary": "Major Courage",
            "secondary": "Brittle",
            "gear": "SPC / PP",
            "notes": "Stack left",
            "ready": "Ready",
        },
        {
            "player": "Tank One",
            "role": "Tank",
            "class": "Dragonknight",
            "build": "MT",
            "primary": "Boss",
            "secondary": "Adds",
            "gear": "Turning Tide",
            "notes": "",
            "ready": "Ready",
        },
    ]


def _schedules():
    return [
        TeamSchedule(
            TeamName="GH Prog",
            RaidDays="Tue, Thu",
            RaidTime="8:00 PM",
            TimeZone="America/New_York",
        )
    ]


def test_google_sheets_csv_keeps_assignment_and_schedule_columns(tmp_path):
    path = tmp_path / "roster.csv"
    export_roster_csv(
        path,
        _members(),
        assignments=_assignments(),
        team_schedules=_schedules(),
    )

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 2
    assert rows[0]["Player"] == "Keen"
    assert rows[0]["Character"] == "Magrat"
    assert rows[0]["Build"] == "DF Healer"
    assert rows[0]["Primary"] == "Major Courage"
    assert rows[0]["Secondary"] == "Brittle"
    assert rows[0]["Team"] == "GH Prog"
    assert rows[0]["Raid Days"] == "Tue, Thu"
    assert rows[0]["Raid Time"] == "8:00 PM"
    assert rows[0]["Time Zone"] == "America/New_York"


def test_discord_share_is_role_grouped_and_mobile_readable():
    text = discord_roster_text(
        _members(),
        assignments=_assignments(),
        team_schedules=_schedules(),
        title="GH Prog",
    )

    assert text.startswith("## GH Prog")
    assert "**Tue, Thu · 8:00 PM · America/New_York**" in text
    assert "### Tanks" in text
    assert "### Healers" in text
    assert "• **Keen** · Warden · Healer · DF Healer" in text
    assert "↳ Major Courage / Brittle" in text
    assert "Gear: SPC / PP" in text
    assert len(text) <= 1950


def test_discord_share_falls_back_to_compact_message_under_discord_limit():
    assignments = []
    members = []
    for index in range(40):
        player = f"Player {index:02d}"
        members.append(
            RosterMember(
                PlayerName=player,
                CharacterName=f"Character {index:02d}",
                EsoClass="Arcanist",
                PrimaryRole="Damage Dealer",
                Status="Active",
                Team="Huge Team",
            )
        )
        assignments.append({
            "player": player,
            "role": "Damage Dealer",
            "class": "Arcanist",
            "build": "Very Long Damage Build Name",
            "primary": "A very long primary assignment that would make Discord complain",
            "secondary": "Another extremely long secondary assignment",
            "gear": "Extremely Long Gear Set Name / Another Extremely Long Gear Set Name",
            "notes": "Notes that add even more text to the share message",
            "ready": "Ready",
        })

    text = discord_roster_text(
        members,
        assignments=assignments,
        title="Huge Team",
    )

    assert len(text) <= 1950
    assert "## Huge Team" in text
    assert "### Damage" in text
