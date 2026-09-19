from pathlib import Path


def test_raid_plan_route_preserves_coverage_aware_workspace() -> None:
    route_source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    assert '("Coverage", "console:7")' in route_source
    assert '("Comp Builder", "comp_builder")' in route_source
    assert '("Optimizer Adviser", "console:6")' in route_source
    assert "install_coverage_raid_plan_scope_support()" in route_source
    assert "install_raid_plan_optimizer_adviser_support()" in route_source
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

    assert 'return f"raid_plan:{str(plan_id or '').strip()}"' in source
    assert "RaidPlanRepository(get_data_dir() / \"raid_plans.json\").list_plans()" in source
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

    assert "def _overlay_planned_gear(snapshot, scope)" in source
    assert "NonAbilityEffectProviderReferenceService(DEFAULT_DATABASE).gear()" in source
    assert "canonical_identity(name)" in source
    assert "for row in scope.planned_gear:" in source
    assert "planned-set evidence is therefore Conditional" in source
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
    assert 'self.scope_card.set_title("Choose a saved Raid Plan")' in source
    assert "Coverage evaluates one saved trial plan at a time." in source
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
    assert '"gap"' in source
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
