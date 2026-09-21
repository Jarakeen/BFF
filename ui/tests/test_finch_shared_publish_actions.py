from pathlib import Path


def test_roster_team_publish_is_explicit_and_nonblocking() -> None:
    source = Path("ui/themed_roster_page.py").read_text(encoding="utf-8")

    assert 'QPushButton("Publish Team to Finch")' in source
    assert "publish_team_to_finch" in source
    assert "ThreadPoolExecutor" in source
    assert "_finch_team_publish_timer" in source

    refresh_start = source.index("    def refresh(self):")
    reload_start = source.index("    def _reload_schedule_teams", refresh_start)
    refresh_source = source[refresh_start:reload_start]
    assert "publish_team_to_finch" not in refresh_source


def test_raid_plan_publish_requires_saved_clean_plan_and_is_nonblocking() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert 'QPushButton("Publish")' in source
    assert "publish_raid_plan_to_finch" in source
    assert "ThreadPoolExecutor" in source
    assert "_finch_plan_publish_timer" in source
    assert "if self.has_pending_changes():" in source
    assert "Save Raid Plan changes before publishing to Finch." in source
    assert "Save this Raid Plan before publishing to Finch." in source
