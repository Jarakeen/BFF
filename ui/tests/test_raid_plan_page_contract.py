from pathlib import Path
from types import SimpleNamespace

from ui.raid_plan_page import (
    RAID_PLAN_SEATS,
    new_personnel_member,
    personnel_player_names,
    raid_plan_member_from_values,
    role_for_seat,
)


def test_raid_plan_workspace_exposes_twelve_standard_trial_chairs() -> None:
    assert RAID_PLAN_SEATS == (
        "Main Tank",
        "Off Tank",
        "Healer 1",
        "Healer 2",
        "DD 1",
        "DD 2",
        "DD 3",
        "DD 4",
        "DD 5",
        "DD 6",
        "DD 7",
        "DD 8",
    )


def test_raid_plan_member_can_start_with_only_gamertag() -> None:
    member = raid_plan_member_from_values(
        seat_id="DD 4",
        gamertag="FriendName",
    )

    assert member is not None
    assert member.seat_id == "dd-4"
    assert member.gamertag == "FriendName"
    assert member.character_name is None
    assert member.role is None
    assert member.eso_class is None
    assert member.selected_build_name is None


def test_empty_chair_is_not_materialized_as_fake_member() -> None:
    member = raid_plan_member_from_values(
        seat_id="Healer 2",
        gamertag="   ",
        role="Healer",
    )

    assert member is None


def test_selected_character_and_build_remain_plan_references() -> None:
    member = raid_plan_member_from_values(
        seat_id="Healer 1",
        gamertag="Jarakeen",
        character_name="Magrat",
        role="Healer",
        eso_class="Warden",
        selected_build_name="DF Healer",
    )

    assert member is not None
    assert member.character_name == "Magrat"
    assert member.role == "Healer"
    assert member.eso_class == "Warden"
    assert member.selected_build_name == "DF Healer"


def test_personnel_autocomplete_names_are_player_level_and_deduplicated() -> None:
    members = (
        SimpleNamespace(PlayerName="Jarakeen", CharacterName="Magrat"),
        SimpleNamespace(PlayerName="jarakeen", CharacterName="Another Character"),
        SimpleNamespace(PlayerName="Rylo", CharacterName="Rylonia"),
        SimpleNamespace(PlayerName="", CharacterName="Character Without Player"),
    )

    assert personnel_player_names(members) == ("Jarakeen", "Rylo")


def test_raid_plan_new_personnel_record_creates_player_identity_only() -> None:
    member = new_personnel_member("  NewFriend  ")

    assert member.PlayerName == "NewFriend"
    assert member.CharacterName == ""
    assert member.EsoClass == ""
    assert member.PrimaryRole == ""
    assert member.SecondaryRole == ""
    assert member.Team == ""
    assert member.Status == "Active"


def test_raid_plan_new_personnel_record_requires_gamertag() -> None:
    try:
        new_personnel_member("   ")
    except ValueError as exc:
        assert "gamertag" in str(exc).casefold()
    else:
        raise AssertionError("empty gamertag should not create a Personnel record")


def test_raid_plan_seat_is_the_role_authority() -> None:
    assert role_for_seat("Main Tank") == "Tank"
    assert role_for_seat("Off Tank") == "Tank"
    assert role_for_seat("Healer 1") == "Healer"
    assert role_for_seat("Healer 2") == "Healer"
    assert role_for_seat("DD 1") == "DD"
    assert role_for_seat("DD 8") == "DD"


def test_raid_plan_class_column_uses_searchable_contains_autocomplete() -> None:
    source = Path("ui/raid_plan_page.py").read_text(encoding="utf-8")
    assert '("SEAT", "GAMERTAG", "CHARACTER", "CLASS", "BUILD", "PERSONNEL")' in source
    assert "class_combo.setEditable(True)" in source
    assert "class_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)" in source
    assert "class_completer.setFilterMode(Qt.MatchFlag.MatchContains)" in source
    assert "class_combo.setCompleter(class_completer)" in source
