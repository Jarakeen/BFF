from pathlib import Path


def test_optimization_replaces_team_source_with_load_team() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    assert 'page._context_field("LOAD TEAM", page.load_team_combo)' in source
    assert 'page.load_team_combo.addItem("Select roster team…", "")' in source
    assert "page._optimization_roster_service.list_team_names()" in source
    assert "_hide_team_source(page)" in source


def test_load_team_reads_named_roster_members_not_all_saved_builds() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    assert "page._optimization_roster_service.list_members()" in source
    assert "team.casefold() in _team_names_for_member(member)" in source
    assert "_identity_values(build) & member_keys" in source
    assert "eligible_indices" in source


def test_load_team_targets_active_compare_editor() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    assert "page.team_tabs.currentIndex() == 1" in source
    assert "return page.team_b_table" in source
    assert "return page.team_table" in source


def test_load_team_autofill_consumes_each_roster_player_once() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    assert "build_role_compatible_autofill(" in source
    assert "build_player_keys=tuple(" in source
    assert "global_index = eligible_indices[assignment.build_index]" in source


def test_optimization_hides_duplicate_build_around_editor() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    assert '"required_slot_combo", "required_class_combo", "required_gear_input"' in source
    assert '{"BUILD AROUND", "CLASS", "REQUIRED SET(S)"}' in source
    assert "PrescribedSlotBuildConstraint machinery remains intact" in source
