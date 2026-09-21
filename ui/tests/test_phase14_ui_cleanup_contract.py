from __future__ import annotations

from pathlib import Path
import re


def test_live_raid_lower_workspace_uses_three_column_operational_layout() -> None:
    source = Path("ui/city_live_raid_page.py").read_text(encoding="utf-8")

    assert 'FoundryCard("Next 60 Seconds", "stopwatch"), "timeline"' in source
    assert 'FoundryCard("Quick Notes / Run Sheet", "clipboard"), "notes"' in source
    assert "right_column = QVBoxLayout()" in source
    assert "right_column.addWidget(coverage, 1)" in source
    assert "right_column.addWidget(recent, 1)" in source
    assert "lower.addLayout(right_column, 3)" in source
    assert "self.workspace_layout.addLayout(lower, 1)" in source
    assert "timeline.setMaximumHeight" not in source
    assert "self.run_notes_edit.setMaximumHeight" not in source


def test_finch_collaboration_has_compact_guide_and_explicit_empty_state() -> None:
    source = Path("ui/finch_collaboration_page.py").read_text(encoding="utf-8")

    assert 'FoundryCard("Collaboration Guide", "feather")' in source
    assert 'FoundryCard("Shared Snapshots", "archive")' in source
    assert 'FoundryCard("Attention Summary", "compass")' not in source
    assert "No shared Finch snapshots yet." in source
    assert "self.empty_state_label.setVisible(not self._rows)" in source
    assert "self.table.setVisible(bool(self._rows))" in source


def test_collectibles_dashboard_uses_one_progress_meter_anatomy() -> None:
    source = Path("ui/collectibles_dashboard_page.py").read_text(encoding="utf-8")
    specs = re.findall(
        r'DashboardSpec\([^\n]+?,\s*"(bar|ring|shield|vial)"\s*,',
        source,
    )

    assert specs
    assert set(specs) == {"bar"}
