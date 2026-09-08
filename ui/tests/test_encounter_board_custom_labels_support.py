from pathlib import Path

from ui import encounter_board_custom_labels_support
from ui import rylo_raid_map_support


def test_custom_label_support_exposes_label_editor_and_key() -> None:
    source = Path(encounter_board_custom_labels_support.__file__).read_text(encoding="utf-8")

    for text in (
        "LABEL",
        "Apply",
        "KEY  Boss = boss marker",
        "P = portal-style",
        "shaded circle = zone",
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


def test_raid_map_startup_installs_custom_labels_for_all_themes() -> None:
    source = Path(rylo_raid_map_support.__file__).read_text(encoding="utf-8")

    assert "install_custom_labels" in source
    assert "install_custom_labels()" in source
