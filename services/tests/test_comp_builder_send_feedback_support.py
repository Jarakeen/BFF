from pathlib import Path


def test_comp_maker_send_feedback_names_team_and_send_state() -> None:
    source = Path("ui/comp_builder_send_feedback_support.py").read_text(encoding="utf-8")

    assert 'f"TEAM / ROSTER PLAN: {_effective_plan_name(page)}"' in source
    assert 'button.setText("Sending Comp…")' in source
    assert 'feedback.setText(f\'Sending “{name}” to Roster…\')' in source
    assert 'label.setText(f\'Sent “{name}” to Roster ✓\')' in source
    assert 'button.setText("Send Comp to Roster")' in source


def test_roster_hides_generated_plan_dropdown_and_shows_static_team_name() -> None:
    source = Path("ui/comp_builder_roster_view_support.py").read_text(encoding="utf-8")

    assert 'combo = getattr(self, "generated_plan_combo", None)' in source
    assert "host.hide()" in source
    assert "combo.hide()" in source
    assert 'self.generated_plan_name_label = QLabel()' in source
    assert 'label.setText(f"TEAM: {_current_generated_plan_name(page)}")' in source


def test_roster_team_name_updates_when_just_sent_plan_is_selected() -> None:
    source = Path("ui/comp_builder_roster_view_support.py").read_text(encoding="utf-8")

    assert "_ORIGINAL_REFRESH_CHOICES(page, selected)" in source
    assert "_refresh_plan_name_label(page)" in source
    assert "RosterPage._refresh_generated_plan_choices = _refresh_generated_plan_choices_with_name" in source


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
