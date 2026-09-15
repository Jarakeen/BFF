from pathlib import Path


def test_raid_plan_adviser_page_extends_rotation_aware_workspace() -> None:
    source = Path("ui/raid_plan_adviser_page.py").read_text(encoding="utf-8")

    assert "from ui.raid_plan_rotation_page import RaidPlanRotationPage" in source
    assert "class RaidPlanAdviserPage(RaidPlanRotationPage):" in source
    assert "adviserRequested = Signal(object)" in source
    assert 'button.setText("Open Adviser")' in source
    assert "self.adviserRequested.emit(self.current_plan())" in source


def test_raid_engine_routes_current_plan_into_existing_optimization_workspace() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    assert "from ui.raid_plan_adviser_page import RaidPlanAdviserPage" in source
    assert "raid_plans = RaidPlanAdviserPage()" in source
    assert "adviserRequested.connect" in source
    assert 'window.pages.get("console:6")' in source
    assert "adviser.set_raid_plan_adviser_scope(plan)" in source
    assert 'window.show_page("console:6")' in source


def test_optimizer_adviser_is_explicitly_read_only_and_plan_scoped() -> None:
    source = Path("ui/raid_plan_optimizer_adviser_support.py").read_text(encoding="utf-8")

    assert "RaidPlanOptimizerAdviserService" in source
    assert "RaidPlanSavedBuildResolutionService" in source
    assert "_populate_team_editor(page.team_table, autofill=False)" in source
    assert "No player, build, assignment, skill, gear, or Raid Plan field is changed automatically." in source
    assert "set_raid_plan_adviser_scope" in source
    assert "save" not in source.casefold().split("def _set_raid_plan_adviser_scope", 1)[1].split("def ", 1)[0]


def test_adviser_support_is_installed_before_main_window_builds_optimization_page() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    install_pos = source.index("install_raid_plan_optimizer_adviser_support()")
    wrap_pos = source.index("_ORIGINAL_BUILD_UI = MainWindow.build_ui")
    assert install_pos < wrap_pos
