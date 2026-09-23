from __future__ import annotations

from pathlib import Path

from models.build_model import GearSlot, PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember
from models.roster_model import RosterMember
from models.team_schedule import TeamSchedule, TeamScheduleSlot
from services.eso_database import EsoDatabase
from services.finch_api_client import FinchSharedSnapshot
from services.finch_shared_publish_service import (
    FinchSharedPublishService,
    shared_raid_plan_payload,
    shared_team_payload,
)
from services.roster_service import RosterService


class FakeClient:
    def __init__(self) -> None:
        self.team_calls = []
        self.plan_calls = []

    def publish_shared_team(self, *, snapshot_key, payload, schema_version=1):
        self.team_calls.append((snapshot_key, payload, schema_version))
        return FinchSharedSnapshot(
            kind="team",
            snapshot_key=snapshot_key.casefold(),
            schema_version=schema_version,
            payload=payload,
            published_by="Jarakeen",
            updated_at="2026-09-20T00:00:00+00:00",
        )

    def publish_shared_raid_plan(self, *, snapshot_key, payload, schema_version=1):
        self.plan_calls.append((snapshot_key, payload, schema_version))
        return FinchSharedSnapshot(
            kind="raid_plan",
            snapshot_key=snapshot_key.casefold(),
            schema_version=schema_version,
            payload=payload,
            published_by="Jarakeen",
            updated_at="2026-09-20T00:00:00+00:00",
        )


def _roster(tmp_path: Path) -> RosterService:
    roster = RosterService(EsoDatabase(tmp_path / "eso.db"))
    member_id = roster.create_member(
        RosterMember(
            PlayerName="Rylo",
            CharacterName="Rylos Arcanist",
            EsoClass="Arcanist",
            PrimaryRole="Damage Dealer",
            SecondaryRole="",
            Team="Performance Mode",
            Status="Active",
            DiscordName="private-discord-name",
            PersonnelNotes="this must remain local",
            YouTube="https://private.example/youtube",
            Twitch="https://private.example/twitch",
        )
    )
    assert member_id > 0
    roster.set_team_schedule(
        TeamSchedule(
            TeamName="Performance Mode",
            TimeZone="America/New_York",
            CurrentFocus="Swashbuckler Supreme",
            DiscordUrl="https://discord.gg/private",
            Slots=(
                TeamScheduleSlot(Day="Mon", StartTime="9:00 PM", EndTime="11:00 PM"),
                TeamScheduleSlot(Day="Wed", StartTime="9:00 PM", EndTime="11:00 PM"),
            ),
        )
    )
    return roster


def test_shared_team_payload_is_small_and_excludes_private_personnel_fields(tmp_path: Path) -> None:
    roster = _roster(tmp_path)

    payload = shared_team_payload(roster, "performance mode")

    assert payload["team_name"] == "Performance Mode"
    assert payload["schedule"]["timezone"] == "America/New_York"
    assert payload["schedule"]["current_focus"] == "Swashbuckler Supreme"
    assert payload["roster"] == {
        "seat_capacity": 12,
        "filled_seats": 1,
        "open_seats": 11,
        "open_seats_by_role": {
            "Tank": 2,
            "Healer": 2,
            "Damage Dealer": 7,
        },
    }
    assert payload["members"][0] == {
        "player_name": "Rylo",
        "character_name": "Rylos Arcanist",
        "eso_class": "Arcanist",
        "primary_role": "Damage Dealer",
        "secondary_role": "",
        "status": "Active",
    }
    rendered = repr(payload)
    assert "private-discord-name" not in rendered
    assert "this must remain local" not in rendered
    assert "discord.gg/private" not in rendered
    assert "private.example" not in rendered


