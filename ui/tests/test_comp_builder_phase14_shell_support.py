from pathlib import Path


def test_phase14_comp_builder_visible_shell_matches_approved_work_chat_contract() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert '"Plan the team. Fill the gaps. Clear the content."' in source
    assert 'matrix.set_title("Recommended Team Plan")' in source
    assert 'details.set_title("Why This Plan")' in source
    assert 'coverage.set_title("Team Health")' in source
    assert 'generate.setText("Auto-Fill Builds")' in source
    assert 'load_team.setText("Load Players")' in source
    assert 'save.setText("Save Plan")' in source
    assert 'send.setText("Send to Raid Plan")' in source


def test_phase14_comp_builder_brief_owns_required_controls() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert '_context_box("TRIAL", page.goal_combo)' in source
    assert '_context_box("DIFFICULTY", page.difficulty_combo)' in source
    assert '_context_box("PLAN NAME", page.plan_name_input)' in source
    assert '_context_box("PLAN STYLE", style)' in source
    assert 'for size in (4, 12):' in source


def test_phase14_comp_builder_plan_table_is_player_first_and_role_grouped() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert '"PLAYER"' in source
    assert '"ROLE / CLASS"' in source
    assert '"RECOMMENDED BUILD (SETS)"' in source
    assert '"KEY RESPONSIBILITY"' in source
    assert '"STATUS"' in source
    assert '("tank", "TANKS")' in source
    assert '("healer", "HEALERS")' in source
    assert '("damage", "DAMAGE")' in source


def test_phase14_comp_builder_why_panel_is_source_backed() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "candidate_support._chair_candidates(page, row)" in source
    assert "score_reasons" in source
    assert '"ALTERNATIVES"' in source
    assert "_candidate_source(candidate)" in source


def test_phase14_comp_builder_health_summarizes_coverage_duplicates_and_recruits() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert '("COVERED",' in source
    assert '("MISSING",' in source
    assert '("DUPLICATE",' in source
    assert '("RECRUIT NEED",' in source
    assert "CompPlanHealthService" in source
    assert "health = _cached_comp_health(page, state)" in source
    assert "health.planned_or_static_required_count" in source


def test_phase14_comp_builder_shell_installs_after_legacy_extensions() -> None:
    bootstrap = Path("ui/application_team_optimization_bootstrap.py").read_text(encoding="utf-8")

    assert "install_comp_builder_phase14_shell()" in bootstrap
    assert bootstrap.index("install_comp_builder_polish()") < bootstrap.index(
        "install_comp_builder_phase14_shell()"
    )
    assert bootstrap.index("install_coverage_group_effect_catalog_support()") < bootstrap.index(
        "install_comp_builder_phase14_shell()"
    )


def test_phase14_why_plan_top_matches_two_set_recommendation_card() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert 'setProperty("confidenceBadge", True)' in source
    assert 'setProperty("compRecommendedSetName", True)' in source
    assert 'page.comp_phase14_set_plus = QLabel("+")' in source
    assert 'setProperty("compRecommendedSetCount", True)' in source
    assert 'page.comp_phase14_role_footer' in source
    assert 'f"{selected_class}  •  {role}"' in source


def test_phase14_four_player_shell_reasserts_owned_geometry() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert 'card_minimum = 520' in source
    assert 'table_minimum = 360' in source
    assert 'card_maximum = 640' in source
    assert 'table_maximum = 600' in source


def test_phase14_twelve_player_plan_expands_and_scrolls_when_needed() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert 'card_minimum = 620' in source
    assert 'table_minimum = 540' in source
    assert 'card_maximum = MAX_WIDGET_HEIGHT' in source
    assert 'table_maximum = MAX_WIDGET_HEIGHT' in source
    assert 'Qt.ScrollBarPolicy.ScrollBarAsNeeded' in source
    assert 'QAbstractItemView.ScrollMode.ScrollPerPixel' in source
    assert 'root.addLayout(middle, 1)' in source
    assert 'middle.setAlignment(Qt.AlignmentFlag.AlignTop)' not in source


