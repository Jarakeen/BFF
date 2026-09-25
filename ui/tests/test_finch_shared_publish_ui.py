from pathlib import Path


def test_team_schedule_has_explicit_finch_publish_action() -> None:
    source = Path("ui/themed_roster_page.py").read_text(encoding="utf-8")

    assert 'QPushButton("To FD.my")' in source
    assert "publish_team_to_finch" in source
    assert "_FINCH_TEAM_PUBLISH_EXECUTOR" in source
    assert "_finch_team_publish_timer" in source
    assert "Save Team Schedule" in source


def test_raid_plan_publish_requires_saved_clean_plan() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert 'QPushButton("To FD.my")' in source
    assert "publish_raid_plan_to_finch" in source
    assert "if self.has_pending_changes():" in source
    assert "Save Raid Plan changes before publishing to Finch." in source
    assert "_FINCH_PLAN_PUBLISH_EXECUTOR" in source
    assert "_finch_plan_publish_timer" in source


def test_raid_plan_publish_has_only_one_publish_button_and_one_poller() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert source.count('QPushButton("To FD.my")') == 1
    assert "Publish to Finch" not in source
    assert source.count("def _poll_raid_plan_publish") == 1
    assert "def _poll_finch_plan_publish" not in source


def test_team_schedule_has_explicit_shared_team_read_import_action() -> None:
    source = Path("ui/themed_roster_page.py").read_text(encoding="utf-8")

    assert 'QPushButton("Check Mail")' in source
    assert "list_shared_teams_from_finch" in source
    assert "import_shared_team_from_finch" in source
    assert "Personnel is never imported." in source
    assert "_FINCH_TEAM_READ_EXECUTOR" in source


def test_raid_plan_has_explicit_shared_plan_read_import_action() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert 'QPushButton("Check Mail")' in source
    assert "list_shared_raid_plans_from_finch" in source
    assert "import_shared_raid_plan_from_finch" in source
    assert "shared assignments and build summaries" in source
    assert "_FINCH_PLAN_READ_EXECUTOR" in source
