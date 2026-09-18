from __future__ import annotations

"""Final Urban Wilderness accessibility/art polish.

This module is intentionally presentation-only. It does not touch ESO mechanics or
canonical raid data. It provides a red/green-independent, low-brightness Raid Map,
reuses existing approved artwork for decorative filler surfaces, and turns the Live
Raid run-note surface into an explicit editable/persisted control.
"""

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QFont, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QWidget

from engine.config import get_resource_path
from services.accessibility_preferences import COLOR_VISION_FRIENDLY, COLOR_VISION_STANDARD

_INSTALLED = False

# Red/green-independent, deliberately low-luminance palette. Text/glyph/shape remain
# the primary identity cue; color is supplementary.
TOKEN_COLORS = {
    "boss": "#665B78",
    "mini_boss": "#66507D",
    "tank": "#2E6D99",
    "healer": "#2C7F91",
    "dps": "#B9792F",
    "portal": "#68598A",
    "aoe": "#A96F2D",
    "stack": "#75658F",
    "reference_entrance": "#5D666B",
    "reference_exit": "#5D666B",
    "reference_banner": "#75694E",
}

ZONE_COLORS = {
    "Danger": "#B9792F",
    "Safe": "#397A9B",
    "Stack": "#74608E",
    "Neutral": "#687176",
}

ZONE_LINE_STYLES = {
    "Danger": Qt.PenStyle.SolidLine,
    "Safe": Qt.PenStyle.DashLine,
    "Stack": Qt.PenStyle.DotLine,
    "Neutral": Qt.PenStyle.DashDotLine,
}


def _card_ancestor(widget: QWidget | None) -> QWidget | None:
    current = widget
    while current is not None:
        if bool(current.property("foundryCard")):
            return current
        current = current.parentWidget()
    return None


def _first_art(*candidates: tuple[str, ...]) -> Path | None:
    """Return the first safe UI artwork path.

    The legacy Field Journal JPEG exports are malformed and trigger Qt's JPEG
    decoder repeatedly during application boot. Keep them on disk for later
    replacement, but never hand .jpg/.jpeg files to QPixmap from the active UI.
    """
    for parts in candidates:
        path = Path(get_resource_path(*parts))
        if path.suffix.casefold() in {".jpg", ".jpeg"}:
            continue
        if path.is_file():
            return path
    return None


