from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ui.raid_engine_dashboard_page import CoverageSnapshot, OptimizationSnapshot, RaidSlotSnapshot
from ui.raid_engine_dashboard_polish_support import (
    _generated_next_actions,
    _status_palette,
)


def test_dashboard_polish_uses_balanced_composition_surface() -> None:
    source = Path("ui/raid_engine_dashboard_polish_support.py").read_text(encoding="utf-8")
    assert "setMinimumSize(560, 350)" in source
    assert "setMinimumWidth(575)" in source
    assert "setMinimumWidth(300)" in source
    assert "setMinimumHeight(380)" in source


def test_dashboard_polish_uses_status_pills_and_colored_coverage() -> None:
    source = Path("ui/raid_engine_dashboard_polish_support.py").read_text(encoding="utf-8")
    assert "'0' if _is_rylo() else '10px'" in source
    assert '"SAVED", "COVERED"' in source
    assert '"NEEDS BUILD", "MISSING"' in source
    assert "setCellWidget(row, 3, host)" in source


def test_dashboard_polish_next_actions_are_editable_and_saveable() -> None:
    source = Path("ui/raid_engine_dashboard_polish_support.py").read_text(encoding="utf-8")
    assert "QTextEdit" in source
    assert 'FoundryButton("Save Note"' in source
    assert 'raid_engine_dashboard_notes.json' in source
    assert "_raid_engine_notes_dirty" in source


def test_generated_next_actions_preserve_dashboard_recommendations() -> None:
    slots = (
        RaidSlotSnapshot("Main Tank", "Susan", "Necromancer", "Tank", "SAVED"),
        RaidSlotSnapshot("Off Tank"),
        RaidSlotSnapshot("Healer 1", "Magrat", "Warden", "Healer", "SAVED"),
        RaidSlotSnapshot("Healer 2", "Recruitment Needed", "Flexible", "", "NEEDS BUILD"),
        RaidSlotSnapshot("DD 1"),
    )
    coverage = CoverageSnapshot(
        effects=(("War Horn", True), ("Minor Brittle", False), ("Purify", False)),
        covered=1,
        total=3,
    )
    optimization = OptimizationSnapshot(
        assigned=2,
        saved_builds=2,
        coverage_covered=1,
        coverage_total=3,
        capability_gaps=2,
        build_swaps=0,
        readiness=25,
    )

    text = _generated_next_actions(slots, coverage, optimization)
    assert "Assign an Off Tank" in text
    assert "Finish builds for Healer 2" in text
    assert "Minor Brittle" in text
    assert "2 capability-resolution gap" in text


def test_status_palette_distinguishes_good_bad_and_open_states() -> None:
    covered = _status_palette("COVERED")
    missing = _status_palette("MISSING")
    open_state = _status_palette("OPEN")
    assert covered != missing
    assert missing != open_state
