from pathlib import Path


def test_comp_maker_send_feedback_keeps_only_send_state_in_actions_card() -> None:
    source = Path("ui/comp_builder_send_feedback_support.py").read_text(encoding="utf-8")

    assert 'button.setText("Sending Comp…")' in source
    assert 'feedback.setText(f\'Sending “{name}” to Roster…\')' in source
    assert 'label.setText(f\'Sent “{name}” to Roster ✓\')' in source
    assert 'button.setText("Send Comp to Roster")' in source
    assert 'page.comp_team_name_label = QLabel()' not in source
    assert 'TEAM / ROSTER PLAN:' not in source


def test_selected_build_details_surface_skills_before_send() -> None:
    source = Path("ui/comp_builder_candidate_picker_support.py").read_text(encoding="utf-8")

    assert 'page.comp_candidate_details_label = QLabel()' in source
    assert '"SELECTED BUILD DETAILS"' in source
    assert '"SKILLS / ABILITIES"' in source
    assert "candidate.skills" in source
    assert "candidate.gear_sets" in source


def test_send_feedback_stays_installed_without_legacy_roster_bridge() -> None:
    installer = Path("ui/application_team_optimization_bootstrap.py").read_text(
        encoding="utf-8"
    )

    assert "install_comp_builder_send_feedback()" in installer
    assert "install_comp_builder_roster_view()" not in installer
    assert "comp_builder_roster_view_support" not in installer
