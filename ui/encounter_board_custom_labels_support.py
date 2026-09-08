from __future__ import annotations

"""Freeform labels, reference anchors, and a compact key for the Raid Map.

Marker kind remains structural (boss, portal, healer, etc.) while label is fully
user-owned. Entrance, exit, and hardmode banner are static reference anchors:
they persist with the board, remain outside Position Timeline movement, and can
be locked in place once the room orientation is established.
"""

import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QGraphicsItem,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


_INSTALLED = False
REFERENCE_PREFIX = "reference_"
REFERENCE_PRESETS = {
    "Entrance": ("reference_entrance", 480.0, 495.0),
    "Exit": ("reference_exit", 480.0, 48.0),
    "Banner": ("reference_banner", 150.0, 465.0),
}
REFERENCE_GLYPHS = {
    "reference_entrance": "IN",
    "reference_exit": "OUT",
    "reference_banner": "⚑",
}


def _is_reference(item) -> bool:
    from ui.components.encounter_board import EncounterToken

    return isinstance(item, EncounterToken) and str(item.kind).startswith(REFERENCE_PREFIX)


def _reference_items(board):
    return [item for item in board._token_items() if _is_reference(item)]


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
    # state, update its human-readable labels without changing those ids. Static
    # reference points never enter the timeline and therefore need no timeline edit.
    timeline = getattr(board, "_position_timeline", None)
    stable_id = getattr(item, "_position_timeline_id", "")
    if timeline is not None and stable_id and not _is_reference(item):
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

    board.save_state()
    board.scene.update()
    board.view.viewport().update()


def _apply_reference_lock(board, locked: bool) -> None:
    locked = bool(locked)
    board._reference_points_locked = locked
    for item in _reference_items(board):
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not locked)
        item.setCursor(
            Qt.CursorShape.ArrowCursor if locked else Qt.CursorShape.OpenHandCursor
        )
    if hasattr(board, "raid_map_reference_lock"):
        board.raid_map_reference_lock.blockSignals(True)
        board.raid_map_reference_lock.setChecked(locked)
        board.raid_map_reference_lock.setText(
            "🔒 References" if locked else "🔓 References"
        )
        board.raid_map_reference_lock.blockSignals(False)
    board.scene.update()


def _toggle_reference_lock(board, checked: bool) -> None:
    _apply_reference_lock(board, checked)
    board.save_state()


def _add_reference(board) -> None:
    label = str(board.raid_map_reference_type.currentText() or "Entrance")
    kind, x, y = REFERENCE_PRESETS.get(label, REFERENCE_PRESETS["Entrance"])
    existing = [item for item in _reference_items(board) if item.kind == kind]
    visible_label = label if not existing else f"{label} {len(existing) + 1}"
    item = board._add_token(kind, visible_label, x, y, radius=16.0)
    item._raid_map_reference = True
    _apply_reference_lock(board, getattr(board, "_reference_points_locked", False))
    board.scene.clearSelection()
    item.setSelected(True)
    board.save_state()
    board.scene.update()


def _reconcile_timeline_ids_after_reload(board) -> None:
    """Reconnect renamed saved markers to existing timeline ids after restart."""

    timeline = getattr(board, "_position_timeline", None)
    if timeline is None or not timeline.steps:
        return

    from ui.components.encounter_board import EncounterToken, EncounterZone

    candidates: dict[tuple[str, str, str], list[str]] = {}
    for step in timeline.steps:
        for state in step.items:
            key = (
                str(state.family).casefold(),
                str(state.kind).casefold(),
                str(state.label).casefold(),
            )
            ids = candidates.setdefault(key, [])
            if state.item_id not in ids:
                ids.append(state.item_id)

    used: set[str] = set()
    current_items = []
    for item in board.scene.items():
        if isinstance(item, EncounterToken) and not _is_reference(item):
            current_items.append(("token", str(item.kind), str(item.label), item))
        elif isinstance(item, EncounterZone):
            current_items.append(("zone", str(item.zone_type), str(item.label), item))

    current_items.sort(
        key=lambda row: (
            row[0], row[1].casefold(), row[2].casefold(),
            round(row[3].pos().x(), 3), round(row[3].pos().y(), 3),
        )
    )
    for family, kind, label, item in current_items:
        key = (family.casefold(), kind.casefold(), label.casefold())
        stable_id = next(
            (value for value in candidates.get(key, ()) if value not in used),
            "",
        )
        if stable_id:
            item._position_timeline_id = stable_id
            used.add(stable_id)

    if hasattr(board, "position_timeline_step_combo"):
        index = board.position_timeline_step_combo.currentIndex()
        if index >= 0:
            from ui import encounter_position_timeline_support as timeline_ui
            timeline_ui._select_step(board, index)