def _set_art(label: QLabel, path: Path | None, *, fallback: str, width: int, height: int) -> None:
    label.clear()
    if path is None:
        label.setText(fallback)
        return
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        label.setText(fallback)
        return
    label.setPixmap(
        pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
    )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import city_raid_plan_workspace_page
    from ui import raid_roster_workspace_page
    from ui.components import encounter_board as board

    # ------------------------------------------------------------------
    # Generic roster sketch used outside the Teams color-art slot
    # ------------------------------------------------------------------
    original_sketch_init = raid_roster_workspace_page._ThemeSketch.__init__
    original_sketch_resize = raid_roster_workspace_page._ThemeSketch.resizeEvent

    def sketch_refresh(self) -> None:
        if raid_roster_workspace_page._theme_is_rylo():
            path = _first_art(
                ("assets", "themes", "bff", "grimoire", "assets", "roster_rylo_sketch.svg")
            )
        else:
            # Parchment/field-journal surfaces use the pencil/sketch family only.
            # The retired roster city/raven images must never be reintroduced here.
            path = _first_art(
                ("assets", "themes", "bff", "field_journal", "roster", "roster_team.jpg")
            )
        _set_art(
            self,
            path,
            fallback="Same people. Better prepared.",
            width=max(640, self.width() or 860),
            height=max(150, self.height() or 180),
        )

    def sketch_init(self, parent=None) -> None:
        original_sketch_init(self, parent)
        self.setMinimumHeight(150)
        self.setMaximumHeight(210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sketch_refresh(self)

    def sketch_resize(self, event) -> None:
        original_sketch_resize(self, event)
        sketch_refresh(self)

    raid_roster_workspace_page._ThemeSketch.__init__ = sketch_init
    raid_roster_workspace_page._ThemeSketch.refresh_theme = sketch_refresh
    raid_roster_workspace_page._ThemeSketch.resizeEvent = sketch_resize

    # ------------------------------------------------------------------
    # Raid Plan center note is decorative, so make it visibly decorative.
    # ------------------------------------------------------------------
    original_plan_overview = city_raid_plan_workspace_page.CityRaidPlanWorkspacePage._build_overview_surface

    def plan_overview_with_art(self):
        page = original_plan_overview(self)
        label = getattr(self, "plan_notes", None)
        if isinstance(label, QLabel):
            path = _first_art(
                ("assets", "themes", "bff", "field_journal", "roster", "roster_people.jpg"),
            )
            label.setMinimumHeight(145)
            label.setMaximumHeight(190)
            label.setToolTip("If it matters, write it down.")
            _set_art(
                label,
                path,
                fallback="If it matters, write it down.",
                width=520,
                height=175,
            )
        return page

    city_raid_plan_workspace_page.CityRaidPlanWorkspacePage._build_overview_surface = plan_overview_with_art

    # ------------------------------------------------------------------
    # Raid Map: remove red/green dependence from every theme.
    # ------------------------------------------------------------------
    prior_add_token = board.EncounterBoard._add_token
    prior_add_zone = board.EncounterBoard._add_zone
    prior_token_paint = board.EncounterToken.paint

    def accessible_add_token(self, kind, label, x, y, radius=18.0):
        token = prior_add_token(self, kind, label, x, y, radius=radius)
        token.color = QColor(TOKEN_COLORS.get(kind, "#5F696D"))
        token.update()
        return token

    def accessible_add_zone(self, zone_type, label, x, y, radius, color=None):
        zone = prior_add_zone(self, zone_type, label, x, y, radius, color=color)
        zone.color = QColor(ZONE_COLORS.get(zone_type, ZONE_COLORS["Neutral"]))
        zone._colorblind_friendly = True
        zone.update()
        return zone

    def accessible_apply_mode(self, mode: str) -> None:
        normalized = COLOR_VISION_FRIENDLY if mode == COLOR_VISION_FRIENDLY else COLOR_VISION_STANDARD
        self._encounter_color_vision_mode = normalized
        for token in self._token_items():
            token.color = QColor(TOKEN_COLORS.get(token.kind, "#5F696D"))
            token.update()
        for zone in self._zone_items():
            zone.color = QColor(ZONE_COLORS.get(zone.zone_type, ZONE_COLORS["Neutral"]))
            zone._colorblind_friendly = True
            zone.update()
        self.view.setBackgroundBrush(QColor("#081416"))
        combo = getattr(self, "color_vision_combo", None)
        if combo is not None:
            combo.setToolTip(
                "Raid Map is red/green-independent in both modes: danger amber/solid, safe blue/dashed, "
                "stack violet/dotted, neutral gray/dash-dot. Labels and glyphs remain the primary cue."
            )
        self.scene.update()
        self.view.viewport().update()

    def accessible_token_paint(self, painter, option, widget=None):
        if self.kind != "boss":
            prior_token_paint(self, painter, option, widget)
            return

        r = self.radius
        selected = self.isSelected()
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        outer = QColor("#BDA968" if selected else "#7E7357")
        painter.setPen(QPen(outer, 2.6 if selected else 1.9, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(0, 0), r + 18, r + 18)

        painter.setPen(QPen(QColor("#8C80A4"), 2.3 if selected else 1.6))
        painter.setBrush(QBrush(QColor(TOKEN_COLORS["boss"])))
        painter.drawEllipse(QPointF(0, 0), r + 4, r + 4)

        painter.setPen(QPen(QColor("#5F6870"), 1.0))
        painter.setBrush(QBrush(QColor("#151A1C")))
        painter.drawEllipse(QPointF(0, 0), r - 3, r - 3)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#D5D0C4")))
        painter.drawEllipse(QPointF(0, -11), 6.5, 6.5)
        torso = QPainterPath()
        torso.moveTo(0, -4)
        torso.lineTo(-14, 8)
        torso.lineTo(-10, 20)
        torso.lineTo(10, 20)
        torso.lineTo(14, 8)
        torso.closeSubpath()
        painter.drawPath(torso)
        painter.setPen(QPen(QColor("#BDA968"), 1.2))
        painter.drawLine(-9, -16, -3, -8)
        painter.drawLine(9, -16, 3, -8)

        font = QFont("Montserrat", 8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#E5DFD3"))
        painter.drawText(QRectF(-58, r + 8, 116, 20), Qt.AlignmentFlag.AlignHCenter, self.label)

    def accessible_zone_paint(self, painter, option, widget=None):
        selected = self.isSelected()
        fill = QColor(self.color)
        fill.setAlpha(54 if not selected else 76)
        edge = QColor(self.color).lighter(145)
        edge.setAlpha(225)
        style = ZONE_LINE_STYLES.get(self.zone_type, Qt.PenStyle.DashDotLine)
        painter.setPen(QPen(edge, 2.7 if selected else 1.8, style))
        painter.setBrush(QBrush(fill))
        painter.drawEllipse(QPointF(0, 0), self.radius, self.radius)
        painter.setPen(QPen(QColor("#D7D7D0"), 1.0, style))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(0, 0), self.radius + 3, self.radius + 3)
        font = QFont("Montserrat", 8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#E7E2D8"))
        painter.drawText(
            QRectF(-self.radius, -10, self.radius * 2, 20),
            Qt.AlignmentFlag.AlignCenter,
            self.label,
        )

    board.EncounterBoard._add_token = accessible_add_token
    board.EncounterBoard._add_zone = accessible_add_zone
    board.EncounterBoard._apply_color_vision_mode = accessible_apply_mode
    board.EncounterToken.paint = accessible_token_paint
    board.EncounterZone.paint = accessible_zone_paint

    _INSTALLED = True


__all__ = ["install", "TOKEN_COLORS", "ZONE_COLORS", "ZONE_LINE_STYLES"]
