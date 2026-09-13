from pathlib import Path


def test_assignments_use_one_simple_optional_boss_selector() -> None:
    source = Path("ui/roster_encounter_assignment_context_support.py").read_text(encoding="utf-8")

    assert 'QLabel("Boss (optional)")' in source
    assert '"Team Default (most common)"' in source
    assert "Pick a boss only when someone's job changes for that fight." in source


def test_team_change_returns_to_safe_team_default() -> None:
    source = Path("ui/roster_encounter_assignment_context_support.py").read_text(encoding="utf-8")

    assert "_reset_encounter_to_default(page)" in source
    assert "team_selector_changed_with_safe_default" in source
    assert "select_team_for_assignments_with_safe_default" in source


def test_obsolete_encounter_override_tab_is_removed() -> None:
    source = Path("ui/roster_encounter_assignment_context_support.py").read_text(encoding="utf-8")

    assert '== "encounter overrides"' in source
    assert "tabs.removeTab(index)" in source


def test_context_selector_installs_before_assignment_persistence() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert source.index("install_roster_encounter_assignment_context_support()") < source.index(
        "install_roster_assignment_persistence_support()"
    )


def test_quick_actions_resolve_selected_build_variant() -> None:
    source = Path("ui/roster_assignment_context_action_support.py").read_text(encoding="utf-8")

    assert "resolve_build_context(" in source
    assert "team_name=team_name" in source
    assert "boss_name=boss_name" in source
