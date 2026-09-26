from pathlib import Path


def _source() -> str:
    return Path("ui/team_optimization_phase14_shell_support.py").read_text(
        encoding="utf-8"
    )


def test_phase14_optimizer_is_a_plan_scoped_recommendation_workbench() -> None:
    source = _source()

    assert "Composition creation lives in Comp Maker." in source
    assert 'FoundryCard("Current Team (Read-Only)"' in source
    assert 'FoundryCard("Recommended Improvements"' in source
    assert 'FoundryCard("Projected Team Health"' in source
    assert 'QPushButton("Review Selected Changes")' in source
    assert "_ORIGINAL_SET_SCOPE(self, raid_plan)" in source
    assert "_render_workbench(self, raid_plan, review)" in source


def test_phase14_optimizer_uses_exactly_twelve_read_only_chairs() -> None:
    source = _source()

    assert source.count('(\"dd-') >= 8
    assert '("tank-1", "Tank 1"' in source
    assert '("tank-2", "Tank 2"' in source
    assert '("healer-1", "Healer 1"' in source
    assert '("healer-2", "Healer 2"' in source
    assert "QAbstractItemView.EditTrigger.NoEditTriggers" in source
    assert "QAbstractItemView.SelectionMode.NoSelection" in source


def test_phase14_optimizer_keeps_unproven_metrics_explicit() -> None:
    source = _source()

    assert '("Survival", "Not evaluated"' in source
    assert '("Sustain", "Not evaluated"' in source
    assert '("Raid Damage", "Not evaluated"' in source
    assert "No synthetic percentage or DPS estimate" in source
    assert "It does not invent damage, uptime, or survival estimates." in source


def test_phase14_optimizer_never_saves_or_overwrites_from_review() -> None:
    source = _source()

    assert "Review only. Existing builds and the saved Raid Plan will not be overwritten." in source
    assert "No build or Raid Plan value has been changed." in source
    assert "optimizer_save_scenario_button" in source
    assert "save_scenario.setEnabled(False)" in source
    assert "repository.save(" not in source
    assert ".save(plan" not in source


def test_phase14_optimizer_shell_installs_after_plan_scope_adapter() -> None:
    support = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    adviser = support.index("install_raid_plan_optimizer_adviser_support()")
    shell = support.index("install_team_optimization_phase14_shell_support()")
    assert adviser < shell


def test_phase14_optimizer_explains_missing_and_incomplete_plan_scope() -> None:
    source = _source()

    assert "No Raid Plan is loaded." in source
    assert "Select a saved plan above to preview it" in source
    assert "An empty or partial team can still be opened" in source
    assert "Its team has no filled chairs yet." in source
    assert "report the remaining open chairs as blockers" in source
    assert "def _render_scope_message(page, raid_plan: RaidPlan, named_chairs: int)" in source
    assert "_render_scope_message(page, raid_plan, named_chairs)" in source


def test_phase14_optimizer_draft_preview_can_open_saved_plans_without_saving() -> None:
    source = _source()

    assert "Optimizer is in draft format. Only preview is available at this time." in source
    assert 'page.optimizer_plan_combo.addItem("Select saved Raid Plan…", None)' in source
    assert "RaidPlanRepository(get_user_database_path()).list_plans()" in source
    assert "RaidPlanRepository(get_user_database_path()).get(str(plan_id))" in source
    assert "page.set_raid_plan_adviser_scope(plan)" in source
    assert "page.optimizer_plan_combo.setEnabled(False)" not in source
    assert "repository.save(" not in source
    assert ".save(plan" not in source
