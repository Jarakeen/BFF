from pathlib import Path

from ui import user_workspace_polish_support


def _source() -> str:
    return Path(user_workspace_polish_support.__file__).read_text(encoding="utf-8")


def test_rotation_numeric_hints_are_placeholders_not_defaults() -> None:
    source = _source()

    assert 'setPlaceholderText("18,200 armor (typical PvE)")' in source
    assert 'setPlaceholderText("35% suggested")' in source
    assert 'setSpecialValueText("")' in source
    assert "setValue(18200" not in source
    assert "setValue(35" not in source


def test_character_command_accent_is_removed() -> None:
    source = _source()

    assert 'card.setProperty("overviewAccent", None)' in source
    assert "OperationsConsole._player_card = player_card_without_accent" in source


def test_personnel_record_uses_gamertag_hint() -> None:
    source = _source()

    assert 'self.player_name.setPlaceholderText("Gamertag")' in source


def test_characters_navigation_opens_personnel_by_label() -> None:
    source = _source()

    assert 'if page_name == "characters":' in source
    assert '_tab_index_by_text(tabs, "PERSONNEL")' in source
    assert "tabs.setCurrentIndex(personnel_index)" in source


def test_polish_installs_after_rotation_and_roster_composition() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    polish_call = source.index("install_user_workspace_polish_support()")
    assert source.index("install_roster_player_architecture_support()") < polish_call
    assert source.index("install_rotation_dashboard_layout_support()") < polish_call
    assert source.index("install_build_rotation_artifact_support()") < polish_call
