from pathlib import Path


def test_raid_plan_route_preserves_coverage_aware_workspace() -> None:
    route_source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    assert '("Coverage", "console:7")' in route_source
    assert '("Comp Builder", "comp_builder")' in route_source
    assert '("Optimizer Adviser", "console:6")' in route_source
    assert "install_coverage_raid_plan_scope_support()" in route_source
    assert "bind_raid_plan_rotation_page" in route_source
    assert 'window.show_page(target)' in route_source


def test_coverage_support_is_installed_before_main_window_construction() -> None:
    support = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")
    bootstrap = Path("ui/application_team_optimization_bootstrap.py").read_text(encoding="utf-8")
    app = Path("app.py").read_text(encoding="utf-8")

    assert "install_coverage_raid_plan_scope_support()" in support
    assert "install_raid_engine_dashboard()" in bootstrap
    assert app.index("bootstrap_team_optimization_extensions()") < app.index(
        "from ui.main_window import MainWindow"
    )
    assert "MainWindow.build_ui =" not in support


def test_coverage_owns_saved_raid_plan_scope_selection() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    plan_item = source.split("def _plan_item_data", 1)[1].split(
        "def _selected_plan_id", 1
    )[0]
    assert 'return f"raid_plan:' in plan_item
    assert "str(plan_id" in plan_item
    assert ".strip()" in plan_item
    assert "RaidPlanRepository(get_user_database_path()).list_plans()" in source
    assert 'label = f"{plan.name} • {trial} • {difficulty}"' in source
    assert "combo.addItem(label, _plan_item_data(plan.plan_id))" in source
    assert 'combo.addItem("No saved Raid Plans", None)' in source
    assert "def _selected_plan_id(page) -> str:" in source
    assert "def _load_selected_plan_scope(page):" in source
    assert "RaidPlanCoverageScopeService().compose" in source
    assert "scope.resolved_builds" in source
    assert "RaidPlanCoverageAssignmentService" in source
    assert "assignment_service.review(" in source


def test_raid_plan_coverage_renders_full_raid_effect_catalog() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    assert "GROUP_COVERAGE_NAMES" in source
    assert "UNIQUE_SUPPORT_SET_NAMES" in source
    assert "RAID_PLAN_COVERAGE_NAMES" in source
    assert "Powerful Assault" not in source  # catalog-driven, never hard-coded here
    assert "snapshot.conditional_providers.get(effect, [])" in source
    assert 'review.state == "assigned_conditional"' in source
    assert "review.label" in source


def test_raid_plan_page_does_not_add_special_coverage_button() -> None:
    source = Path("ui/raid_plan_coverage_page.py").read_text(encoding="utf-8")

    assert "Check Plan Coverage" not in source
    assert "FoundryButton" not in source
    assert "coverageRequested = Signal(object)" in source


def test_raid_plan_coverage_overlays_reviewed_planned_set_evidence() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")
    shared = Path("services/raid_planned_gear_coverage_service.py").read_text(encoding="utf-8")

    assert "def _overlay_planned_gear(snapshot, scope)" in source
    assert "RaidPlannedGearCoverageService(DEFAULT_DATABASE).overlay(" in source
    assert "PlannedGearCoverageProvider(" in source
    assert "for row in scope.planned_gear" in source
    assert "Planned gear is raid-lead intent" in shared
    assert "conditional_providers" in shared
    assert 'prefix = "perfected "' in shared
    assert "snapshot = _overlay_planned_gear(snapshot, scope)" in source


def test_raid_plan_footer_keeps_only_primary_save_on_the_right() -> None:
    base = Path("ui/raid_plan_page.py").read_text(encoding="utf-8")
    action_block = base.split("actions.addStretch(1)", 1)[1].split(
        "root.addLayout(actions)", 1
    )[0]

    assert 'FoundryButton(\n            "Save",\n            role=ButtonRole.PRIMARY' in action_block
    assert "Build Research / Top Gear" not in action_block
    assert "Open Comp Maker" not in action_block
    assert "Open Coverage" not in action_block
    assert "Open Optimizer" not in action_block


def test_raid_plan_coverage_refresh_wrapper_rejects_non_plan_visible_scopes() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    assert "def refresh_with_raid_plan(self, *args, **kwargs):" in source
    assert 'page.scope_card.set_title("Coverage Reference Catalog")' in source
    assert 'data.startswith("roster_team:")' not in source
    assert "return _ORIGINAL_REFRESH(self, *args, **kwargs)" not in source


