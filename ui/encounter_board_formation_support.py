from __future__ import annotations

"""Preset raid-stack formations for the Encounters Raid Map.

Formations are presentation/positioning helpers. They reuse the existing
Urban Wilderness DD/healer markers, can be moved as one locked group, and keep
all normal Raid Map persistence/capture behavior.
"""

from dataclasses import dataclass
import math

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from services.accessibility_preferences import VISUAL_THEME_URBAN_WILDERNESS

_INSTALLED = False

# Raid Map scene units are pixel-like logical coordinates. Use the standard
# 96-DPI CSS conversion so the requested 1.75 cm of additional breathing room
# is explicit and maintainable instead of becoming another mystery number.
HOUSE_STACK_EXTRA_SPACING_CM = 1.75
HOUSE_STACK_EXTRA_SPACING_SCENE_UNITS = HOUSE_STACK_EXTRA_SPACING_CM * (96.0 / 2.54)


@dataclass(frozen=True)
class FormationPreset:
    key: str
    label: str
    dps_positions: tuple[tuple[float, float], ...]
    healer_positions: tuple[tuple[float, float], ...]


FORMATION_PRESETS = (
    FormationPreset(
        key="house_stacks",
        label="House Stacks",
        # Canonical house-stack numbering:
        #   5   6   7   8
        #   1   2   3   4
        # Original DD center spacing was 80 horizontal / 60 vertical.
        # Add 1.75 cm (~66.14 scene units at 96 DPI) around the player slots
        # while preserving the formation center and numbering.
        dps_positions=(
            (260.79, 348.07),
            (406.93, 348.07),
            (553.07, 348.07),
            (699.21, 348.07),
            (260.79, 221.93),
            (406.93, 221.93),
            (553.07, 221.93),
            (699.21, 221.93),
        ),
        healer_positions=((333.86, 454.0), (626.14, 454.0)),
    ),
    FormationPreset(
        key="rainbow_stacks",
        label="Rainbow Stacks",
        # Reference layout:
        #        H1      H2
        #      DD2    DD3
        #   DD1          DD4
        #      DD6    DD7
        # DD5              DD8
        dps_positions=(
            (375.0, 285.0),
            (445.0, 250.0),
            (515.0, 250.0),
            (585.0, 285.0),
            (315.0, 340.0),
            (415.0, 320.0),
            (545.0, 320.0),
            (645.0, 340.0),
        ),
        healer_positions=((365.0, 195.0), (595.0, 195.0)),
    ),
)

_PRESET_BY_KEY = {preset.key: preset for preset in FORMATION_PRESETS}


def _role_items(board, kind: str):
    return sorted(
        (item for item in board._token_items() if item.kind == kind),
        key=lambda item: (str(item.label).casefold(), item.pos().x(), item.pos().y()),
    )


def _ensure_role_items(board, kind: str, count: int):
    items = _role_items(board, kind)
    while len(items) < count:
        number = len(items) + 1
        label = f"DD {number}" if kind == "dps" else f"Healer {number}"
        token = board._add_token(kind, label, 480.0, 360.0)
        board._counts[kind] = max(board._counts.get(kind, 0), number)
        items.append(token)
    return items


def _set_group_lock_button(board) -> None:
    button = getattr(board, "formation_lock_button", None)
    if button is None:
        return
    locked = bool(getattr(board, "_formation_group_locked", True))
    button.blockSignals(True)
    button.setChecked(locked)
    button.setText("🔒" if locked else "🔓")
    button.setToolTip(
        "Formation locked: drag any formation player to move the whole stack."
        if locked
        else "Formation unlocked: players can be moved individually."
    )
    button.blockSignals(False)


def _set_rotation_controls(board) -> None:
    enabled = getattr(board, "_active_formation_key", "") == "rainbow_stacks"
    for name in ("formation_rotate_left_button", "formation_rotate_right_button"):
        button = getattr(board, name, None)
        if button is not None:
            button.setEnabled(enabled)


