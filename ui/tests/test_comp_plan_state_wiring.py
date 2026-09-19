from pathlib import Path


def test_raid_plan_binding_creates_canonical_comp_state_before_legacy_projection() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    bind = source.split("def _bind_plan_comp_builder", 1)[1].split(
        "def _open_plan_comp_builder", 1
    )[0]
    state_index = bind.index("CompPlanStateService.from_raid_plan(")
    roster_index = bind.index("comp.apply_roster_team_context(")
    assert state_index < roster_index


def test_phase14_visible_plan_reads_raid_plan_facts_from_canonical_comp_state() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "def _state_chair_for_row(page, row: int):" in source
    render = source.split("def _refresh_plan_table(page)", 1)[1].split(
        "def _selected_backend_row", 1
    )[0]
    assert "chair_state = _state_chair_for_row(page, backend_row)" in render
    assert 'getattr(chair_state, "planned_gear_sets", ())' in render
    assert 'getattr(chair_state, "primary_assignment", "")' in render


def test_candidate_application_updates_canonical_state_and_respects_locks() -> None:
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(
        encoding="utf-8"
    )

    assert "def _candidate_state_changes(" in source
    assert 'chair.is_locked("class")' in source
    assert 'chair.is_locked("build")' in source
    assert 'chair.is_locked("gear")' in source
    assert 'changes["planned_skills"]' not in source.split(
        "def _candidate_state_changes", 1
    )[1].split("def _refresh_candidates", 1)[0]
    assert 'chair.is_locked("mundus")' in source
    assert "_replace_state_chair(page, chair.with_changes(**changes))" in source


def test_manual_gear_edits_update_canonical_state_and_respect_gear_lock() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    toggle = source.split("def _toggle_manual_set", 1)[1].split(
        "def _refresh_manual_set_picker", 1
    )[0]
    assert 'chair_state.is_locked("gear")' in toggle
    assert "planned_gear_sets=planned" in toggle
    assert "page._comp_plan_state.with_chair(" in toggle


def test_load_players_updates_canonical_state_without_overwriting_locks() -> None:
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(
        encoding="utf-8"
    )

    sync = source.split("def _sync_comp_state_from_matches", 1)[1].split(
        "def apply_roster_team_context", 1
    )[0]
    assert 'chair.is_locked("player")' in sync
    assert 'chair.is_locked("character")' in sync
    assert 'chair.is_locked("role")' in sync
    assert 'chair.is_locked("class")' in sync
    assert "page._comp_plan_state = current" in sync


def test_bound_comp_save_persists_state_directly_without_generated_draft() -> None:
    main = Path("ui/main_window.py").read_text(encoding="utf-8")
    shell = Path("ui/comp_builder_phase14_shell_support.py").read_text(
        encoding="utf-8"
    )

    direct = main.split("def _persist_comp_plan_state_to_raid_plan", 1)[1].split(
        "def _persist_generated_comp_plan_to_raid_plan", 1
    )[0]
    assert "CompPlanStateService.to_raid_plan(state, base_plan=base_plan)" in direct
    assert "GeneratedRosterDraftService" not in direct
    assert "raid_plan_from_generated_slots" not in direct

    save = shell.split("def _save_to_originating_raid_plan", 1)[1].split(
        "def _build_health", 1
    )[0]
    canonical_branch = save.split("else:", 1)[0]
    assert "_persist_comp_plan_state_to_raid_plan" in canonical_branch
    assert "save_generated_plan" not in canonical_branch


def test_raid_plan_visible_save_merge_preserves_comp_locks() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    merge = source.split("def merge_visible_plan_with_loaded_snapshot", 1)[1].split(
        "class RaidPlanPersistencePage", 1
    )[0]
    assert "comp_locked_fields=prior.comp_locked_fields" in merge


def test_comp_plan_name_picker_uses_canonical_state_and_five_piece_manual_restore() -> None:
    source = Path("ui/comp_builder_page.py").read_text(encoding="utf-8")

    selected = source.split("def _raid_plan_name_selected", 1)[1].split(
        "def _build_ui", 1
    )[0]
    assert "CompPlanStateService.from_raid_plan(" in selected
    assert "_five_piece_set_names(" in selected
    assert "[:2]" in selected
    assert "tuple(member.planned_gear_sets or ())" in selected
    assert "self._comp_plan_state =" in selected
