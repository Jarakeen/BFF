from pathlib import Path


def test_team_schedule_has_one_explicit_finch_publish_action() -> None:
    source = Path("ui/themed_roster_page.py").read_text(encoding="utf-8")

    assert source.count('QPushButton("Publish Team to Finch")') == 1
    assert source.count("publish_team_to_finch,") == 1
    assert "clicked.connect(self._publish_selected_team_to_finch)" in source
    assert "timeout.connect(self._poll_team_publish)" in source

    refresh_start = source.index("    def refresh(self):")
    publish_start = source.index("    def _publish_selected_team_to_finch", refresh_start)
    refresh_source = source[refresh_start:publish_start]
    assert "publish_team_to_finch" not in refresh_source


def test_raid_plan_has_one_explicit_finch_publish_action() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert source.count('QPushButton("Publish")') == 1
    assert source.count("publish_raid_plan_to_finch,") == 1
    assert "clicked.connect(self._publish_saved_plan_to_finch)" in source
    assert "timeout.connect(self._poll_raid_plan_publish)" in source
    assert "if self.has_pending_changes():" in source
    assert "Save Raid Plan changes before publishing to Finch." in source
    assert "plan_id=plan_id" in source


def test_normal_page_refresh_paths_do_not_publish_to_finch() -> None:
    roster_source = Path("ui/themed_roster_page.py").read_text(encoding="utf-8")
    plan_source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    roster_refresh_start = roster_source.index("    def refresh(self):")
    roster_publish_start = roster_source.index(
        "    def _publish_selected_team_to_finch", roster_refresh_start
    )
    assert "publish_team_to_finch" not in roster_source[
        roster_refresh_start:roster_publish_start
    ]

    plan_load_start = plan_source.index("    def load_selected_plan(self)")
    plan_delete_start = plan_source.index("    def delete_selected_plan", plan_load_start)
    assert "publish_raid_plan_to_finch" not in plan_source[
        plan_load_start:plan_delete_start
    ]
