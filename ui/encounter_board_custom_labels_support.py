from __future__ import annotations

"""Freeform labels, reference anchors, and a compact key for the Raid Map.

Marker kind remains structural (boss, portal, healer, etc.) while label is fully
user-owned. Entrance, exit, and hardmode banner are static reference anchors:
they persist with the board, remain outside Position Timeline movement, and can
be locked in place once the room orientation is established.
"""

import json

from shiboken6 import isValid
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QGraphicsItem,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
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


def _qt_alive(value) -> bool:
    if value is None:
        return False
    try:
        return bool(isValid(value))
    except (RuntimeError, TypeError):
        return False


def _selected_labelable(board):
    from ui.components.encounter_board import EncounterToken, EncounterZone

    if not _qt_alive(board):
        return None
    scene = getattr(board, "scene", None)
    if not _qt_alive(scene):
        return None

    try:
        selected_items = scene.selectedItems()
    except RuntimeError:
        return None

    selected = [
        item
        for item in selected_items
        if isinstance(item, (EncounterToken, EncounterZone))
    ]
    return selected[0] if len(selected) == 1 else None


def _item_kind(item) -> tuple[str, str]:
    from ui.components.encounter_board import EncounterToken

    if isinstance(item, EncounterToken):
        return "token", str(item.kind)
    return "zone", str(item.zone_type)


def _sync_label_editor(board) -> None:
    if not _qt_alive(board):
        return
    editor = getattr(board, "raid_map_custom_label", None)
    apply_button = getattr(board, "raid_map_apply_label", None)
    if not _qt_alive(editor) or not _qt_alive(apply_button):
        return

    item = _selected_labelable(board)
    editor.blockSignals(True)
    if item is None:
        editor.clear()
        editor.setPlaceholderText("Select one marker or zone to rename")
        editor.setEnabled(False)
        apply_button.setEnabled(False)
    else:
        editor.setEnabled(True)
        apply_button.setEnabled(True)
        editor.setText(str(item.label))
        family, kind = _item_kind(item)
        editor.setPlaceholderText(
            f"Custom label for {family} / {kind}"
        )
    editor.blockSignals(False)


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
        board.raid_map_reference_lock.setText("🔒" if locked else "🔓")
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




def _seat_id_for_token(item, ordinal: int) -> str:
    kind = str(getattr(item, "kind", "") or "").casefold()
    if kind == "tank":
        return f"tank-{ordinal}"
    if kind == "healer":
        return f"healer-{ordinal}"
    if kind == "dps":
        return f"dd-{ordinal}"
    return ""


def _refresh_player_name_labels(board) -> None:
    enabled = bool(getattr(board, "_raid_map_show_player_names", False))
    resolver = getattr(board, "raid_plan_member_labels_resolver", None)
    labels = resolver() if enabled and callable(resolver) else {}
    counters = {"tank": 0, "healer": 0, "dps": 0}
    tokens = sorted(
        (item for item in board._token_items() if str(item.kind).casefold() in counters),
        key=lambda item: (str(item.kind).casefold(), item.pos().x(), item.pos().y()),
    )
    for item in tokens:
        kind = str(item.kind).casefold()
        counters[kind] += 1
        seat_id = _seat_id_for_token(item, counters[kind])
        if not hasattr(item, "_raid_map_seat_label"):
            item._raid_map_seat_label = str(item.label)
        seat_label = str(item._raid_map_seat_label)
        player = str(labels.get(seat_id, "") or "").strip()
        item.label = player if enabled and player else seat_label
        item.update()
    board.scene.update()
    board.view.viewport().update()


def _toggle_player_name_labels(board, checked: bool) -> None:
    board._raid_map_show_player_names = bool(checked)
    _refresh_player_name_labels(board)

