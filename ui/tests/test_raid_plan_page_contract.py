from pathlib import Path
from types import SimpleNamespace

from ui.raid_plan_page import (
    RAID_PLAN_SEATS,
    is_seat_placeholder,
    new_personnel_member,
    personnel_player_names,
    raid_plan_member_from_values,
    role_for_seat,
)


def test_raid_plan_workspace_exposes_twelve_standard_trial_chairs() -> None:
    assert RAID_PLAN_SEATS == (
        "Tank 1",
        "Tank 2",
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
    assert role_for_seat("Tank 1") == "Tank"
    assert role_for_seat("Tank 2") == "Tank"
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


def test_personnel_refresh_preserves_blank_player_chairs() -> None:
    source = Path("ui/raid_plan_page.py").read_text(encoding="utf-8")
    assert "combo.setCurrentIndex(-1)" in source
    assert "combo.lineEdit().clear()" in source
    assert "Blank Raid Plan chairs" in source


def test_raid_plan_lower_action_row_exposes_save_and_city_shell_owns_comp_navigation() -> None:
    base_source = Path("ui/raid_plan_page.py").read_text(encoding="utf-8")
    city_source = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")

    assert 'self.lower_save_plan_button = FoundryButton(' in base_source
    assert '"Save",' in base_source
    assert '("Comp Builder", "comp_builder")' in city_source
    assert 'button.clicked.connect(lambda _=False, target=route: self.pageRequested.emit(target))' in city_source


def test_lower_raid_plan_save_is_bound_by_persistence_page() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")
    assert 'lower_save = getattr(self, "lower_save_plan_button", None)' in source
    assert "lower_save.clicked.connect(self.save_current_plan)" in source


def test_lower_raid_plan_save_binding_does_not_disconnect_empty_signal() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")
    assert "lower_save.clicked.connect(self.save_current_plan)" in source
    assert "lower_save.clicked.disconnect()" not in source


def test_class_only_recruit_chair_is_persistable_without_gamertag() -> None:
    member = raid_plan_member_from_values(
        seat_id="Tank 1",
        gamertag="",
        role="Tank",
        eso_class="Dragonknight",
    )

    assert member is not None
    assert member.seat_id == "tank-1"
    assert member.gamertag == ""
    assert member.role == "Tank"
    assert member.eso_class == "Dragonknight"


def test_raid_plan_player_picker_uses_seat_as_empty_placeholder() -> None:
    source = Path("ui/raid_plan_page.py").read_text(encoding="utf-8")
    assert 'player_combo.lineEdit().setPlaceholderText(seat)' in source


def test_raid_plan_seat_placeholders_are_never_personnel_players() -> None:
    for seat in RAID_PLAN_SEATS:
        assert is_seat_placeholder(seat)
        assert is_seat_placeholder(f"  {seat.lower()}  ")
        try:
            new_personnel_member(seat)
        except ValueError as exc:
            assert "seat placeholders" in str(exc)
        else:
            raise AssertionError(f"{seat} was incorrectly accepted as a Personnel player")

    assert not is_seat_placeholder("DDDestroyer")
    assert new_personnel_member("DDDestroyer").PlayerName == "DDDestroyer"


def test_raid_plan_auto_promotion_skips_seat_placeholders() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert "if not gamertag or is_seat_placeholder(gamertag):" in source
    assert "Raid Plan seat placeholders cannot be saved as players." in source


def test_city_raid_plan_exposes_build_share_menu() -> None:
    source = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")

    assert 'self.share_builds_button = QPushButton("Share Builds ▾")' in source
    assert 'share_menu.addAction("Export Ink-Light PDF")' in source
    assert 'share_menu.addAction("Export CSV")' in source
    assert 'share_menu.addAction("Copy for Discord")' in source
    assert "export_raid_plan_builds_pdf" in source
    assert "export_raid_plan_builds_csv" in source
    assert "raid_plan_discord_builds_text" in source
