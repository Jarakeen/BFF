from __future__ import annotations

"""Color-vision and Raid Map UX support for Encounters tactical mapping."""

import json
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.accessibility_preferences import (
    AccessibilityPreferences,
    COLOR_VISION_FRIENDLY,
    COLOR_VISION_STANDARD,
)

_INSTALLED = False

STANDARD_TOKEN_COLORS = {
    "boss": "#4A2420",
    "mini_boss": "#63372A",
    "tank": "#24445A",
    "healer": "#365A3E",
    "dps": "#5A302C",
    "portal": "#41305A",
    "aoe": "#673B1E",
    "stack": "#586028",
}

COLORBLIND_TOKEN_COLORS = {
    "boss": "#8A4F22",
    "mini_boss": "#6F568A",
    "tank": "#2E6FA3",
    "healer": "#2586A8",
    "dps": "#D96C1E",
    "portal": "#6659A8",
    "aoe": "#E17C24",
    "stack": "#8066A6",
}

STANDARD_ZONE_COLORS = {
    "Danger": "#8A351F",
    "Safe": "#2E6651",
    "Stack": "#64722E",
    "Neutral": "#375F69",
}

COLORBLIND_ZONE_COLORS = {
    "Danger": "#D96C1E",
    "Safe": "#347DB3",
    "Stack": "#8066A6",
    "Neutral": "#777B7E",
}

ZONE_LINE_STYLES = {
    "Danger": Qt.PenStyle.SolidLine,
    "Safe": Qt.PenStyle.DashLine,
    "Stack": Qt.PenStyle.DotLine,
    "Neutral": Qt.PenStyle.DashDotLine,
}


