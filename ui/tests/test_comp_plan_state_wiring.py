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


def test_comp_page_participates_in_app_wide_unsaved_navigation_contract() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "def _has_pending_changes(page) -> bool:" in source
    assert "def _save_pending_changes(page) -> bool:" in source
    assert "def _discard_pending_changes(page) -> None:" in source
    assert "page.has_pending_changes = lambda: _has_pending_changes(page)" in source
    assert "page.save_pending_changes = lambda: _save_pending_changes(page)" in source
    assert "page.discard_pending_changes = lambda: _discard_pending_changes(page)" in source
    assert "def _mark_comp_state_dirty(page) -> None:" in source
    assert "editTextChanged" in source


def test_phase14_team_health_reads_canonical_comp_state_before_legacy_fallback() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    health = source.split("def _refresh_health(page) -> None:", 1)[1].split(
        "def _refresh_shell(page) -> None:", 1
    )[0]
    assert 'state = getattr(page, "_comp_plan_state", None)' in health
    assert "CompPlanHealthService(DEFAULT_DATABASE).evaluate(state)" in health
    assert "health.conditional_required" in health
    assert "health.missing_required" in health
    assert "health.duplicate_effects" in health
    assert "health.open_player_seats" in health
    assert "Compatibility fallback for ad-hoc/unbound Comp sessions" in health
    assert health.index("CompPlanHealthService(DEFAULT_DATABASE).evaluate(state)") < health.index(
        "Compatibility fallback for ad-hoc/unbound Comp sessions"
    )


def test_phase14_team_health_surfaces_assignment_proof_and_duplicate_primary() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    health = source.split("def _refresh_health(page) -> None:", 1)[1].split(
        "def _refresh_shell(page) -> None:", 1
    )[0]
    assert 'review.state == "assigned_unproven"' in health
    assert '"Assigned to "' in health
    assert '" • source not proven"' in health
    assert "review.duplicate_primary" in health
    assert '"Multiple primary assignments: "' in health


def test_canonical_autofill_uses_comp_state_and_preserves_legacy_as_fallback() -> None:
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(
        encoding="utf-8"
    )

    assert 'state = getattr(page, "_comp_plan_state", None)' in source
    assert "CompPlanAutoFillService().apply(" in source
    assert "page._comp_plan_state = result.state" in source
    assert "result.skipped_existing" in source
    assert "Legacy/ad-hoc path remains temporarily unchanged in ownership." in source
    assert "support._set_candidate_for_row(page, row, candidate)" in source


def test_canonical_autofill_uses_primary_assignments_as_chair_local_constraints() -> None:
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(
        encoding="utf-8"
    )

    assert "assignment = str(chair.primary_assignment or \"\").strip()" in source
    assert "provider_resolution_by_slot[chair.seat_id] = assignment_resolution" in source
    assert "local_required = provider_resolution.provider_ids" in source
    assert "Explicit primary Assignments are stronger" in source


def test_comp_selected_chair_can_assign_any_gear_catalog_set_directly() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "def _catalog_set_names(page) -> tuple[str, ...]:" in source
    assert "GearSetRepository(DEFAULT_DATABASE).list_sets()" in source
    assert "def _add_planned_gear_set(page, set_name: str) -> None:" in source
    assert "def _remove_planned_gear_set(page, set_name: str) -> None:" in source
    assert 'heading = QLabel("ASSIGN GEAR")' in source
    assert 'picker.setProperty("compDirectGearPicker", True)' in source
    assert "picker.completer().setFilterMode(Qt.MatchFlag.MatchContains)" in source
    assert 'add = QPushButton("Add Set")' in source
    assert "Recommendations below are suggestions, not restrictions." in source
    assert "chair_state.with_changes(planned_gear_sets=(*existing, canonical))" in source
    assert "chair_state.is_locked(\"gear\")" in source


def test_comp_row_status_uses_canonical_planned_gear_not_only_legacy_picker_state() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    status = source.split("def _status_for_row", 1)[1].split(
        "def _group_rows", 1
    )[0]
    assert "chair_state = _state_chair_for_row(page, row)" in status
    assert "state_sets = tuple(chair_state.planned_gear_sets or ())" in status
    assert "planned_gear = bool(state_sets or manual_sets or applied_sets)" in status
