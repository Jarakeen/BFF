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