def test_phase14_team_health_uses_mockup_status_indicators() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert '("COVERED", "✓", "covered"' in source
    assert '("MISSING", "×", "missing"' in source
    assert '("DUPLICATE", "!", "duplicate"' in source
    assert '("RECRUIT NEED", "i", "recruit"' in source
    assert 'setProperty("compHealthIndicator", True)' in source


def test_phase14_why_refresh_initializes_set_state_in_every_branch() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert 'page.comp_phase14_set_one.setText("No recommendation")' in source
    assert 'page.comp_phase14_set_two.setText("")' in source
    assert 'page.comp_phase14_set_plus.setVisible(False)' in source
    assert 'page.comp_phase14_set_one.setText("No eligible build")' in source
    assert 'set_one, set_two = _candidate_sets(preferred)' in source
    assert 'set_two if set_two else "No second set resolved"' in source

    candidate_assignment = source.index("set_one, set_two = _candidate_sets(preferred)")
    assert source.find("if not set_two:", 0, candidate_assignment) == -1


def test_phase14_why_choices_apply_to_selected_chair() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert 'setProperty("compCandidateChoice", True)' in source
    assert "CompCandidateAdviserService(DEFAULT_DATABASE).apply(" in source
    assert "page._comp_plan_state = updated" in source
    assert "page.comp_phase14_recommendation_frame._comp_candidate = preferred" in source
    assert "page.comp_phase14_alt_one_frame._comp_candidate = alt_one" in source
    assert "page.comp_phase14_alt_two_frame._comp_candidate = alt_two" in source
    assert "_refresh_shell(page)" in source


def test_phase14_why_choices_use_five_piece_projection_and_confidence_levels() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert 'getattr(candidate, "five_piece_sets", ())' in source
    assert '"No five-piece sets resolved"' in source
    assert '("high", "High confidence"' in source
    assert '("medium", "Medium confidence"' in source
    assert '("low", "Low confidence"' in source
    assert '("review", "Needs review"' in source


def test_phase14_comp_builder_save_updates_or_creates_raid_plan_not_template_file() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "def _save_to_originating_raid_plan(page)" in source
    assert "CompBuildPersistenceService(get_data_dir())" in source
    assert '"_persist_comp_plan_state_to_raid_plan"' in source
    assert "candidate_support.save_generated_plan(page)" not in source
    assert '"_persist_generated_comp_plan_to_raid_plan"' not in source
    assert "page._raid_plan_origin_id = plan.plan_id" in source
    assert 'refresh_names = getattr(page, "_refresh_raid_plan_name_choices", None)' in source
    assert "Open it from Raid Plan first" not in source
    assert "save.clicked.disconnect()" in source


def test_phase14_return_visit_reasserts_geometry_and_visible_scrollbar() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")
    main = Path("ui/main_window.py").read_text(encoding="utf-8")

    assert "def refresh_phase14_presentation(page)" in source
    assert "Qt.ScrollBarPolicy.ScrollBarAlwaysOn" in source
    assert 'if page_name == "comp_builder":' in main
    assert "refresh_phase14_presentation(comp)" in main


def test_phase14_candidate_choices_remain_stable_after_selecting_alternative() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "preferred = candidates[0] if candidates else applied" in source
    assert "item.candidate_id != preferred.candidate_id" in source
    assert "selected_id =" in source
    assert "alt_one.candidate_id == selected_id" in source


def test_phase14_final_shell_reapplies_recruit_class_constraints() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "from ui.comp_builder_roster_intake_support import _reapply_class_constraints" in source
    assert "_reapply_class_constraints(self)" in source
    assert "def _render_slots_with_phase14_shell(self, slots)" in source
    assert "def apply_roster_context_with_shell(self, *args, **kwargs)" in source


def test_phase14_save_persists_explicit_canonical_state_without_materializing_visible_suggestions() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    save_block = source.split("def _save_to_originating_raid_plan(page)", 1)[1].split(
        "def _has_pending_changes", 1
    )[0]
    assert "_sync_context_into_comp_state(page)" in save_block
    assert "CompBuildPersistenceService(get_data_dir())" in save_block
    assert 'getattr(window, "_persist_comp_plan_state_to_raid_plan", None)' in save_block
    assert "_materialize_visible_recommendations(page)" not in save_block
    assert "save_generated_plan(page)" not in save_block