def _paint_reference(item, painter, option, widget=None) -> None:
    r = item.radius
    selected = item.isSelected()
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)
    edge = QColor("#D6C6A5" if selected else "#868B88")
    fill = QColor("#343A3B")
    painter.setPen(QPen(edge, 2.3 if selected else 1.5))
    painter.setBrush(QBrush(fill))
    painter.drawEllipse(item.boundingRect().center(), r, r)

    glyph = REFERENCE_GLYPHS.get(item.kind, "•")
    glyph_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
    painter.setFont(glyph_font)
    painter.setPen(QColor("#F0EEE8"))
    painter.drawText(
        item.boundingRect().adjusted(0, 0, 0, -24),
        Qt.AlignmentFlag.AlignCenter,
        glyph,
    )

    label_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
    painter.setFont(label_font)
    painter.setPen(QColor("#D9D5CB"))
    painter.drawText(
        item.boundingRect().adjusted(0, r + 16, 0, 0),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        item.label,
    )


def _label_and_key_panel(board) -> QWidget:
    """Use the existing label/key row so the top of the map gains no new row."""

    panel = QWidget(board)
    row = QHBoxLayout(panel)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)

    heading = QLabel("LABEL")
    heading.setProperty("sidebarHeading", True)
    row.addWidget(heading)

    board.raid_map_custom_label = QLineEdit()
    board.raid_map_custom_label.setMinimumWidth(150)
    board.raid_map_custom_label.setPlaceholderText("Select one marker or zone to rename")
    board.raid_map_custom_label.returnPressed.connect(lambda: _rename_selected(board))
    row.addWidget(board.raid_map_custom_label, 1)

    board.raid_map_apply_label = QPushButton("Apply")
    board.raid_map_apply_label.clicked.connect(lambda: _rename_selected(board))
    row.addWidget(board.raid_map_apply_label)

    reference_heading = QLabel("REFERENCE")
    reference_heading.setProperty("sidebarHeading", True)
    row.addWidget(reference_heading)

    board.raid_map_reference_type = QComboBox()
    for name in REFERENCE_PRESETS:
        board.raid_map_reference_type.addItem(name)
    board.raid_map_reference_type.setMaximumWidth(105)
    board.raid_map_reference_type.setToolTip(
        "Static room reference point. Reference points persist across timeline steps."
    )
    row.addWidget(board.raid_map_reference_type)

    add_reference = QPushButton("+ Add")
    add_reference.setToolTip("Add the selected static reference point to the Raid Map")
    add_reference.clicked.connect(lambda: _add_reference(board))
    row.addWidget(add_reference)

    board.raid_map_reference_lock = QPushButton("🔓 References")
    board.raid_map_reference_lock.setCheckable(True)
    board.raid_map_reference_lock.setToolTip(
        "Lock Entrance, Exit, and Banner reference points so they cannot be dragged accidentally"
    )
    board.raid_map_reference_lock.toggled.connect(
        lambda checked: _toggle_reference_lock(board, checked)
    )
    row.addWidget(board.raid_map_reference_lock)

    key = QLabel(
        "KEY  Boss • M mini-boss • T tank • H healer • D DD • P portal-style • "
        "! AOE • + stack • IN entrance • OUT exit • ⚑ banner"
    )
    key.setProperty("muted", True)
    key.setWordWrap(True)
    key.setToolTip(
        "Marker type controls its symbol/style. Visible labels are freeform. "
        "Entrance, Exit, and Banner are static orientation references."
    )
    row.addWidget(key, 3)
    return panel


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components.encounter_board import EncounterBoard, EncounterToken

    original_build_ui = EncounterBoard._build_ui
    original_init = EncounterBoard.__init__
    original_save_state = EncounterBoard.save_state
    original_load_state = EncounterBoard.load_state
    original_token_paint = EncounterToken.paint

    def build_ui_with_labels(self):
        original_build_ui(self)
        root = self.layout()
        if root is None:
            return
        # Reuse the existing label/key row. No additional toolbar row is created.
        insert_at = max(0, root.count() - 1)
        root.insertWidget(insert_at, _label_and_key_panel(self))

    def save_state_with_reference_lock(self):
        original_save_state(self)
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return
        payload["reference_points_locked"] = bool(
            getattr(self, "_reference_points_locked", False)
        )
        self.state_path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    def load_state_with_reference_lock(self) -> bool:
        loaded = original_load_state(self)
        locked = False
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            locked = bool(payload.get("reference_points_locked", False))
        except (OSError, json.JSONDecodeError, TypeError):
            locked = False
        _apply_reference_lock(self, locked)
        return loaded

    def token_paint_with_references(self, painter, option, widget=None):
        if _is_reference(self):
            _paint_reference(self, painter, option, widget)
            return
        original_token_paint(self, painter, option, widget)

    def init_with_labels(self, *args, **kwargs):
        self._reference_points_locked = False
        original_init(self, *args, **kwargs)
        _reconcile_timeline_ids_after_reload(self)
        _apply_reference_lock(self, getattr(self, "_reference_points_locked", False))
        self.scene.selectionChanged.connect(lambda: _sync_label_editor(self))
        _sync_label_editor(self)

    EncounterBoard._build_ui = build_ui_with_labels
    EncounterBoard.save_state = save_state_with_reference_lock
    EncounterBoard.load_state = load_state_with_reference_lock
    EncounterBoard._apply_reference_lock = _apply_reference_lock
    EncounterBoard.__init__ = init_with_labels
    EncounterToken.paint = token_paint_with_references
    _INSTALLED = True
