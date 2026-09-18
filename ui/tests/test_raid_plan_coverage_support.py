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
    assert "coverageRequested.connect" in route_source
    assert "_open_raid_plan_coverage" in route_source
    assert 'window.pages.get("console:7")' in route_source
    assert "coverage.set_raid_plan_scope(plan)" in route_source


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


def test_coverage_scope_never_falls_back_to_team_optimization_scope() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    assert 'self.scope_combo.addItem("Raid Plan", "raid_plan")' in source
    assert 'self.scope_combo.currentData() == "raid_plan"' in source
    assert "RaidPlanCoverageScopeService().compose" in source
    assert "scope.resolved_builds" in source
    assert "scope.primary_for(effect)" in source
    assert "scope.secondary_for(effect)" in source
    assert "set_team_scope" not in source


def test_raid_plan_coverage_renders_full_raid_effect_catalog() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    assert "GROUP_COVERAGE_NAMES" in source
    assert "UNIQUE_SUPPORT_SET_NAMES" in source
    assert "RAID_PLAN_COVERAGE_NAMES" in source
    assert "Powerful Assault" not in source  # catalog-driven, never hard-coded here
    assert "snapshot.conditional_providers.get(effect, [])" in source
    assert '"conditional": "Conditional"' in source


def test_raid_plan_coverage_action_emits_current_plan() -> None:
    source = Path("ui/raid_plan_coverage_page.py").read_text(encoding="utf-8")

    assert 'FoundryButton(\n            "Check Plan Coverage"' in source
    assert "plan = self.current_plan()" in source
    assert "self.coverageRequested.emit(plan)" in source


def test_raid_plan_coverage_overlays_reviewed_planned_set_evidence() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    assert "def _overlay_planned_gear(snapshot, scope)" in source
    assert "NonAbilityEffectProviderReferenceService(DEFAULT_DATABASE).gear()" in source
    assert "canonical_identity(name)" in source
    assert "for row in scope.planned_gear:" in source
    assert "planned-set evidence is therefore Conditional" in source
    assert "snapshot = _overlay_planned_gear(snapshot, scope)" in source