def test_raid_plan_coverage_reconciles_explicit_assignment_ownership() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    assert "RaidPlanCoverageAssignmentService" in source
    assert "assignment_service.review(" in source
    assert "review.label" in source
    assert '"assigned_supported"' in source
    assert '"assigned_conditional"' in source
    assert '"assigned_unproven"' in source
    assert "review.counts_as_planned_coverage" in source
    assert '"MISSING  {unassigned_gaps}' in source
    assert "DUPLICATE PRIMARY" in source


def test_coverage_needs_review_filter_accepts_assignment_aware_evidence_state() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert 'evidence not in {"available", "assigned_supported"}' in source


def test_coverage_scope_picker_contains_saved_raid_plans_only() -> None:
    scope = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")
    health = Path("ui/coverage_health_check_support.py").read_text(encoding="utf-8")
    base = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    refresh = scope.split("def _refresh_scope_plan_choices", 1)[1].split(
        "def _load_selected_plan_scope", 1
    )[0]
    enhance = health.split("def enhance_coverage_page", 1)[1]

    assert "combo.clear()" in refresh
    assert "_plan_item_data(plan.plan_id)" in refresh
    assert "Roster Team:" not in refresh
    assert "All Saved Builds" not in refresh
    assert "_sync_team_choices(page)" not in enhance
    assert "Coverage evaluates saved Raid Plans only." in base


def test_raid_plan_coverage_counts_planned_and_conditional_effects_as_present() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    assert "review.counts_as_planned_coverage" in source
    assert '"COVERED  {planned_present}' in source
    assert '"ASSIGNED • RUNTIME UNPROVEN  {assigned_unproven}' in source
    assert '"MISSING  {unassigned_gaps}' in source
    assert '"Planned: " + ", ".join(planned_primary)' in source
    assert "Assigned provider counts as planned coverage" in source


def test_coverage_assignment_service_exposes_binary_planning_state() -> None:
    source = Path("services/raid_plan_coverage_assignment_service.py").read_text(
        encoding="utf-8"
    )

    assert "def coverage_state(self) -> str:" in source
    assert 'return "covered" if self.state != "gap" else "missing"' in source
    assert 'label = "Covered • Conditional"' in source
    assert 'label = "Covered • Planned"' in source
    assert 'label = "Missing • No provider"' in source


def test_raid_plan_coverage_includes_explicit_planned_skill_and_class_evidence() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")
    scope = Path("services/raid_plan_coverage_scope_service.py").read_text(encoding="utf-8")
    planned = Path("services/raid_planned_skill_coverage_service.py").read_text(encoding="utf-8")

    assert "RaidPlannedSkillCoverageService(DEFAULT_DATABASE).overlay(" in source
    assert "PlannedSkillCoverageProvider(" in source
    assert "for row in scope.planned_skills" in source
    assert "snapshot = _overlay_planned_skills(snapshot, scope)" in source
    assert "planned_skill_chairs = len(scope.planned_skills)" in source

    assert "class RaidPlanPlannedSkills:" in scope
    assert "planned_skills: tuple[RaidPlanPlannedSkills, ...]" in scope
    assert "member.planned_skills" in scope
    assert "eso_class=member.eso_class" in scope

    allowed = planned.split("_ALLOWED_TARGETS =", 1)[1].split("}", 1)[0]
    assert "    SupportTargetType.SELF,\n" not in allowed
    assert "planned_skill_lines" in planned
    assert "passive.skill_line" in planned
    assert "class alone" not in planned.casefold()


def test_coverage_can_display_generic_assignment_source_annotation() -> None:
    model = Path("models/raid_plan.py").read_text(encoding="utf-8")
    assignments = Path("ui/city_raid_assignments_page.py").read_text(encoding="utf-8")
    scope = Path("services/raid_plan_coverage_scope_service.py").read_text(encoding="utf-8")
    coverage = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    assert "assignment_source: str | None = None" in model
    assert 'form.addRow("Source", self.selected_assignment_source)' in assignments
    assert "assignment_source=assignment_source or None" in assignments
    assert "_assignment_source_by_seat" in assignments
    assert "def source_note_for(" in scope
    assert "member.assignment_source" in scope
    assert 'f"{provider} • {scope.source_note_for(effect, provider)}"' in coverage


def test_coverage_refresh_preserves_selected_plan_and_provider_persistence_contract() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")
    page_source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert "preferred_plan_id" in source
    assert "_coverage_selected_plan_id" in source
    assert "saved provider failed Coverage read-back verification" in page_source
    assert "removed provider survived Coverage read-back verification" in page_source


def test_coverage_exposes_explicit_verified_save_action() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert 'QPushButton("Save Coverage")' in source
    assert "self.save_coverage_button.clicked.connect(self._save_coverage)" in source
    assert "def _save_coverage(self) -> None:" in source
    assert "Coverage providers changed during persistence verification" in source
