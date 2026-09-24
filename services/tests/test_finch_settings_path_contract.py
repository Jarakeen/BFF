from __future__ import annotations

from pathlib import Path

from engine.config import get_app_root, get_settings_path


def test_settings_path_is_anchored_to_app_root() -> None:
    assert get_settings_path() == get_app_root() / "settings.json"


def test_finch_runtime_surfaces_do_not_use_bare_settings_path() -> None:
    paths = (
        "ui/settings_page.py",
        "ui/finch_collaboration_page.py",
        "ui/coverage_page.py",
        "ui/city_raid_readiness_page.py",
        "ui/themed_roster_page.py",
        "ui/encounters_page.py",
        "ui/raid_plan_persistence_page.py",
        "ui/roster_page.py",
        "services/finch_shared_import_service.py",
        "services/finch_shared_publish_service.py",
        "services/finch_shared_readiness_service.py",
        "services/finch_shared_coverage_service.py",
        "services/finch_roster_sync_service.py",
        "services/finch_collaboration_overview_service.py",
        "services/finch_raid_map_publish_service.py",
    )
    for path in paths:
        source = Path(path).read_text(encoding="utf-8")
        assert 'Path("settings.json")' not in source, path
        assert "get_settings_path()" in source, path
