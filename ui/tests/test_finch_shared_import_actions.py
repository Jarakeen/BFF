from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_roster_shared_team_action_is_explicit_copy_to_local() -> None:
    source = _source("ui/themed_roster_page.py")

    assert 'QPushButton("Get Shared Teams")' in source
    assert '"Copy shared Team to Local:"' in source
    assert '"Copy Shared Team to Local"' in source
    assert "never overwrites an existing Team" in source
    assert "import_shared_team_from_finch" in source


def test_raid_plan_shared_action_is_explicit_copy_to_local_without_replace_warning() -> None:
    source = _source("ui/raid_plan_persistence_page.py")

    assert 'QPushButton("Get Shared Plans")' in source
    assert '"Copy shared Raid Plan to Local:"' in source
    assert '"Copy Shared Raid Plan to Local"' in source
    assert "never replaces an existing plan" in source
    assert "will be replaced" not in source
    assert "import_shared_raid_plan_from_finch" in source


def test_shared_reads_remain_user_triggered_not_refresh_side_effects() -> None:
    roster = _source("ui/themed_roster_page.py")
    raid_plan = _source("ui/raid_plan_persistence_page.py")

    roster_refresh = roster[roster.index("    def refresh(self):"):roster.index("    def _reload_schedule_teams")]
    assert "list_shared_teams_from_finch" not in roster_refresh

    load_plan = raid_plan[raid_plan.index("    def load_selected_plan"):raid_plan.index("    def save_current_plan")]
    assert "list_shared_raid_plans_from_finch" not in load_plan
