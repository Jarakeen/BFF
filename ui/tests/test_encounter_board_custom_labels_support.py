from pathlib import Path

from ui import encounter_board_custom_labels_support
from ui import rylo_raid_map_support


def test_custom_label_support_exposes_label_editor_and_key() -> None:
    source = Path(encounter_board_custom_labels_support.__file__).read_text(encoding="utf-8")

    for text in (
        "LABEL",
        "Apply",
        "KEY  Boss",
        "P portal-style",
        "IN entrance",
        "OUT exit",
        "⚑ banner",
        "Select one marker or zone to rename",
    ):
        assert text in source


def test_custom_label_keeps_marker_kind_separate_from_freeform_label() -> None:
    source = Path(encounter_board_custom_labels_support.__file__).read_text(encoding="utf-8")

    assert "item.label = label" in source
    assert "item.kind" in source
    assert "item.zone_type" in source
    assert "board.save_state()" in source


def test_custom_label_updates_timeline_human_label_without_changing_item_id() -> None:
    source = Path(encounter_board_custom_labels_support.__file__).read_text(encoding="utf-8")

    assert "state.item_id == stable_id" in source
    assert "replace(state, label=label)" in source
    assert "_reconcile_timeline_ids_after_reload" in source
    assert "item._position_timeline_id = stable_id" in source


def test_reference_points_use_existing_label_key_row_not_a_new_row() -> None:
    source = Path(encounter_board_custom_labels_support.__file__).read_text(encoding="utf-8")

    assert '"REFERENCE"' in source
    assert '"Entrance"' in source
    assert '"Exit"' in source
    assert '"Banner"' in source
    assert "Reuse the existing label/key row" in source
    assert "root.insertWidget(insert_at, _label_and_key_panel(self))" in source


def test_reference_points_are_lockable_and_persist_lock_state() -> None:
    source = Path(encounter_board_custom_labels_support.__file__).read_text(encoding="utf-8")

    assert "reference_points_locked" in source
    assert "ItemIsMovable" in source
    assert "_apply_reference_lock" in source
    assert "🔒 References" in source
    assert "🔓 References" in source


def test_reference_points_are_excluded_from_position_timeline() -> None:
    source = Path(rylo_raid_map_support.__file__).read_text(encoding="utf-8")

    assert "timeline_board_items_without_references" in source
    assert 'startswith("reference_")' in source
    assert "Reference anchors are spatial context, not choreography" in source


def test_raid_map_startup_installs_custom_labels_for_all_themes() -> None:
    source = Path(rylo_raid_map_support.__file__).read_text(encoding="utf-8")

    assert "install_custom_labels" in source
    assert "install_custom_labels()" in source
