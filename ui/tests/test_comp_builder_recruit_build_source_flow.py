from pathlib import Path

from ui import comp_builder_phase14_shell_support, raid_engine_dashboard_support


def test_raid_plan_trial_maps_to_comp_goal_before_roster_handoff() -> None:
    source = Path(raid_engine_dashboard_support.__file__).read_text(encoding="utf-8")

    assert "from ui.comp_builder_page import GOAL_TRIALS" in source
    assert "matching_goals = [" in source
    assert "mapped_trial" in source
    assert "preferred_goal" in source
    assert "comp.goal_combo.setCurrentIndex(index)" in source


def test_phase14_recruit_panel_exposes_ranked_build_source_action() -> None:
    source = Path(comp_builder_phase14_shell_support.__file__).read_text(encoding="utf-8")

    assert 'QPushButton("Load Current Ranked Builds")' in source
    assert "page.comp_phase14_refresh_sources.setVisible(True)" in source
    assert 'source_button = getattr(page, "refresh_esologs_button", None)' in source
    assert "source_button.click()" in source
    assert "page.comp_phase14_refresh_sources.setVisible(False)" in source
