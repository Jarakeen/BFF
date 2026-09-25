from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_raid_plan_overview_has_one_action_surface_and_team_schedule() -> None:
    source = _source("ui/city_raid_plan_workspace_page.py")

    assert 'FoundryCard("Quick Actions"' not in source
    assert 'FoundryCard("Linked Resources"' not in source
    assert 'FoundryCard("Team Schedule", "stopwatch")' in source
    assert 'self.roster_service.get_team_schedule(team_name)' in source
    assert 'self.backup_plan_button.setParent(left)' in source
    assert 'self.share_builds_button.setParent(left)' in source
    assert 'QPushButton("Save Current Plan")' not in source


def test_raid_plan_save_has_prewrite_snapshot_and_bulk_identity_guard() -> None:
    source = _source("ui/raid_plan_persistence_page.py")
    start = source.index("    def save_current_plan(self)")
    end = source.index("    def _open_assignments", start)
    method = source[start:end]

    snapshot = method.index("self._safety_snapshots.create(")
    write = method.index("self.plan_repository.save(")
    assert snapshot < write
    assert "len(changed_player_seats) >= 6" in method
    assert "Save blocked: this edit would replace player identity" in method
    assert "duplicate_occupied_player_seats(plan)" in method
    assert "persisted != plan" in method


def test_raid_plan_save_repairs_build_that_belongs_to_different_character() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert "def _repair_selected_build_identity(self, member, catalog):" in source
    repair = source.split(
        "def _repair_selected_build_identity(self, member, catalog):", 1
    )[1].split("    def current_plan", 1)[0]
    assert 'build_character_id == character_id' in repair
    assert "self._replacement_build_for_stale_member(member)" in repair
    assert "selected_build_id=replacement_id or None" in repair

    current = source.split("def current_plan(self) -> RaidPlan:", 1)[1].split(
        "    def has_pending_changes", 1
    )[0]
    assert current.count("self._repair_selected_build_identity(") >= 2
