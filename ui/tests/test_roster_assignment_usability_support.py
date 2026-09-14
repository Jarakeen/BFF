from pathlib import Path


def test_assignment_headers_sort_player_role_and_class_only():
    source = Path("ui/roster_assignment_usability_support.py").read_text(encoding="utf-8")

    assert '_SORTABLE_COLUMNS = {0: "Player", 1: "Role", 2: "Class"}' in source
    assert "header.sectionClicked.connect" in source
    assert "table.sortItems(column, order)" in source
    assert "Qt.SortOrder.AscendingOrder" in source
    assert "Qt.SortOrder.DescendingOrder" in source
    assert "_apply_saved_sort(self)" in source


def test_boss_selector_uses_contains_autocomplete_and_reviewed_raid_identities():
    source = Path("ui/roster_assignment_usability_support.py").read_text(encoding="utf-8")

    assert "load_raid_encounter_identities(get_data_dir())" in source
    assert "row.display_name" in source
    assert "row.encounter_id" in source
    assert "combo.setEditable(True)" in source
    assert "QComboBox.InsertPolicy.NoInsert" in source
    assert "QCompleter" in source
    assert "Qt.CaseSensitivity.CaseInsensitive" in source
    assert "Qt.MatchFlag.MatchContains" in source
    assert "QCompleter.CompletionMode.PopupCompletion" in source
    assert "setClearButtonEnabled(True)" in source


def test_reviewed_identity_keeps_lylanar_and_turlassil_as_one_planning_fight():
    source = Path("data/raid_encounter_identity.json").read_text(encoding="utf-8")

    assert '"encounter_id":"lylanar_turlassil"' in source
    assert '"display_name":"Lylanar and Turlassil"' in source
    assert '"member_ids":["lylanar","turlassil"]' in source


def test_assignment_usability_installs_after_context_actions():
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert "install_roster_assignment_usability_support()" in source
    assert source.index("install_roster_assignment_context_action_support()") < source.index(
        "install_roster_assignment_usability_support()"
    )
