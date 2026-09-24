from __future__ import annotations

from pathlib import Path


def test_city_raid_pages_share_compact_plan_context_bar() -> None:
    helper = Path("ui/raid_plan_header_controls.py").read_text(encoding="utf-8")
    plan = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")
    assignments = Path("ui/city_raid_assignments_page.py").read_text(encoding="utf-8")
    persistence = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert "def rehome_plan_header_controls(" in helper
    assert 'row.addWidget(_field("TRIAL", trial_combo' in helper
    assert 'row.addWidget(_field("DIFFICULTY", difficulty_combo' in helper
    assert 'row.addWidget(_field("PLAN", plan_name_edit' in helper
    assert 'row.addWidget(_field("SAVED PLAN", saved_plan_combo' in helper
    assert 'shared.setText("Shared Plans")' in helper

    assert "self.load_plan_button = QPushButton" in persistence
    assert "self.save_plan_button = QPushButton" in persistence
    assert "self.delete_plan_button = QPushButton" in persistence
    assert "self.saved_plan_controls = controls" in persistence

    assert "rehome_plan_header_controls(" in plan
    assert "trailing_widgets=(self.share_builds_button,)" in plan
    assert "self.header.add_context_widget(self.share_builds_button)" not in plan

    assert "rehome_plan_header_controls(" in assignments
    assert "trailing_widgets=(self.save_assignments_button,)" in assignments
    assert 'self.save_assignments_button = QPushButton("Save Assignments")' in assignments


def test_assignments_context_bar_has_one_save_action() -> None:
    assignments = Path("ui/city_raid_assignments_page.py").read_text(encoding="utf-8")

    assert 'self.save_assignments_button = QPushButton("Save Assignments")' in assignments
    assert '"load_plan_button",' in assignments
    assert '"publish_plan_finch_button",' in assignments
    assert '"get_shared_plans_button",' in assignments
    assert '"delete_plan_button",' in assignments
    context_call = assignments[
        assignments.index("plan_context_bar = rehome_plan_header_controls("):
        assignments.index("self.workspace_layout.addWidget(plan_context_bar)")
    ]
    assert '"save_plan_button"' not in context_call


def test_assignments_save_returns_persisted_plan() -> None:
    assignments = Path("ui/city_raid_assignments_page.py").read_text(encoding="utf-8")

    save_method = assignments[
        assignments.index("    def save_current_plan(self):"):
        assignments.index("\n\n\n__all__")
    ]
    assert "saved = super().save_current_plan()" in save_method
    assert "return saved" in save_method


def test_assignment_apply_rebaselines_after_visible_assignments_restore() -> None:
    assignments = Path("ui/raid_plan_assignment_page.py").read_text(encoding="utf-8")

    apply_method = assignments[
        assignments.index("    def apply_plan(self, plan: RaidPlan) -> None:"):
        assignments.index("    def clear_plan(self) -> None:")
    ]
    assert "self._navigation_baseline_plan = self.current_plan()" in apply_method
    assert "self._refresh_action_availability()" in apply_method
