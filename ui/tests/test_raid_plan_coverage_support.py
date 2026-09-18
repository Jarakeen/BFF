from pathlib import Path


def test_raid_plan_route_preserves_coverage_aware_workspace() -> None:
    route_source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")
    adviser_source = Path("ui/raid_plan_adviser_page.py").read_text(encoding="utf-8")
    rotation_source = Path("ui/raid_plan_rotation_page.py").read_text(encoding="utf-8")

    assert "RaidPlanAdviserPage" in route_source
    assert "from ui.raid_plan_rotation_page import RaidPlanRotationPage" in adviser_source
    assert "class RaidPlanAdviserPage(RaidPlanRotationPage):" in adviser_source
    assert "from ui.raid_plan_coverage_page import RaidPlanCoveragePage" in rotation_source
    assert "class RaidPlanRotationPage(RaidPlanCoveragePage):" in rotation_source
    assert '("Coverage", "console:7")' in route_source
    assert '("Comp Builder", "comp_builder")' in route_source
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
    assert 'combo.addItem(f"Raid Plan: {plan.name}", _plan_item_data(plan.plan_id))' in source
    assert "def _selected_plan_id(page) -> str:" in source
    assert "def _load_selected_plan_scope(page):" in source
    assert "RaidPlanCoverageScopeService().compose" in source
    assert "scope.resolved_builds" in source
    assert "scope.primary_for(effect)" in source
    assert "scope.secondary_for(effect)" in source


def test_raid_plan_coverage_renders_full_raid_effect_catalog() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    assert "GROUP_COVERAGE_NAMES" in source
    assert "UNIQUE_SUPPORT_SET_NAMES" in source
    assert "RAID_PLAN_COVERAGE_NAMES" in source
    assert "Powerful Assault" not in source  # catalog-driven, never hard-coded here
    assert "snapshot.conditional_providers.get(effect, [])" in source
    assert '"conditional": "Conditional"' in source


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


def test_lower_open_coverage_is_plain_navigation() -> None:
    base = Path("ui/raid_plan_page.py").read_text(encoding="utf-8")
    coverage_page = Path("ui/raid_plan_coverage_page.py").read_text(encoding="utf-8")

    assert "self.open_coverage_button.clicked.connect(self._open_coverage)" in base
    assert 'self.pageRequested.emit("console:7")' in base
    assert "def _open_coverage(self, *_args) -> None:" not in coverage_page
