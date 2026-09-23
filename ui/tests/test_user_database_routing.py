from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_primary_user_owned_surfaces_use_foundrydock_database() -> None:
    expected = (
        "ui/roster_page.py",
        "ui/raid_plan_page.py",
        "ui/raid_roster_workspace_page.py",
        "ui/operations_console_schedule_support.py",
        "ui/build_context_variant_support.py",
        "ui/coverage_health_check_support.py",
        "ui/broadcast_page.py",
    )
    for path in expected:
        source = _source(path)
        assert "get_user_database_path" in source, path


def test_builds_keeps_reference_and_personnel_databases_separate() -> None:
    source = _source("ui/builds_page.py")
    assert 'self.database = EsoDatabase(self.data_dir / "eso.db")' in source
    assert "self.user_database = EsoDatabase(get_user_database_path())" in source
    assert "self.roster_service = RosterService(self.user_database)" in source


def test_collectible_batch_writes_go_through_profiled_user_service() -> None:
    source = _source("ui/collectibles_page.py")
    assert "ProfiledCollectibleService" in source
    assert "self.service.set_owned_batch" in source
    assert "INSERT INTO collectible_progress" not in source


def test_app_migrates_legacy_user_state_before_window_construction() -> None:
    source = _source("app.py")
    assert "migrate_legacy_user_data()" in source
    assert source.index("migrate_legacy_user_data()") < source.index("from ui.startup_splash")
