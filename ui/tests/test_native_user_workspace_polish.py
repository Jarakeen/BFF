from pathlib import Path


def test_rotation_numeric_hints_are_native_placeholders_not_defaults() -> None:
    dd_controls = Path("ui/rotation_dd_evaluation_policy_controls.py").read_text(
        encoding="utf-8"
    )
    dashboard = Path("ui/rotation_dashboard_canonical_page.py").read_text(
        encoding="utf-8"
    )

    assert 'setPlaceholderText("18,200 armor (typical PvE)")' in dd_controls
    assert 'setPlaceholderText("35% suggested")' in dashboard
    assert 'setSpecialValueText("")' in dd_controls
    assert 'setSpecialValueText("")' in dashboard
    assert "setValue(18200" not in dd_controls
    assert "setValue(35" not in dashboard


def test_character_command_is_natively_a_normal_card() -> None:
    source = Path("ui/operations_console.py").read_text(encoding="utf-8")
    player_card = source.split("def _player_card", 1)[1].split("def ", 1)[0]

    assert 'FoundryCard("Character Command")' in player_card
    assert "overviewAccent" not in player_card


def test_personnel_record_natively_uses_gamertag_hint() -> None:
    source = Path("widgets/roster_record.py").read_text(encoding="utf-8")

    assert 'self.player_name.setPlaceholderText("Gamertag")' in source


def test_characters_navigation_natively_opens_personnel_by_label() -> None:
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    characters = source.split('if page_name == "characters":', 1)[1].split(
        'if page_name == "scribed_skills":', 1
    )[0]

    assert '_tab_index_by_text(roster_page.tabs, "PERSONNEL")' in characters
    assert "roster_page.tabs.setCurrentIndex(personnel_index)" in characters
    assert "roster_page.tabs.setCurrentIndex(1)" not in characters


def test_obsolete_workspace_polish_installer_is_not_composed() -> None:
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")

    assert "user_workspace_polish_support" not in source
