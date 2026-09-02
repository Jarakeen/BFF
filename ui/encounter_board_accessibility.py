from __future__ import annotations

"""Color-vision support for Encounters > Mechanics tactical mapping board."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel

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
    """Install a persistent Standard/Colorblind Friendly board mode."""
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components import encounter_board as board

    original_init = board.EncounterBoard.__init__
    original_add_token = board.EncounterBoard._add_token
    original_add_zone = board.EncounterBoard._add_zone
    original_zone_paint = board.EncounterZone.paint

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
        if hasattr(self, "color_vision_key"):
            if friendly:
                self.color_vision_key.setText(
                    "Danger: orange / solid   •   Safe: blue / dashed   •   "
                    "Stack: purple / dotted   •   Neutral: gray / dash-dot"
                )
            else:
                self.color_vision_key.setText(
                    "Standard encounter colors. Labels and marker glyphs remain visible alongside color."
                )
        self.scene.update()
        self.view.viewport().update()

    def color_vision_changed(self, _index: int) -> None:
        mode = str(self.color_vision_combo.currentData() or COLOR_VISION_STANDARD)
        mode = self._accessibility_preferences.set_color_vision_mode(mode)
        apply_color_vision_mode(self, mode)

    def init_with_accessibility(self, parent=None):
        original_init(self, parent)

        self._accessibility_preferences = AccessibilityPreferences()
        mode = self._accessibility_preferences.color_vision_mode()

        row = QHBoxLayout()
        row.setSpacing(6)
        label = QLabel("COLOR VISION")
        label.setProperty("sidebarHeading", True)
        row.addWidget(label)

        self.color_vision_combo = QComboBox()
        self.color_vision_combo.setObjectName("encounterColorVisionCombo")
        self.color_vision_combo.addItem("Standard", COLOR_VISION_STANDARD)
        self.color_vision_combo.addItem("Colorblind Friendly", COLOR_VISION_FRIENDLY)
        index = self.color_vision_combo.findData(mode)
        self.color_vision_combo.setCurrentIndex(index if index >= 0 else 0)
        self.color_vision_combo.currentIndexChanged.connect(
            lambda i: color_vision_changed(self, i)
        )
        row.addWidget(self.color_vision_combo)

        self.color_vision_key = QLabel()
        self.color_vision_key.setProperty("muted", True)
        self.color_vision_key.setWordWrap(True)
        row.addWidget(self.color_vision_key, 1)

        layout = self.layout()
        if layout is not None:
            layout.insertLayout(0, row)

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

    # QPointF is imported lazily here only to keep the compatibility layer tiny.
    from PySide6.QtCore import QPointF

    board.EncounterBoard.__init__ = init_with_accessibility
    board.EncounterBoard._apply_color_vision_mode = apply_color_vision_mode
    board.EncounterBoard._add_token = add_token_with_palette
    board.EncounterBoard._add_zone = add_zone_with_palette
    board.EncounterZone.paint = paint_zone_with_pattern

    _INSTALLED = True
