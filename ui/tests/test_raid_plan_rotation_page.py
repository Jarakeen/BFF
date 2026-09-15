from pathlib import Path


def test_raid_plan_rotation_page_preserves_coverage_inheritance() -> None:
    source = Path("ui/raid_plan_rotation_page.py").read_text(encoding="utf-8")

    assert "from ui.raid_plan_coverage_page import RaidPlanCoveragePage" in source
    assert "class RaidPlanRotationPage(RaidPlanCoveragePage):" in source
    assert "rotationRequested = Signal(object, str)" in source
    assert '"Open Rotation"' in source
    assert "self.rotationRequested.emit(plan, seat_id)" in source


def test_raid_engine_routes_selected_chair_to_existing_rotation_page() -> None:
    route_source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")
    adviser_source = Path("ui/raid_plan_adviser_page.py").read_text(encoding="utf-8")

    assert "from ui.raid_plan_adviser_page import RaidPlanAdviserPage" in route_source
    assert "raid_plans = RaidPlanAdviserPage()" in route_source
    assert "from ui.raid_plan_rotation_page import RaidPlanRotationPage" in adviser_source
    assert "class RaidPlanAdviserPage(RaidPlanRotationPage):" in adviser_source
    assert "rotationRequested.connect" in route_source
    assert 'window.pages.get("rotations")' in route_source
    assert "bind_raid_plan_rotation_page" in route_source
    assert 'window.show_page("rotations")' in route_source


def test_rotation_handoff_does_not_mutate_rotation_engine_files() -> None:
    support = Path("ui/raid_plan_rotation_handoff_support.py").read_text(encoding="utf-8")

    assert "RaidPlanRotationContextBridge" in support
    assert "RaidPlanSavedBuildResolutionService" in support
    assert "set_rotation_generate_canonical_context_provider" in support
    assert "selected_encounter_id" in support
    assert "encounter_id=encounter_id" in support
    assert "with_raid_plan_member" not in support