def _clear_group_membership(board) -> None:
    for item in tuple(getattr(board, "_formation_group_items", ())):
        if getattr(item, "_formation_board", None) is board:
            item._formation_board = None
            item._formation_grouped = False
    board._formation_group_items = []


def _set_formation_group(board, preset_key: str, items) -> None:
    _clear_group_membership(board)
    board._formation_group_items = list(items)
    board._active_formation_key = str(preset_key or "")
    board._formation_group_locked = True
    for item in board._formation_group_items:
        item._formation_board = board
        item._formation_grouped = True
    _set_group_lock_button(board)
    _set_rotation_controls(board)


def _toggle_formation_lock(board, checked: bool) -> None:
    board._formation_group_locked = bool(checked)
    _set_group_lock_button(board)


def _group_scene_limits(item):
    from ui.components.encounter_board import SCENE_H, SCENE_W

    margin = max(62.0, float(getattr(item, "radius", 18.0)) + 8.0)
    return margin, SCENE_W - margin, margin, SCENE_H - margin - 24.0


def _clamped_group_delta(board, dx: float, dy: float) -> tuple[float, float]:
    starts = tuple(getattr(board, "_formation_drag_start_positions", ()))
    if not starts:
        return dx, dy

    min_dx = -float("inf")
    max_dx = float("inf")
    min_dy = -float("inf")
    max_dy = float("inf")
    for item, x, y in starts:
        left, right, top, bottom = _group_scene_limits(item)
        min_dx = max(min_dx, left - x)
        max_dx = min(max_dx, right - x)
        min_dy = max(min_dy, top - y)
        max_dy = min(max_dy, bottom - y)

    return (
        max(min_dx, min(max_dx, dx)),
        max(min_dy, min(max_dy, dy)),
    )


def _move_locked_group(board, anchor) -> None:
    if not bool(getattr(board, "_formation_group_locked", False)):
        return
    if getattr(board, "_formation_drag_anchor", None) is not anchor:
        return
    starts = tuple(getattr(board, "_formation_drag_start_positions", ()))
    if not starts:
        return

    anchor_start = getattr(board, "_formation_drag_anchor_start", None)
    if anchor_start is None:
        return
    dx = anchor.pos().x() - anchor_start[0]
    dy = anchor.pos().y() - anchor_start[1]
    dx, dy = _clamped_group_delta(board, dx, dy)
    for item, x, y in starts:
        item.setPos(x + dx, y + dy)
    board.scene.update()
    board.view.viewport().update()


def _formation_center(items) -> tuple[float, float]:
    rows = tuple(items)
    if not rows:
        return 0.0, 0.0
    return (
        sum(item.pos().x() for item in rows) / len(rows),
        sum(item.pos().y() for item in rows) / len(rows),
    )


def _fit_group_to_scene(items) -> None:
    rows = tuple(items)
    if not rows:
        return
    min_shift_x = -float("inf")
    max_shift_x = float("inf")
    min_shift_y = -float("inf")
    max_shift_y = float("inf")
    for item in rows:
        left, right, top, bottom = _group_scene_limits(item)
        x, y = item.pos().x(), item.pos().y()
        min_shift_x = max(min_shift_x, left - x)
        max_shift_x = min(max_shift_x, right - x)
        min_shift_y = max(min_shift_y, top - y)
        max_shift_y = min(max_shift_y, bottom - y)

    shift_x = max(min_shift_x, min(max_shift_x, 0.0))
    shift_y = max(min_shift_y, min(max_shift_y, 0.0))
    if shift_x or shift_y:
        for item in rows:
            item.setPos(item.pos().x() + shift_x, item.pos().y() + shift_y)


