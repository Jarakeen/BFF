from __future__ import annotations

"""Freeform labels and a compact symbol key for the interactive Raid Map.

Marker kind remains structural (boss, portal, healer, etc.) while label is fully
user-owned. This lets the same portal-style marker represent a portal, poison
spot, meteor drop, or whatever other indignity the encounter requires.
"""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


_INSTALLED = False


def _selected_labelable(board):
    from ui.components.encounter_board import EncounterToken, EncounterZone

    selected = [
        item
        for item in board.scene.selectedItems()
        if isinstance(item, (EncounterToken, EncounterZone))
    ]
    return selected[0] if len(selected) == 1 else None


def _item_kind(item) -> tuple[str, str]:
    from ui.components.encounter_board import EncounterToken

    if isinstance(item, EncounterToken):
        return "token", str(item.kind)
    return "zone", str(item.zone_type)


def _sync_label_editor(board) -> None:
    if not hasattr(board, "raid_map_custom_label"):
        return
    item = _selected_labelable(board)
    board.raid_map_custom_label.blockSignals(True)
    if item is None:
        board.raid_map_custom_label.clear()
        board.raid_map_custom_label.setPlaceholderText("Select one marker or zone to rename")
        board.raid_map_custom_label.setEnabled(False)
        board.raid_map_apply_label.setEnabled(False)
    else:
        board.raid_map_custom_label.setEnabled(True)
        board.raid_map_apply_label.setEnabled(True)
        board.raid_map_custom_label.setText(str(item.label))
        family, kind = _item_kind(item)
        board.raid_map_custom_label.setPlaceholderText(
            f"Custom label for {family} / {kind}"
        )
    board.raid_map_custom_label.blockSignals(False)


def _rename_selected(board) -> None:
    item = _selected_labelable(board)
    if item is None:
        return
    label = " ".join(board.raid_map_custom_label.text().split()).strip()
    if not label:
        return

    old_label = str(item.label)
    if old_label == label:
        return

    item.label = label
    item.update()

    # Position Timeline owns stable item ids. If this board already has timeline
    # state, update its human-readable labels without changing those ids.
    timeline = getattr(board, "_position_timeline", None)
    stable_id = getattr(item, "_position_timeline_id", "")
    if timeline is not None and stable_id:
        from dataclasses import replace
        from services.encounter_position_timeline import PositionTimeline

        changed = False
        steps = []
        for step in timeline.steps:
            items = []
            for state in step.items:
                if state.item_id == stable_id and state.label != label:
                    state = replace(state, label=label)
                    changed = True
                items.append(state)
            steps.append(replace(step, items=tuple(items)))
        if changed:
            board._position_timeline = PositionTimeline(steps=tuple(steps))
            store = getattr(board, "_position_timeline_store", None)
            if store is not None:
                store.save(board._position_timeline)

    # Existing board persistence already stores each item's label. Save through
    # the board's current wrapper so uploaded backgrounds/accessibility state are
    # preserved too.
    board.save_state()
    board.scene.update()
    board.view.viewport().update()


def _label_and_key_panel(board) -> QWidget:
    panel = QWidget(board)
    row = QHBoxLayout(panel)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)

    heading = QLabel("LABEL")
    heading.setProperty("sidebarHeading", True)
    row.addWidget(heading)

    board.raid_map_custom_label = QLineEdit()
    board.raid_map_custom_label.setMinimumWidth(180)
    board.raid_map_custom_label.setPlaceholderText("Select one marker or zone to rename")
    board.raid_map_custom_label.returnPressed.connect(lambda: _rename_selected(board))
    row.addWidget(board.raid_map_custom_label, 1)

    board.raid_map_apply_label = QPushButton("Apply")
    board.raid_map_apply_label.clicked.connect(lambda: _rename_selected(board))
    row.addWidget(board.raid_map_apply_label)

    key = QLabel(
        "KEY  Boss = boss marker   M = mini-boss   T = tank   H = healer   "
        "D = DD   P = portal-style   ! = AOE   + = stack   shaded circle = zone"
    )
    key.setProperty("muted", True)
    key.setWordWrap(True)
    key.setToolTip(
        "Marker type controls its symbol/style. The visible label is freeform, "
        "so a portal-style marker can be named Poison Spot, North Portal, etc."
    )
    row.addWidget(key, 3)
    return panel


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components.encounter_board import EncounterBoard

    original_build_ui = EncounterBoard._build_ui
    original_init = EncounterBoard.__init__

    def build_ui_with_labels(self):
        original_build_ui(self)
        root = self.layout()
        if root is None:
            return
        # Keep the label/key beside the editing controls and above the timeline
        # / map itself. Accessibility may hide the old helper paragraph at index 2.
        insert_at = max(0, root.count() - 1)
        root.insertWidget(insert_at, _label_and_key_panel(self))

    def init_with_labels(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.scene.selectionChanged.connect(lambda: _sync_label_editor(self))
        _sync_label_editor(self)

    EncounterBoard._build_ui = build_ui_with_labels
    EncounterBoard.__init__ = init_with_labels
    _INSTALLED = True
