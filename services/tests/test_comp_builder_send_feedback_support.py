from pathlib import Path


def test_comp_maker_send_feedback_keeps_only_send_state_in_actions_card() -> None:
    source = Path("ui/comp_builder_send_feedback_support.py").read_text(encoding="utf-8")

    assert 'button.setText("Sending Comp…")' in source
    assert 'feedback.setText(f\'Sending “{name}” to Roster…\')' in source
    assert 'label.setText(f\'Sent “{name}” to Roster ✓\')' in source
    assert 'button.setText("Send Comp to Roster")' in source
    assert 'page.comp_team_name_label = QLabel()' not in source
    assert 'TEAM / ROSTER PLAN:' not in source


def test_roster_hides_generated_plan_dropdown_without_static_team_name() -> None:
    source = Path("ui/comp_builder_roster_view_support.py").read_text(encoding="utf-8")

    assert 'combo = getattr(self, "generated_plan_combo", None)' in source
    assert "host.hide()" in source
    assert "combo.hide()" in source
    assert 'generated_plan_name_label' not in source
    assert 'TEAM:' not in source


def test_roster_generated_plan_choices_still_refresh_while_hidden() -> None:
    source = Path("ui/comp_builder_roster_view_support.py").read_text(encoding="utf-8")

    assert "_ORIGINAL_REFRESH_CHOICES(page, selected)" in source
    assert "RosterPage._refresh_generated_plan_choices = _refresh_generated_plan_choices_hidden" in source


def test_selected_build_details_surface_skills_before_send() -> None:
    source = Path("ui/comp_builder_candidate_picker_support.py").read_text(encoding="utf-8")

    assert 'page.comp_candidate_details_label = QLabel()' in source
    assert '"SELECTED BUILD DETAILS"' in source
    assert '"SKILLS / ABILITIES"' in source
    assert "candidate.skills" in source
    assert "candidate.gear_sets" in source


def test_send_feedback_and_roster_cleanup_are_installed() -> None:
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(encoding="utf-8")

    assert "install_comp_builder_send_feedback()" in installer
    assert "install_comp_builder_roster_view()" in installer
    assert installer.index("install_comp_builder_send_feedback()") < installer.index(
        "install_comp_builder_roster_view()"
    )