def rotate_rainbow(board, degrees: float) -> bool:
    """Rotate the active Rainbow Stack as one piece around its own center."""
    if getattr(board, "_active_formation_key", "") != "rainbow_stacks":
        return False
    items = tuple(getattr(board, "_formation_group_items", ()))
    if not items:
        return False

    cx, cy = _formation_center(items)
    angle = math.radians(float(degrees))
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    for item in items:
        dx = item.pos().x() - cx
        dy = item.pos().y() - cy
        # Screen Y increases downward. Positive degrees therefore rotate
        # clockwise visually, matching clock-face language.
        item.setPos(
            cx + dx * cos_a - dy * sin_a,
            cy + dx * sin_a + dy * cos_a,
        )
    _fit_group_to_scene(items)
    board.scene.update()
    board.view.viewport().update()
    return True


def apply_formation(board, preset_key: str) -> bool:
    """Arrange eight DDs and two healers and bind them as one formation group."""
    preset = _PRESET_BY_KEY.get(str(preset_key or "").strip())
    if preset is None:
        return False

    dps_items = _ensure_role_items(board, "dps", len(preset.dps_positions))
    healer_items = _ensure_role_items(board, "healer", len(preset.healer_positions))

    for index, ((x, y), token) in enumerate(
        zip(preset.dps_positions, dps_items, strict=True),
        start=1,
    ):
        token.label = f"DD {index}"
        token.setPos(x, y)
        token.update()

    for index, ((x, y), token) in enumerate(
        zip(preset.healer_positions, healer_items, strict=True),
        start=1,
    ):
        token.label = f"Healer {index}"
        token.setPos(x, y)
        token.update()

    _set_formation_group(board, preset.key, [*dps_items, *healer_items])
    board.scene.update()
    board.view.viewport().update()
    return True


def _top_level_panel(widget, board):
    current = widget
    while current is not None:
        parent = current.parentWidget()
        if parent is board:
            return current
        current = parent
    return None


def _set_more_tools_visible(board, visible: bool) -> None:
    for panel in tuple(getattr(board, "_raid_map_advanced_panels", ())):
        panel.setVisible(bool(visible))
    button = getattr(board, "raid_map_more_tools_button", None)
    if button is not None:
        button.setText("Less Tools ▴" if visible else "More Tools ▾")