def _install_inline_controls(board) -> None:
    """Place rename/reference controls into existing Raid Map toolbar rows."""

    root = board.layout()
    if root is None or root.count() < 3:
        return

    actor_toolbar = root.itemAt(0).layout()
    layout_toolbar = root.itemAt(2).layout()
    if actor_toolbar is None or layout_toolbar is None:
        return

    # ------------------------------------------------------------------
    # LAYOUT row: rename stays visible on the left; destructive Delete is
    # deliberately pushed all the way to the right.
    # ------------------------------------------------------------------
    board.raid_map_custom_label = QLineEdit()
    board.raid_map_custom_label.setMinimumWidth(260)
    board.raid_map_custom_label.setPlaceholderText("Select marker or zone to rename")
    board.raid_map_custom_label.returnPressed.connect(lambda: _rename_selected(board))

    board.raid_map_apply_label = QPushButton("Rename")
    board.raid_map_apply_label.clicked.connect(lambda: _rename_selected(board))

    delete_button = next(
        (
            button
            for button in board.findChildren(QPushButton)
            if button.text() == "Delete Selected"
        ),
        None,
    )
    if delete_button is not None:
        layout_toolbar.removeWidget(delete_button)

    # Caption remains first. Rename field/button immediately follow it.
    layout_toolbar.insertWidget(1, board.raid_map_custom_label, 1)
    layout_toolbar.insertWidget(2, board.raid_map_apply_label)

    # The existing stretch keeps view/output controls grouped away from Rename.
    # Re-adding Delete last makes it the far-right destructive action.
    if delete_button is not None:
        layout_toolbar.addWidget(delete_button)

    # ------------------------------------------------------------------
    # ACTORS row: static orientation references live at the far right after
    # the row's existing stretch, where Entrance/Exit are always reachable.
    # ------------------------------------------------------------------
    reference_heading = QLabel("REFERENCE")
    reference_heading.setProperty("sidebarHeading", True)

    board.raid_map_reference_type = QComboBox()
    for name in REFERENCE_PRESETS:
        board.raid_map_reference_type.addItem(name)
    board.raid_map_reference_type.setMaximumWidth(115)
    board.raid_map_reference_type.setToolTip(
        "Add Entrance, Exit, or Banner as a static room reference."
    )

    board.raid_map_add_reference = QPushButton("+ Add")
    board.raid_map_add_reference.setToolTip(
        "Add the selected static reference point to the Raid Map."
    )
    board.raid_map_add_reference.clicked.connect(lambda: _add_reference(board))

    board.raid_map_reference_lock = QPushButton("🔓")
    board.raid_map_reference_lock.setCheckable(True)
    board.raid_map_reference_lock.setFixedWidth(38)
    board.raid_map_reference_lock.setToolTip(
        "Lock Entrance, Exit, and Banner reference points."
    )
    board.raid_map_reference_lock.toggled.connect(
        lambda checked: _toggle_reference_lock(board, checked)
    )

    actor_toolbar.addWidget(reference_heading)
    actor_toolbar.addWidget(board.raid_map_reference_type)
    actor_toolbar.addWidget(board.raid_map_add_reference)
    actor_toolbar.addWidget(board.raid_map_reference_lock)

    # Formation support owns the row this belongs on and is installed later.
    # Keep only the behavior here; that layer places the button immediately after
    # the formation controls once they actually exist.


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
        _install_inline_controls(self)

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
        self._raid_map_show_player_names = False
        original_init(self, *args, **kwargs)
        _reconcile_timeline_ids_after_reload(self)
        _apply_reference_lock(self, getattr(self, "_reference_points_locked", False))
        scene = getattr(self, "scene", None)
        if _qt_alive(scene):
            self._raid_map_label_selection_changed = lambda: _sync_label_editor(self)
            scene.selectionChanged.connect(self._raid_map_label_selection_changed)
        _sync_label_editor(self)

    EncounterBoard._build_ui = build_ui_with_labels
    EncounterBoard.save_state = save_state_with_reference_lock
    EncounterBoard.load_state = load_state_with_reference_lock
    EncounterBoard._apply_reference_lock = _apply_reference_lock
    EncounterBoard.refresh_player_name_labels = _refresh_player_name_labels
    EncounterBoard._toggle_player_name_labels = _toggle_player_name_labels
    EncounterBoard.__init__ = init_with_labels
    EncounterToken.paint = token_paint_with_references
    _INSTALLED = True
