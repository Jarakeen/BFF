from pathlib import Path


def test_city_raid_plan_exposes_editable_team_selector() -> None:
    source = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")

    assert "self.team_combo = QComboBox()" in source
    assert 'self.team_combo.addItem("No Team", "")' in source
    assert "team_name=team_name or None" in source
    assert 'self._refresh_team_choices(str(getattr(plan, "team_name", "") or ""))' in source


def test_raid_plan_header_places_team_between_plan_and_saved_plan() -> None:
    source = Path("ui/raid_plan_header_controls.py").read_text(encoding="utf-8")

    plan = source.index('_field("PLAN", plan_name_edit')
    team = source.index('_field("TEAM", team_combo')
    saved = source.index('_field("SAVED PLAN", saved_plan_combo')
    assert plan < team < saved


def test_raid_plan_personnel_sync_uses_visible_team_selector() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert 'team_combo = getattr(self, "team_combo", None)' in source
    assert "return _clean(team_combo.currentData())" in source