def install() -> None:
    """Add compact formation controls and group behavior to Urban Wilderness Raid Map."""
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components import encounter_board as encounter_board

    original_init = encounter_board.EncounterBoard.__init__
    original_token_press = encounter_board.EncounterToken.mousePressEvent
    original_token_move = encounter_board.EncounterToken.mouseMoveEvent
    original_token_release = encounter_board.EncounterToken.mouseReleaseEvent

    def token_press_with_group(self, event):
        board = getattr(self, "_formation_board", None)
        if (
            board is not None
            and bool(getattr(board, "_formation_group_locked", False))
            and self in tuple(getattr(board, "_formation_group_items", ()))
        ):
            board._formation_drag_anchor = self
            board._formation_drag_anchor_start = (self.pos().x(), self.pos().y())
            board._formation_drag_start_positions = tuple(
                (item, item.pos().x(), item.pos().y())
                for item in board._formation_group_items
            )
        original_token_press(self, event)

    def token_move_with_group(self, event):
        original_token_move(self, event)
        board = getattr(self, "_formation_board", None)
        if board is not None:
            _move_locked_group(board, self)

    def token_release_with_group(self, event):
        original_token_release(self, event)
        board = getattr(self, "_formation_board", None)
        if board is not None:
            _move_locked_group(board, self)
            board._formation_drag_anchor = None
            board._formation_drag_anchor_start = None
            board._formation_drag_start_positions = ()

    def init_with_formations(self, parent=None):
        self._formation_group_items = []
        self._formation_group_locked = True
        self._active_formation_key = ""
        self._formation_drag_anchor = None
        self._formation_drag_anchor_start = None
        self._formation_drag_start_positions = ()

        original_init(self, parent)

        app = QApplication.instance()
        if app is None or app.property("visualTheme") != VISUAL_THEME_URBAN_WILDERNESS:
            return

        root = self.layout()
        if root is None:
            return

        self.formation_combo = QComboBox()
        self.formation_combo.setObjectName("encounterFormationCombo")
        for preset in FORMATION_PRESETS:
            self.formation_combo.addItem(preset.label, preset.key)
        self.formation_combo.setMinimumWidth(150)
        self.formation_combo.setToolTip(
            "Choose a reusable raid stack. Apply creates/positions 8 DDs and 2 healers."
        )

        formation_label = QLabel("FORMATIONS")
        formation_label.setProperty("sidebarHeading", True)

        apply_button = QPushButton("✓ Apply")
        apply_button.setObjectName("encounterApplyFormationButton")
        apply_button.setToolTip("Apply the selected stack formation.")
        apply_button.clicked.connect(
            lambda _checked=False: self.apply_formation(
                str(self.formation_combo.currentData() or "")
            )
        )

        self.formation_lock_button = QPushButton("🔒")
        self.formation_lock_button.setCheckable(True)
        self.formation_lock_button.setChecked(True)
        self.formation_lock_button.setFixedWidth(38)
        self.formation_lock_button.toggled.connect(
            lambda checked: _toggle_formation_lock(self, checked)
        )

        self.formation_rotate_left_button = QPushButton("↶ 90°")
        self.formation_rotate_left_button.setToolTip(
            "Rotate the Rainbow Stack 90° counter-clockwise."
        )
        self.formation_rotate_left_button.clicked.connect(
            lambda _checked=False: rotate_rainbow(self, -90.0)
        )

        self.formation_rotate_right_button = QPushButton("↷ 90°")
        self.formation_rotate_right_button.setToolTip(
            "Rotate the Rainbow Stack 90° clockwise."
        )
        self.formation_rotate_right_button.clicked.connect(
            lambda _checked=False: rotate_rainbow(self, 90.0)
        )

        self.raid_map_more_tools_button = QPushButton("More Tools ▾")
        self.raid_map_more_tools_button.setCheckable(True)
        self.raid_map_more_tools_button.setToolTip(
            "Show Timeline, Rename, and Reference controls only when you need them."
        )

        panel = QWidget(self)
        row = QHBoxLayout(panel)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        row.addWidget(formation_label)
        row.addWidget(self.formation_combo)
        row.addWidget(apply_button)
        row.addWidget(self.formation_lock_button)
        row.addWidget(self.formation_rotate_left_button)
        row.addWidget(self.formation_rotate_right_button)
        row.addStretch(1)
        row.addWidget(self.raid_map_more_tools_button)

        # Keep the normal high-frequency controls visible, but collapse the
        # four-row Timeline/Edit/Reference block behind one button. The arena
        # gets the vertical space instead of the toolbar bureaucracy.
        advanced = []
        timeline_combo = getattr(self, "position_timeline_step_combo", None)
        if timeline_combo is not None:
            timeline_panel = _top_level_panel(timeline_combo, self)
            if timeline_panel is not None:
                advanced.append(timeline_panel)
        custom_label = getattr(self, "raid_map_custom_label", None)
        if custom_label is not None:
            label_panel = _top_level_panel(custom_label, self)
            if label_panel is not None and label_panel not in advanced:
                advanced.append(label_panel)
        self._raid_map_advanced_panels = advanced
        self.raid_map_more_tools_button.toggled.connect(
            lambda checked: _set_more_tools_visible(self, checked)
        )
        _set_more_tools_visible(self, False)

        # Base rows are Actors, Mechanics & Areas, Layout & Output. Insert the
        # compact formation row between Mechanics and Layout.
        root.insertWidget(2, panel)

        _set_group_lock_button(self)
        _set_rotation_controls(self)

    encounter_board.EncounterToken.mousePressEvent = token_press_with_group
    encounter_board.EncounterToken.mouseMoveEvent = token_move_with_group
    encounter_board.EncounterToken.mouseReleaseEvent = token_release_with_group
    encounter_board.EncounterBoard.__init__ = init_with_formations
    encounter_board.EncounterBoard.apply_formation = apply_formation
    encounter_board.EncounterBoard.rotate_rainbow_formation = rotate_rainbow

    _INSTALLED = True