def test_comp_to_raid_plan_bridge_verifies_exact_repository_round_trip() -> None:
    source = Path("ui/main_window.py").read_text(encoding="utf-8")

    assert "persisted = raid_plans.plan_repository.get(plan.plan_id)" in source
    assert "persisted is None or persisted != plan" in source
    assert "the app is refusing to report success" in source
    assert "raid_plans.apply_plan(persisted)" in source


def test_raid_plan_class_map_is_authoritative_in_visible_comp_shell() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")
    handoff = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")
    intake = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert '_raid_plan_class_by_seat' in handoff
    assert 'apply_raid_plan_class_constraints(comp, class_by_seat)' in handoff
    assert 'def apply_raid_plan_class_constraints(page, class_by_seat' in intake
    assert 'page._comp_class_constraint_by_slot = dict(cleaned)' in intake
    assert 'raid_classes = dict(getattr(page, "_raid_plan_class_by_seat", {}) or {})' in source
    assert 'apply_raid_plan_class_constraints(page, raid_classes)' in source


def test_raid_plan_handoff_replaces_stale_comp_class_state_before_render() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    map_index = source.index("comp._raid_plan_class_by_seat = dict(class_by_seat)")
    apply_index = source.index("comp.apply_roster_team_context(")
    refresh_index = source.index("refresh_phase14_presentation(comp)")
    assert map_index < apply_index < refresh_index
    assert "comp._comp_class_constraint_by_slot = dict(class_by_seat)" in source


def test_phase14_comp_builder_can_pick_individual_sets_per_chair() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "def _toggle_manual_set(page, set_name: str)" in source
    assert '"_comp_manual_gear_sets_by_slot"' in source
    assert 'heading = QLabel("ASSIGN GEAR")' in source
    assert 'picker.setPlaceholderText("Search all gear sets…")' in source
    assert "def _add_planned_gear_set(page, set_name: str) -> None:" in source
    assert "def _remove_planned_gear_set(page, set_name: str) -> None:" in source
    assert "lambda *_: _add_planned_gear_set(page, picker.text())" in source
    assert "_refresh_manual_set_picker(page, candidates)" in source
    assert '" + ".join(state_sets)' in source
    assert '" + ".join(manual_sets)' in source


def test_raid_plan_reopens_comp_with_planned_manual_sets() -> None:
    handoff = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    assert "planned_sets_by_seat = {" in handoff
    assert 'getattr(member, "planned_gear_sets", ())' in handoff
    assert "comp._comp_manual_gear_sets_by_slot = dict(planned_sets_by_seat)" in handoff


def test_raid_plan_handoff_copies_class_directly_into_comp_selector() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    assert "for comp_row in range(comp.matrix_table.rowCount()):" in source
    assert 'slot_name = str(comp._cell_text(comp_row, 0) or "").strip()' in source
    assert 'wanted_class = str(class_by_seat.get(slot_name, "") or "").strip()' in source
    assert "selector = comp.matrix_table.cellWidget(comp_row, 2)" in source
    assert "selector.setCurrentIndex(match)" in source


def test_raid_plan_class_only_recruit_chair_is_handed_to_comp_maker() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    assert 'or "Recruit"' in source
    assert 'str(getattr(member, "eso_class", "") or "").strip()' in source
    assert 'tuple(getattr(member, "planned_gear_sets", ()) or ())' in source
    assert '"Tank 1", "Tank 2", "Healer 1", "Healer 2"' in source


def test_recruit_with_applied_or_manual_sets_is_not_labeled_needs_gear() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert 'planned_gear = bool(state_sets or manual_sets or applied_sets)' in source
    assert 'return "Planned gear" if planned_gear else "Needs gear"' in source
    assert 'if applied or manual_sets:' in source


