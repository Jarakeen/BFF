from pathlib import Path


def test_coverage_reads_canonical_user_database() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    assert "get_user_database_path" in source
    assert 'RaidPlanRepository(get_user_database_path())' in source
    assert 'RaidPlanRepository(get_data_dir() / "raid_plans.json")' not in source


def test_plan_workflow_routes_preserve_comp_and_coverage_context() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    route = source[
        source.index("def _route_plan_page("):
        source.index("def _open_finch_collaboration_workspace(")
    ]
    assert 'if target == "comp_builder":' in route
    assert "_open_plan_comp_builder(window, source_page)" in route
    assert 'if target == "console:7":' in route
    assert '_open_raid_plan_coverage(window, plan)' in route
    assert 'Save or discard Raid Plan changes before opening Coverage.' in route


def test_finch_coverage_publish_defaults_to_canonical_plan_database() -> None:
    source = Path("services/finch_shared_coverage_service.py").read_text(encoding="utf-8")

    assert "get_user_database_path" in source
    assert "else get_user_database_path()" in source