def install() -> None:
    """Install Raid Map naming, uploads, and persistent color-vision support."""
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components import encounter_board as board
    from ui.components.foundry_card import FoundryCard
    from ui import encounters_page

    original_init = board.EncounterBoard.__init__
    original_add_token = board.EncounterBoard._add_token
    original_add_zone = board.EncounterBoard._add_zone
    original_zone_paint = board.EncounterZone.paint
    original_save_state = board.EncounterBoard.save_state
    original_load_state = board.EncounterBoard.load_state

    def palette_for(mode: str):
        if mode == COLOR_VISION_FRIENDLY:
            return COLORBLIND_TOKEN_COLORS, COLORBLIND_ZONE_COLORS
        return STANDARD_TOKEN_COLORS, STANDARD_ZONE_COLORS

    def apply_color_vision_mode(self, mode: str) -> None:
        normalized = (
            COLOR_VISION_FRIENDLY
            if mode == COLOR_VISION_FRIENDLY
            else COLOR_VISION_STANDARD
        )
        self._encounter_color_vision_mode = normalized
        token_colors, zone_colors = palette_for(normalized)
        friendly = normalized == COLOR_VISION_FRIENDLY

        for token in self._token_items():
            token.color = QColor(token_colors.get(token.kind, "#5B6063"))
            token.update()

        for zone in self._zone_items():
            zone.color = QColor(zone_colors.get(zone.zone_type, zone_colors["Neutral"]))
            zone._colorblind_friendly = friendly
            zone.update()

        self.view.setBackgroundBrush(QColor("#0E1012" if friendly else "#061315"))
        if hasattr(self, "color_vision_combo"):
            if friendly:
                self.color_vision_combo.setToolTip(
                    "Colorblind Friendly: Danger orange/solid, Safe blue/dashed, "
                    "Stack purple/dotted, Neutral gray/dash-dot."
                )
            else:
                self.color_vision_combo.setToolTip(
                    "Standard encounter colors. Marker labels and glyphs remain visible alongside color."
                )
        self.scene.update()
        self.view.viewport().update()

    def color_vision_changed(self, _index: int) -> None:
        mode = str(self.color_vision_combo.currentData() or COLOR_VISION_STANDARD)
        mode = self._accessibility_preferences.set_color_vision_mode(mode)
        apply_color_vision_mode(self, mode)

    @staticmethod
    def _button_by_text(widget, text: str):
        for button in widget.findChildren(QPushButton):
            if button.text() == text:
                return button
        return None

    def _install_tooltips(self) -> None:
        self.boss_mode.setToolTip("Choose 1 Boss or 2 Bosses. Use 2 Bosses for paired encounters such as twins.")
        self.mini_boss_button.setToolTip("Add a mini-boss marker. Up to 6 mini-bosses may be placed.")
        self.zone_type_combo.setToolTip("Choose the circle zone type: Danger, Safe, Stack, or Neutral.")
        self.zone_size_combo.setToolTip("Choose a preset size for the selected or next circle zone.")
        self.zone_radius_spin.setToolTip("Set the radius of the selected or next circle zone.")
        self.view.setToolTip("Drag markers and circle zones to position them. Use the mouse wheel to zoom.")

        help_text = {
            "+ Tank": "Add a tank marker to Raid Map.",
            "+ Healer": "Add a healer marker to Raid Map.",
            "+ DD": "Add a damage-dealer marker or DD stack to Raid Map.",
            "+ Portal": "Add a portal marker to Raid Map.",
            "+ AOE": "Add an AOE marker to Raid Map.",
            "+ Stack": "Add a stack-point marker to Raid Map.",
            "Delete Selected": "Remove the currently selected marker or circle zone.",
            "Fit Arena": "Fit the entire Raid Map in the visible board area.",
            "+ Circle Zone": "Add a resizable circle zone using the selected type and radius.",
            "Upload Map": "Import a PNG, JPG, JPEG, or WebP image as the Raid Map background.",
            "Replace Map": "Replace the current Raid Map background image.",
            "Remove Map": "Remove the uploaded background and return to the built-in blank arena.",
            "Save Layout": "Save the current editable Raid Map layout and background reference.",
            "Capture Positioning": "Capture the Raid Map image used by the Assignments positioning preview.",
        }
        for text, tooltip in help_text.items():
            button = _button_by_text(self, text)
            if button is not None:
                button.setToolTip(tooltip)

    def _raid_map_dir(self) -> Path:
        path = self.data_dir / "raid_maps"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _background_relative_path(self) -> str:
        path = getattr(self, "_raid_map_background_path", None)
        if not path:
            return ""
        try:
            return str(Path(path).resolve().relative_to(self.data_dir.resolve())).replace("\\", "/")
        except ValueError:
            return str(Path(path))

    def _clear_background_item(self) -> None:
        item = getattr(self, "_raid_map_background_item", None)
        if item is not None and item.scene() is self.scene:
            self.scene.removeItem(item)
        self._raid_map_background_item = None

    def _set_background_map(self, path: str | Path | None) -> bool:
        _clear_background_item(self)
        self._raid_map_background_path = None

        if not path:
            _refresh_map_buttons(self)
            self.scene.update()
            return True

        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.data_dir / candidate
        if not candidate.exists():
            _refresh_map_buttons(self)
            return False

        pixmap = QPixmap(str(candidate))
        if pixmap.isNull():
            _refresh_map_buttons(self)
            return False

        scaled = pixmap.scaled(
            int(board.SCENE_W),
            int(board.SCENE_H),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        item = self.scene.addPixmap(scaled)
        item.setPos(
            (board.SCENE_W - scaled.width()) / 2.0,
            (board.SCENE_H - scaled.height()) / 2.0,
        )
        # Above the built-in dungeon floor, below every mechanic overlay.
        item.setZValue(-60)
        self._raid_map_background_item = item
        self._raid_map_background_path = candidate
        _refresh_map_buttons(self)
        self.scene.update()
        self.view.viewport().update()
        return True

    def _unique_import_path(self, source: Path) -> Path:
        folder = _raid_map_dir(self)
        stem = source.stem.strip() or "raid_map"
        suffix = source.suffix.lower() or ".png"
        candidate = folder / f"{stem}{suffix}"
        counter = 2
        while candidate.exists() and candidate.resolve() != source.resolve():
            candidate = folder / f"{stem}_{counter}{suffix}"
            counter += 1
        return candidate

    def _choose_background_map(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Raid Map",
            "",
            "Map Images (*.png *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if not filename:
            return

        source = Path(filename)
        destination = _unique_import_path(self, source)
        try:
            if source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
        except OSError:
            return

        if _set_background_map(self, destination):
            save_state_with_background(self)

    def _remove_background_map(self) -> None:
        _set_background_map(self, None)
        save_state_with_background(self)

    def _refresh_map_buttons(self) -> None:
        has_map = bool(getattr(self, "_raid_map_background_path", None))
        if hasattr(self, "upload_map_button"):
            self.upload_map_button.setText("Replace Map" if has_map else "Upload Map")
            self.upload_map_button.setToolTip(
                "Replace the current Raid Map background image."
                if has_map
                else "Import a PNG, JPG, JPEG, or WebP image as the Raid Map background."
            )
        if hasattr(self, "remove_map_button"):
            self.remove_map_button.setEnabled(has_map)

    def save_state_with_background(self) -> None:
        original_save_state(self)
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return
        payload["background_map"] = _background_relative_path(self)
        self.state_path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    def load_state_with_background(self) -> bool:
        loaded = original_load_state(self)
        background = ""
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            background = str(payload.get("background_map", "") or "").strip()
        except (OSError, json.JSONDecodeError, TypeError):
            background = ""
        _set_background_map(self, background or None)
        return loaded

    def init_with_accessibility(self, parent=None):
        self._raid_map_background_item = None
        self._raid_map_background_path = None
        original_init(self, parent)

        self._accessibility_preferences = AccessibilityPreferences()
        mode = self._accessibility_preferences.color_vision_mode()

        self.color_vision_combo = QComboBox()
        self.color_vision_combo.setObjectName("encounterColorVisionCombo")
        self.color_vision_combo.addItem("Standard", COLOR_VISION_STANDARD)
        self.color_vision_combo.addItem("Colorblind Friendly", COLOR_VISION_FRIENDLY)
        index = self.color_vision_combo.findData(mode)
        self.color_vision_combo.setCurrentIndex(index if index >= 0 else 0)
        self.color_vision_combo.currentIndexChanged.connect(
            lambda i: color_vision_changed(self, i)
        )
        self.color_vision_combo.setMinimumWidth(150)

        # Keep the board controls to exactly two horizontal rows.
        layout = self.layout()
        primary_toolbar = None
        zone_toolbar = None
        hint = None
        if layout is not None:
            if layout.count() > 0:
                primary_toolbar = layout.itemAt(0).layout()
            if layout.count() > 1:
                zone_toolbar = layout.itemAt(1).layout()
            if layout.count() > 2:
                hint = layout.itemAt(2).widget()

        if primary_toolbar is not None:
            color_label = QLabel("COLOR VISION")
            color_label.setProperty("sidebarHeading", True)
            primary_toolbar.insertWidget(0, self.color_vision_combo)
            primary_toolbar.insertWidget(0, color_label)

        # The old helper paragraph becomes mouse-over help on the controls.
        if hint is not None:
            hint.hide()

        if primary_toolbar is not None and zone_toolbar is not None:
            save_button = _button_by_text(self, "Save Layout")
            capture_button = _button_by_text(self, "Capture Positioning")
            for button in (save_button, capture_button):
                if button is not None:
                    primary_toolbar.removeWidget(button)

            # Background controls live on row 2 without creating another toolbar.
            self.upload_map_button = QPushButton("Upload Map")
            self.upload_map_button.clicked.connect(lambda: _choose_background_map(self))
            self.remove_map_button = QPushButton("Remove Map")
            self.remove_map_button.clicked.connect(lambda: _remove_background_map(self))

            zone_toolbar.addStretch(1)
            zone_toolbar.addWidget(self.upload_map_button)
            zone_toolbar.addWidget(self.remove_map_button)
            if save_button is not None:
                zone_toolbar.addWidget(save_button)
            if capture_button is not None:
                zone_toolbar.addWidget(capture_button)

        _refresh_map_buttons(self)
        _install_tooltips(self)
        apply_color_vision_mode(self, mode)

    def add_token_with_palette(
        self,
        kind: str,
        label: str,
        x: float,
        y: float,
        radius: float = 18.0,
    ):
        token = original_add_token(self, kind, label, x, y, radius=radius)
        mode = getattr(self, "_encounter_color_vision_mode", COLOR_VISION_STANDARD)
        token_colors, _ = palette_for(mode)
        token.color = QColor(token_colors.get(kind, "#5B6063"))
        token.update()
        return token

    def add_zone_with_palette(
        self,
        zone_type: str,
        label: str,
        x: float,
        y: float,
        radius: float,
        color: str | None = None,
    ):
        zone = original_add_zone(
            self,
            zone_type,
            label,
            x,
            y,
            radius,
            color=color,
        )
        mode = getattr(self, "_encounter_color_vision_mode", COLOR_VISION_STANDARD)
        _, zone_colors = palette_for(mode)
        zone.color = QColor(zone_colors.get(zone_type, zone_colors["Neutral"]))
        zone._colorblind_friendly = mode == COLOR_VISION_FRIENDLY
        zone.update()
        return zone

    def paint_zone_with_pattern(self, painter, option, widget=None):
        original_zone_paint(self, painter, option, widget)
        if not getattr(self, "_colorblind_friendly", False):
            return

        edge = QColor(self.color).lighter(145)
        edge.setAlpha(245)
        pen = QPen(
            edge,
            2.8,
            ZONE_LINE_STYLES.get(self.zone_type, Qt.PenStyle.DashDotLine),
        )
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.drawEllipse(QPointF(0, 0), self.radius + 2, self.radius + 2)

    def raid_map_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        board_card = FoundryCard(
            "Raid Map",
            "treasure-map",
        ).set_watermark("compass", 0.025)
        self.encounter_board = board.EncounterBoard()
        self.encounter_board.snapshotSaved.connect(self._positioning_snapshot_saved)
        board_card.addWidget(self.encounter_board)
        root.addWidget(board_card, 1)

        self._load_positioning_preview(self.encounter_board.snapshot_path)
        return tab

    def build_ui_with_raid_map(self) -> None:
        # Call the original page builder, which now uses raid_map_tab because
        # _mechanics_tab is patched before the page instance is constructed.
        original_page_build_ui(self)
        for index in range(self.section_tabs.count()):
            if self.section_tabs.tabText(index) == "MECHANICS":
                self.section_tabs.setTabText(index, "RAID MAP")
                break

    # QPointF is imported lazily here only to keep the compatibility layer tiny.
    from PySide6.QtCore import QPointF

    original_page_build_ui = encounters_page.EncountersPage._build_ui

    board.EncounterBoard.__init__ = init_with_accessibility
    board.EncounterBoard._apply_color_vision_mode = apply_color_vision_mode
    board.EncounterBoard._add_token = add_token_with_palette
    board.EncounterBoard._add_zone = add_zone_with_palette
    board.EncounterBoard.save_state = save_state_with_background
    board.EncounterBoard.load_state = load_state_with_background
    board.EncounterZone.paint = paint_zone_with_pattern
    encounters_page.EncountersPage._mechanics_tab = raid_map_tab
    encounters_page.EncountersPage._build_ui = build_ui_with_raid_map

    _INSTALLED = True