def test_comp_maker_plan_name_is_editable_saved_raid_plan_picker() -> None:
    source = Path("ui/comp_builder_page.py").read_text(encoding="utf-8")

    assert "class EditablePlanNameCombo(QComboBox):" in source
    assert "self.setEditable(True)" in source
    assert "def text(self) -> str:" in source
    assert "def setText(self, value: object) -> None:" in source
    assert "self.raid_plan_repository = RaidPlanRepository" in source
    assert "self._refresh_raid_plan_name_choices()" in source
    assert "self.plan_name_input.activated.connect(self._raid_plan_name_selected)" in source
    assert "group_size=self._raid_plan_group_size(plan)" in source
    assert "def _raid_plan_group_size(plan) -> int:" in source
    assert "self._raid_plan_origin_id = plan.plan_id" in source


def test_comp_maker_navigation_refreshes_plan_picker_without_route_based_binding() -> None:
    source = Path("ui/main_window.py").read_text(encoding="utf-8")

    block = source.split('if page_name == "comp_builder":', 1)[1].split(
        'if page_name == "console:6":', 1
    )[0]
    assert '_refresh_raid_plan_name_choices' in block
    assert "_bind_plan_comp_builder" not in block
    assert "refresh_phase14_presentation(comp)" in block


def test_new_comp_plan_repairs_comp_build_provenance_after_first_raid_plan_binding() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    save_block = source.split("def _save_to_originating_raid_plan(page)", 1)[1].split(
        "def _has_pending_changes", 1
    )[0]
    assert "was_unbound = not state.is_raid_plan_bound" in save_block
    assert "build_service = CompBuildPersistenceService(get_data_dir())" in save_block
    assert "if was_unbound and plan is not None:" in save_block
    assert "rebound_result = build_service.persist(page._comp_plan_state)" in save_block
    assert "rebound_result.state.mark_saved()" in save_block


def test_comp_maker_plan_picker_guards_unsaved_state_before_switching_saved_plans() -> None:
    source = Path("ui/comp_builder_page.py").read_text(encoding="utf-8")

    assert "def _confirm_raid_plan_switch(self, target_plan_id: str) -> bool:" in source
    assert 'box.setWindowTitle("Unsaved Comp Plan Changes")' in source
    assert "QMessageBox.StandardButton.Save" in source
    assert "QMessageBox.StandardButton.Discard" in source
    assert "QMessageBox.StandardButton.Cancel" in source
    assert 'save_pending = getattr(self, "save_pending_changes", None)' in source
    assert 'discard_pending = getattr(self, "discard_pending_changes", None)' in source
    assert "self._restore_raid_plan_picker_to_current_state()" in source

    load_block = source.split("def _raid_plan_name_selected(self, index: int) -> None:", 1)[1].split(
        "    def _build_ui", 1
    )[0]
    assert "if not self._confirm_raid_plan_switch(str(plan_id)):" in load_block
    assert load_block.index("_confirm_raid_plan_switch") < load_block.index(
        "self.raid_plan_repository.get"
    )


def test_phase14_comp_runtime_has_one_canonical_persistence_path() -> None:
    page = Path("ui/comp_builder_page.py").read_text(encoding="utf-8")
    candidates = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")
    main = Path("ui/main_window.py").read_text(encoding="utf-8")
    shell = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "GeneratedRosterDraftService" not in page
    assert "GeneratedRosterDraftSlot" not in page
    assert "self.plan_service =" not in page
    assert "self.user_template_path =" not in page

    assert "GeneratedRosterDraftSlot" not in candidates
    assert "def save_generated_plan(" not in candidates
    assert "page.plan_service.save_plan(" not in candidates

    assert "def _persist_generated_comp_plan_to_raid_plan(" not in main
    assert "def _show_generated_roster_plan(" not in main
    assert "GeneratedRosterDraftService" not in main
    assert "rosterPlanSent.connect(self._show_generated_roster_plan)" not in main

    assert "CompBuildPersistenceService(get_data_dir())" in shell
    assert '"_persist_comp_plan_state_to_raid_plan"' in shell