def test_shared_raid_plan_payload_excludes_local_ids_builds_and_notes() -> None:
    plan = RaidPlan(
        plan_id="ss-performance-mode",
        trial_id="sunspire",
        name="Performance Mode SS",
        team_name="Performance Mode",
        difficulty="Veteran",
        status="planning",
        plan_note="private raid lead note",
        members=(
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Rylo",
                roster_member_id=42,
                player_id="player-local-id",
                character_id="character-local-id",
                character_name="Rylos Arcanist",
                role="Damage Dealer",
                eso_class="Arcanist",
                selected_build_id="build-local-id",
                selected_build_name="Corpsebuster Support",
                build_source_kind="comp",
                build_source_name="Performance Mode RG",
                build_source_url="https://private.example/build",
                planned_gear_sets=("Corpsebuster", "Null Arca"),
                planned_skills=("Fatecarver",),
                planned_mundus="The Thief",
                primary_assignment="Major Courage",
                secondary_assignment="Minor Toughness",
                utility_assignments=("Portal", "Interrupt"),
                notes="private chair note",
            ),
        ),
    )

    payload = shared_raid_plan_payload(plan)

    assert payload["plan_id"] == "ss-performance-mode"
    assert payload["members"] == [
        {
            "seat_id": "dd-1",
            "house_stack_number": 1,
            "gamertag": "Rylo",
            "character_name": "Rylos Arcanist",
            "role": "Damage Dealer",
            "eso_class": "Arcanist",
            "primary_assignment": "Major Courage",
            "secondary_assignment": "Minor Toughness",
            "utility_assignments": ["Portal", "Interrupt"],
            "build_summary": {
                "name": "Corpsebuster Support",
                "source_kind": "comp",
                "source_name": "Performance Mode RG",
                "planned_gear_sets": ["Corpsebuster", "Null Arca"],
                "planned_mundus": "The Thief",
                "front_weapon": "",
                "back_weapon": "",
                "front_skills": ["Fatecarver"],
                "back_skills": [],
                "food": "",
                "potion": "",
            },
        }
    ]
    rendered = repr(payload)
    for forbidden in (
        "player-local-id",
        "character-local-id",
        "build-local-id",
        "https://private.example/build",
        "private raid lead note",
        "private chair note",
    ):
        assert forbidden not in rendered


def test_publish_service_uses_versioned_snapshots(tmp_path: Path) -> None:
    roster = _roster(tmp_path)
    client = FakeClient()
    service = FinchSharedPublishService(client=client, roster=roster)

    team_result = service.publish_team("Performance Mode")
    plan = RaidPlan(
        plan_id="rg-pm",
        trial_id="rockgrove",
        name="RG",
        team_name="Performance Mode",
        members=(RaidPlanMember(seat_id="tank-1", gamertag="Tank"),),
    )
    plan_result = service.publish_raid_plan(plan)

    assert client.team_calls[0][0] == "Performance Mode"
    assert client.team_calls[0][2] == 2
    assert client.plan_calls[0][0] == "rg-pm"
    assert client.plan_calls[0][2] == 5
    assert team_result.kind == "team"
    assert plan_result.kind == "raid_plan"



def test_shared_raid_plan_payload_includes_sub_ready_operational_build_fields() -> None:
    plan = RaidPlan(
        plan_id="rg-pm",
        trial_id="rockgrove",
        name="Rockgrove HM",
        team_name="Performance Mode",
        difficulty="HM",
        members=(
            RaidPlanMember(
                seat_id="tank-2",
                gamertag="Rylo",
                character_name="Rylo DK",
                role="Tank",
                eso_class="Dragonknight",
                selected_build_id="tank-build-id",
                selected_build_name="RG Tank 2",
                planned_gear_sets=("Pearlescent Ward", "Turning Tide", "Nazaray"),
                planned_mundus="The Atronach",
                primary_assignment="Main Tank · Oax",
                secondary_assignment="Backup: Bahsei",
            ),
        ),
    )
    build = PlayerBuild(
        Name="Rylo DK",
        Gamertag="Rylo",
        BuildName="RG Tank 2",
        BuildId="tank-build-id",
        EsoClass="Dragonknight",
        Role="Tank",
        Mundus="The Atronach",
        FrontBarWeapon=GearSlot(WeaponType="Sword"),
        FrontBarOffHand=GearSlot(WeaponType="Shield"),
        BackBarWeapon=GearSlot(WeaponType="Ice Staff"),
        FrontBarSkills=["Pierce Armor", "Heroic Slash", "Igneous Shield", "Balance", "Defensive Stance", "Barrier"],
        BackBarSkills=["Elemental Blockade", "Inner Rage", "Resolving Vigor", "Green Dragon Blood", "Unrelenting Grip", "Aggressive Horn"],
        Food="Orzorga's Smoked Bear Haunch",
        Potion="Tri-Stat",
    )

    payload = shared_raid_plan_payload(plan, saved_builds=(build,))
    summary = payload["members"][0]["build_summary"]

    assert summary["front_weapon"] == "Sword & Board"
    assert summary["back_weapon"] == "Ice Staff"
    assert summary["front_skills"][0] == "Pierce Armor"
    assert summary["back_skills"][0] == "Elemental Blockade"
    assert summary["food"] == "Orzorga's Smoked Bear Haunch"
    assert summary["potion"] == "Tri-Stat"
    assert summary["planned_mundus"] == "The Atronach"
