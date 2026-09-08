from pathlib import Path

from ui import encounter_position_timeline_support
from ui import rylo_raid_map_support


def test_position_timeline_support_exposes_expected_controls() -> None:
    source = Path(encounter_position_timeline_support.__file__).read_text(encoding="utf-8")

    for text in (
        "POSITION TIMELINE",
        "+ Step",
        "Duplicate",
        "Save Step",
        "▶ Play",
        "⏸",
        "Step note",
    ):
        assert text in source


def test_position_timeline_animates_between_saved_positions() -> None:
    source = Path(encounter_position_timeline_support.__file__).read_text(encoding="utf-8")

    assert "_start_transition" in source
    assert "_animation_tick" in source
    assert "time.monotonic()" in source
    assert "item.setPos" in source
    assert "_position_timeline_timer.start(16)" in source


def test_raid_map_startup_installs_position_timeline_for_all_themes() -> None:
    source = Path(rylo_raid_map_support.__file__).read_text(encoding="utf-8")

    assert "install_position_timeline" in source
    assert "install_position_timeline()" in source
    assert "if not _is_rylo():" in source
