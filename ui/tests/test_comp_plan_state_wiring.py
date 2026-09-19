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


def test_comp_plan_name_picker_uses_canonical_state_and_bulk_five_piece_restore() -> None:
    source = Path("ui/comp_builder_page.py").read_text(encoding="utf-8")

    helper = source.split("def _planned_five_piece_sets_by_seat", 1)[1].split(
        "def _refresh_raid_plan_name_choices", 1
    )[0]
    selected = source.split("def _raid_plan_name_selected", 1)[1].split(
        "def _build_ui", 1
    )[0]
    assert "CompPlanStateService.from_raid_plan(" in selected
    assert "planned_five_piece_sets = self._planned_five_piece_sets_by_seat(plan)" in selected
    assert "self._comp_manual_gear_sets_by_slot = dict(planned_five_piece_sets)" in selected
    assert "_five_piece_set_names(" in helper
    assert "all_names" in helper
    assert "[:2]" in helper
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
    assert "health = _cached_comp_health(page, state)" in health
    assert "health.conditional_required" in health
    assert "health.missing_required" in health
    assert "health.duplicate_effects" in health
    assert "health.open_player_seats" in health
    assert "Compatibility fallback only for unsupported state-less legacy sessions" in health
    assert health.index("health = _cached_comp_health(page, state)") < health.index(
        "Compatibility fallback only for unsupported state-less legacy sessions"
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


def test_canonical_autofill_requires_comp_state_and_has_no_state_less_fallback() -> None:
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(
        encoding="utf-8"
    )

    assert 'state = getattr(page, "_comp_plan_state", None)' in source
    assert 'if state is None:' in source
    assert "state-less legacy mode" in source
    assert "CompPlanAutoFillService().apply(" in source
    assert "page._comp_plan_state = result.state" in source
    assert "result.skipped_existing" in source
    assert "Legacy/ad-hoc path remains temporarily unchanged in ownership." not in source
    assert "support._set_candidate_for_row(page, row, candidate)" not in source


def test_canonical_autofill_tracks_saved_players_from_comp_state_not_only_mirror() -> None:
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(
        encoding="utf-8"
    )

    assert "canonical_saved_players = {" in source
    assert 'chair.build_source_kind' in source
    assert 'chair.build_source_name' in source
    assert "canonical_saved_players | set(support._used_saved_players(page))" in source


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
    assert "def _gear_catalog_completer(page) -> QCompleter:" in source
    assert "QStringListModel(list(_catalog_set_names(page)), page)" in source
    assert "completer.setFilterMode(Qt.MatchFlag.MatchContains)" in source
    assert "picker.setCompleter(_gear_catalog_completer(page))" in source
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


def test_comp_raid_plan_switch_suppresses_refresh_storms_during_hydration() -> None:
    page = Path("ui/comp_builder_page.py").read_text(encoding="utf-8")
    shell = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")
    intake = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    selected = page.split("def _raid_plan_name_selected", 1)[1].split(
        "def _build_ui", 1
    )[0]
    assert "self.goal_combo.blockSignals(True)" in selected
    assert "self.difficulty_combo.blockSignals(True)" in selected
    assert "self._comp_loading_plan = True" in selected
    assert "finally:" in selected
    assert "self._comp_loading_plan = False" in selected

    refresh_wrapper = shell.split("def refresh_candidates_with_shell", 1)[1].split(
        "candidate_support._refresh_candidates =", 1
    )[0]
    assert 'getattr(page, "_comp_loading_plan", False)' in refresh_wrapper
    assert "return" in refresh_wrapper

    render_wrapper = shell.split("def _render_slots_with_phase14_shell", 1)[1].split(
        "def install()", 1
    )[0]
    assert 'not getattr(self, "_comp_loading_plan", False)' in render_wrapper

    setter = intake.split("def _set_class_constraint", 1)[1].split(
        "def _reapply_class_constraints", 1
    )[0]
    assert "class_combo.blockSignals(True)" in setter
    assert "class_combo.blockSignals(False)" in setter


def test_bound_comp_plan_table_does_not_recompute_candidates_for_every_row() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    render = source.split("def _refresh_plan_table(page) -> None:", 1)[1].split(
        "def _selected_backend_row", 1
    )[0]
    assert 'chair_state = _state_chair_for_row(page, backend_row)' in render
    assert 'getattr(page, "_comp_applied_candidates", {}).get(slot_name)' in render
    assert "else _candidate_for_row(page, backend_row)" in render
    assert render.index('chair_state = _state_chair_for_row(page, backend_row)') < render.index(
        "else _candidate_for_row(page, backend_row)"
    )


def test_direct_gear_picker_reuses_one_catalog_completion_model() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    helper = source.split("def _gear_catalog_completer", 1)[1].split(
        "def _canonical_catalog_set_name", 1
    )[0]
    picker = source.split("def _refresh_manual_set_picker", 1)[1].split(
        "def _responsibility_for_row", 1
    )[0]
    assert 'getattr(page, "_comp_gear_catalog_completer", None)' in helper
    assert "QStringListModel(list(_catalog_set_names(page)), page)" in helper
    assert "page._comp_gear_catalog_completer = completer" in helper
    assert "picker = QLineEdit()" in picker
    assert "picker.setCompleter(_gear_catalog_completer(page))" in picker
    assert "picker.addItems(" not in picker


def test_comp_raid_plan_group_size_uses_canonical_seats_not_named_player_count() -> None:
    source = Path("ui/comp_builder_page.py").read_text(encoding="utf-8")

    helper = source.split("def _raid_plan_group_size(plan)", 1)[1].split(
        "def _planned_five_piece_sets_by_seat", 1
    )[0]
    selected = source.split("def _raid_plan_name_selected", 1)[1].split(
        "def _build_ui", 1
    )[0]
    assert '"tank-2"' in helper
    assert '"healer-2"' in helper
    assert 'f"dd-{index}" for index in range(3, 9)' in helper
    assert '"tank-1", "healer-1", "dd-1", "dd-2"' in helper
    assert "group_size=self._raid_plan_group_size(plan)" in selected
    assert "group_size=12" not in selected


def test_selected_chair_adviser_renders_canonical_group_impact_and_applies_same_proposal() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    why = source.split("def _refresh_why(page) -> None:", 1)[1].split(
        "def _health_tile", 1
    )[0]
    apply = source.split("def _apply_choice(page, frame: QFrame) -> None:", 1)[1].split(
        "def _refresh_why", 1
    )[0]

    assert "_cached_candidate_proposal(" in why
    assert "proposal.gained_planned_required" in why
    assert "proposal.assignment_proof_improved" in why
    assert "proposal.gained_effect_evidence" in why
    assert "proposal.lost_planned_required" in why
    assert "proposal.assignment_proof_regressed" in why
    assert "proposal.duplicates_added" in why
    assert "proposal.duplicates_removed" in why
    assert "proposal.blocked_fields" in why

    assert "CompCandidateAdviserService(DEFAULT_DATABASE).apply(" in apply
    assert "proposal=cached_proposal" in apply
    assert "page._comp_plan_state = updated" in apply
    assert "proposal.blocked_fields" in apply
    assert "candidate_support._set_candidate_for_row" in apply  # legacy-only fallback


def test_comp_shell_memoizes_team_health_and_selected_candidate_proposals() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")
    adviser = Path("services/comp_candidate_adviser_service.py").read_text(encoding="utf-8")

    assert "def _cached_comp_health(page, state):" in source
    assert 'getattr(page, "_comp_phase14_health_cache", None)' in source
    assert "if cached_state == state:" in source
    assert "def _cached_candidate_proposal(page, state, chair, candidate):" in source
    assert 'getattr(page, "_comp_phase14_proposal_cache", None)' in source
    assert "current_health=_cached_comp_health(page, state)" in source

    health = source.split("def _refresh_health(page) -> None:", 1)[1].split(
        "def _refresh_shell(page) -> None:", 1
    )[0]
    assert "health = _cached_comp_health(page, state)" in health
    assert "CompPlanHealthService(DEFAULT_DATABASE).evaluate(state)" not in health

    assert "current_health: CompPlanHealth | None = None" in adviser
    assert "current_health = current_health or self.health.evaluate(state)" in adviser
    assert "proposal: CompCandidateProposal | None = None" in adviser


def test_selected_chair_candidate_discovery_is_cached_by_relevant_inputs() -> None:
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    chair = source.split("def _chair_candidates(page, row: int)", 1)[1].split(
        "def _saved_player_key", 1
    )[0]
    assert 'cache = getattr(page, "_comp_chair_candidate_cache", None)' in chair
    assert "observed_gear" in chair
    assert "observed_skills" in chair
    assert "member_key" in chair
    assert "preferred_class" in chair
    assert "goal" in chair
    assert "if cache_key in cache:" in chair
    assert "if len(cache) >= 64:" in chair


def test_selected_chair_adviser_can_seed_only_empty_planned_skills() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")
    service = Path("services/comp_plan_skill_seed_service.py").read_text(encoding="utf-8")

    assert 'QPushButton("Fill Empty Skills")' in source
    assert "def _fill_empty_skills(page) -> None:" in source
    assert "CompPlanSkillSeedService().apply(" in source
    assert "page._comp_plan_state = updated" in source
    assert "Existing skills were not replaced." in source
    assert "chair.planned_skills" in source
    assert 'chair.is_locked("skills")' in service
    assert "elif chair.planned_skills:" in service
    assert 'candidate.source_kind == "reference_template"' in service
    assert "not candidate.complete_build" in service


def test_phase14_comp_direct_open_always_has_canonical_state() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "def _ensure_default_comp_state(page) -> None:" in source
    ensure = source.split("def _ensure_default_comp_state(page) -> None:", 1)[1].split(
        "def _mark_comp_state_dirty", 1
    )[0]
    assert "CompPlanStateService.new_unbound(" in ensure
    assert "page._comp_plan_state = state" in ensure
    install = source.split("def _install_shell(page) -> None:", 1)[1].split(
        "def _init_with_phase14_shell", 1
    )[0]
    assert "_ensure_default_comp_state(page)" in install


def test_unbound_comp_save_finalizes_without_generated_draft() -> None:
    main = Path("ui/main_window.py").read_text(encoding="utf-8")
    shell = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    direct = main.split("def _persist_comp_plan_state_to_raid_plan", 1)[1].split(
        "def _persist_generated_comp_plan_to_raid_plan", 1
    )[0]
    assert "if state.is_raid_plan_bound:" in direct
    assert "CompPlanStateService.to_new_raid_plan(" in direct
    assert "CompPlanStateService.unique_raid_plan_id(" in direct

    save = shell.split("def _save_to_originating_raid_plan", 1)[1].split(
        "def _has_pending_changes", 1
    )[0]
    assert "save_generated_plan" not in save
    assert "_persist_generated_comp_plan_to_raid_plan" not in save
    assert "_persist_comp_plan_state_to_raid_plan" in save


def test_send_to_raid_plan_uses_same_canonical_save_path() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    helper = source.split("def _send_to_raid_plan(page) -> bool:", 1)[1].split(
        "def _save_pending_changes", 1
    )[0]
    health = source.split("def _build_health(page, card: FoundryCard) -> None:", 1)[1].split(
        "def _install_shell", 1
    )[0]

    assert "_save_to_originating_raid_plan(page)" in helper
    assert 'show_page("raid_plans")' in helper
    assert "send.clicked.disconnect()" in health
    assert "send.clicked.connect(lambda *_: _send_to_raid_plan(page))" in health


def test_bound_plan_hydration_finishes_clean_on_both_entry_routes() -> None:
    page = Path("ui/comp_builder_page.py").read_text(encoding="utf-8")
    dashboard = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    selected = page.split("def _raid_plan_name_selected", 1)[1].split(
        "def _build_ui", 1
    )[0]
    assert "self._comp_plan_state = self._comp_plan_state.mark_saved()" in selected

    bind = dashboard.split("def _bind_plan_comp_builder", 1)[1].split(
        "def _open_plan_comp_builder", 1
    )[0]
    assert "comp._comp_plan_state = comp._comp_plan_state.mark_saved()" in bind
    assert "CompBuilderPage._raid_plan_group_size(plan)" in bind
    assert "group_size=12" not in bind


def test_unbound_discard_restores_planning_baseline() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    discard = source.split("def _discard_pending_changes(page) -> None:", 1)[1].split(
        "def _build_health", 1
    )[0]
    assert "not state.is_raid_plan_bound" in discard
    assert 'getattr(page, "_comp_unbound_baseline_state", None)' in discard
    assert "page._comp_plan_state = baseline" in discard


def test_fallback_candidate_apply_does_not_let_build_lock_block_other_fields() -> None:
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    changes = source.split("def _candidate_state_changes", 1)[1].split(
        "def _refresh_candidates", 1
    )[0]
    apply = source.split("def _set_candidate_for_row", 1)[1].split(
        "def _apply_top_candidate", 1
    )[0]

    assert 'if not chair.is_locked("build"):' in changes
    assert 'if not chair.is_locked("gear"):' in changes
    assert 'if not chair.is_locked("class")' in changes
    assert 'if not chair.is_locked("mundus"):' in changes
    assert 'if chair is not None and chair.is_locked("build"):' not in apply
    assert "_candidate_state_changes(chair, candidate)" in apply
    assert "_comp_last_candidate_apply_blocked_fields" in apply


def test_roster_intake_is_state_first_then_renders_accepted_values() -> None:
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    apply = source.split("def apply_roster_team_context", 1)[1].split(
        "def _send_roster_team_to_comp", 1
    )[0]
    sync_index = apply.index("_sync_comp_state_from_matches(page, matched, assignments)")
    render_index = apply.index("_set_player(page, row, member, assignments.get(member_id))")
    assert sync_index < render_index

    setter = source.split("def _set_player", 1)[1].split("def _clear_player_rows", 1)[0]
    assert "chair = _state_chair_for_row(page, row)" in setter
    assert "chair.player_name" in setter
    assert "chair.character_name" in setter
    assert "chair.eso_class" in setter
    assert "chair.primary_assignment" in setter
