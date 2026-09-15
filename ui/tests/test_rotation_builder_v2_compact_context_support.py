from pathlib import Path

import ui.rotation_builder_v2_compact_context_support as compact_context
import ui.rotation_dashboard_layout_support as layout_support


def test_rotation_context_card_matches_compact_mockup_proportions() -> None:
    source = Path(compact_context.__file__).read_text(encoding="utf-8")

    assert 'control.setMinimumHeight(30)' in source
    assert 'control.setMaximumHeight(30)' in source
    assert 'card.set_body_margins(10, 5, 10, 6)' in source
    assert 'card.set_body_spacing(4)' in source
    assert 'context_grid.setVerticalSpacing(3)' in source
    assert '_compact_field("CHARACTER", page.character_combo)' in source
    assert '_compact_field("DIFFICULTY", page.rotation_threshold_difficulty_combo)' in source
    assert '_compact_field("ROTATION GOAL", page.rotation_goal_combo)' in source
    assert 'build_summary.hide()' in source


def test_compact_context_installs_after_v2_finish() -> None:
    source = Path(layout_support.__file__).read_text(encoding="utf-8")

    finish = source.index("install_rotation_builder_v2_finish(page)")
    compact = source.index("install_rotation_builder_v2_compact_context(page)")
    assert finish < compact
