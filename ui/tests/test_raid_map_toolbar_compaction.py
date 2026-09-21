from pathlib import Path


def test_raid_map_rename_and_reference_controls_are_in_compact_top_rows() -> None:
    source = Path("ui/encounter_board_custom_labels_support.py").read_text(encoding="utf-8")

    assert "def _install_inline_controls" in source
    assert "actor_toolbar = root.itemAt(0).layout()" in source
    assert "layout_toolbar = root.itemAt(2).layout()" in source
    assert "layout_toolbar.insertWidget(1, board.raid_map_custom_label, 1)" in source
    assert "layout_toolbar.insertWidget(2, board.raid_map_apply_label)" in source
    assert "layout_toolbar.addWidget(delete_button)" in source
    assert "actor_toolbar.addWidget(board.raid_map_reference_type)" in source
    assert "actor_toolbar.addWidget(board.raid_map_add_reference)" in source
    assert "actor_toolbar.addWidget(board.raid_map_reference_lock)" in source


def test_raid_map_animation_button_only_controls_timeline_panel() -> None:
    source = Path("ui/encounter_board_formation_support.py").read_text(encoding="utf-8")

    assert 'QPushButton("To Animate ▾")' in source
    assert '"Hide Animation ▴" if visible else "To Animate ▾"' in source
    assert "Show the animation timeline and playback controls." in source
    assert 'custom_label = getattr(self, "raid_map_custom_label", None)' not in source
