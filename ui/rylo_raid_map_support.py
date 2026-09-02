from __future__ import annotations

"""Theme the Encounters Raid Map for Rylo without changing Foundry behavior."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QFont, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QApplication

from services.accessibility_preferences import VISUAL_THEME_RYLO

_INSTALLED = False

RYLO_TOKEN_COLORS = {
    "boss": "#6B2A2C",
    "mini_boss": "#765A88",
    "tank": "#347DB3",
    "healer": "#2F8FA5",
    "dps": "#D96C1E",
    "portal": "#7764A8",
    "aoe": "#E17C24",
    "stack": "#8066A6",
}

RYLO_ZONE_COLORS = {
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


def _is_rylo() -> bool:
    app = QApplication.instance()
    return bool(app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components import encounter_board as board
    from ui.theme.theme_manager import ThemeManager

    original_draw_arena = board.EncounterBoard._draw_arena
    original_token_paint = board.EncounterToken.paint
    original_zone_paint = board.EncounterZone.paint
    original_apply_mode = board.EncounterBoard._apply_color_vision_mode
    original_theme_apply = ThemeManager.apply

    def draw_arena_theme_aware(self) -> None:
        if not _is_rylo():
            original_draw_arena(self)
            return

        self.scene.clear()
        shell = QColor("#0B0B0D")
        stone_dark = QColor("#111214")
        stone_mid = QColor("#18191B")
        stone_light = QColor("#202225")
        seam = QColor("#373A3E")
        steel = QColor("#575B60")
        steel_faint = QColor("#414449")
        brick = QColor("#6E1F24")

        self.scene.addRect(
            8, 8, board.SCENE_W - 16, board.SCENE_H - 16,
            QPen(steel, 2), QBrush(shell),
        ).setZValue(-120)

        self.scene.addRect(78, 184, 92, 172, QPen(seam, 1.2), QBrush(stone_mid)).setZValue(-112)
        self.scene.addRect(790, 184, 92, 172, QPen(seam, 1.2), QBrush(stone_mid)).setZValue(-112)

        outer = QPolygonF([
            QPointF(210, 62), QPointF(750, 62), QPointF(862, 160), QPointF(862, 380),
            QPointF(750, 478), QPointF(210, 478), QPointF(98, 380), QPointF(98, 160),
        ])
        self.scene.addPolygon(outer, QPen(steel, 2), QBrush(stone_dark)).setZValue(-110)

        inner = QPolygonF([
            QPointF(260, 110), QPointF(700, 110), QPointF(790, 190), QPointF(790, 350),
            QPointF(700, 430), QPointF(260, 430), QPointF(170, 350), QPointF(170, 190),
        ])
        self.scene.addPolygon(inner, QPen(QColor("#4A4D51"), 1.2), QBrush(stone_mid)).setZValue(-100)

        self.scene.addEllipse(318, 170, 324, 200, QPen(steel_faint, 1.5), QBrush(stone_light)).setZValue(-95)
        self.scene.addEllipse(382, 215, 196, 110, QPen(brick, 1.2), QBrush(QColor("#151618"))).setZValue(-90)

        self.scene.addLine(480, 104, 480, 436, QPen(seam, 1.0)).setZValue(-88)
        self.scene.addLine(178, 270, 782, 270, QPen(seam, 1.0)).setZValue(-88)
        self.scene.addLine(250, 145, 710, 395, QPen(QColor("#2A2C2F"), 0.8)).setZValue(-88)
        self.scene.addLine(710, 145, 250, 395, QPen(QColor("#2A2C2F"), 0.8)).setZValue(-88)

        for x, y in ((230, 140), (480, 118), (730, 140), (198, 270), (762, 270), (230, 400), (480, 422), (730, 400)):
            self.scene.addEllipse(x - 9, y - 9, 18, 18, QPen(steel_faint, 1.0), QBrush(QColor("#202225"))).setZValue(-84)

        for x, y in ((125, 88), (835, 88), (125, 452), (835, 452)):
            self.scene.addEllipse(x - 7, y - 7, 14, 14, QPen(steel_faint, 1.0), QBrush(QColor("#1C1E20"))).setZValue(-82)

        title = self.scene.addText("ENCOUNTER ARENA")
        title.setDefaultTextColor(QColor("#A9AAAC"))
        title.setFont(QFont("Bahnschrift SemiCondensed", 10, QFont.Weight.Bold))
        title.setPos(410, 24)
        title.setZValue(-70)

    def token_paint_theme_aware(self, painter, option, widget=None):
        if not _is_rylo():
            original_token_paint(self, painter, option, widget)
            return

        r = self.radius
        selected = self.isSelected()
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)
        steel = QColor("#D0D2D4" if selected else "#7A7E82")
        text = QColor("#E4E4E2")
        fill = QColor(RYLO_TOKEN_COLORS.get(self.kind, "#666A6E"))

        if self.kind == "boss":
            painter.setPen(QPen(QColor("#8B2E32"), 2.4 if selected else 1.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(0, 0), r + 18, r + 18)
            painter.setPen(QPen(steel, 2.6 if selected else 1.7))
            painter.setBrush(QBrush(fill))
            painter.drawEllipse(QPointF(0, 0), r + 4, r + 4)
            painter.setPen(QPen(QColor("#45484C"), 1.0))
            painter.setBrush(QBrush(QColor("#151618")))
            painter.drawEllipse(QPointF(0, 0), r - 3, r - 3)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#D0D2D4")))
            painter.drawEllipse(QPointF(0, -11), 6.5, 6.5)
            torso = QPainterPath()
            torso.moveTo(0, -4); torso.lineTo(-14, 8); torso.lineTo(-10, 20); torso.lineTo(10, 20); torso.lineTo(14, 8); torso.closeSubpath()
            painter.drawPath(torso)
            painter.setPen(QPen(QColor("#8B2E32"), 1.4))
            painter.drawLine(-9, -16, -3, -8); painter.drawLine(9, -16, 3, -8)
            font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(font); painter.setPen(text)
            painter.drawText(QRectF(-58, r + 8, 116, 20), Qt.AlignmentFlag.AlignHCenter, self.label)
            return

        if self.kind == "mini_boss":
            painter.setPen(QPen(steel, 2.3 if selected else 1.6))
            painter.setBrush(QBrush(fill))
            diamond = QPolygonF([QPointF(0, -r - 4), QPointF(r + 4, 0), QPointF(0, r + 4), QPointF(-r - 4, 0)])
            painter.drawPolygon(diamond)
            painter.setPen(QPen(QColor("#45484C"), 1.0))
            painter.setBrush(QBrush(QColor("#151618")))
            painter.drawEllipse(QPointF(0, 0), r - 5, r - 5)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold)); painter.setPen(text)
            painter.drawText(QRectF(-r, -r, r * 2, r * 2), Qt.AlignmentFlag.AlignCenter, "M")
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(QRectF(-58, r + 7, 116, 18), Qt.AlignmentFlag.AlignHCenter, self.label)
            return

        painter.setPen(QPen(steel, 2.3 if selected else 1.5))
        painter.setBrush(QBrush(fill))
        painter.drawEllipse(QPointF(0, 0), r, r)
        glyph = {"tank": "T", "healer": "H", "dps": "D", "portal": "P", "aoe": "!", "stack": "+"}.get(self.kind, "•")
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold)); painter.setPen(QColor("#F1F1EF"))
        painter.drawText(QRectF(-r, -r, r * 2, r * 2), Qt.AlignmentFlag.AlignCenter, glyph)
        painter.setFont(QFont("Segoe UI", 8)); painter.setPen(text)
        painter.drawText(QRectF(-58, r + 4, 116, 18), Qt.AlignmentFlag.AlignHCenter, self.label)

    def zone_paint_theme_aware(self, painter, option, widget=None):
        if not _is_rylo():
            original_zone_paint(self, painter, option, widget)
            return

        selected = self.isSelected()
        fill = QColor(self.color)
        fill.setAlpha(68 if not selected else 92)
        edge = QColor(self.color).lighter(145)
        edge.setAlpha(235)
        friendly = bool(getattr(self, "_colorblind_friendly", False))
        style = ZONE_LINE_STYLES.get(self.zone_type, Qt.PenStyle.SolidLine) if friendly else (Qt.PenStyle.DashLine if selected else Qt.PenStyle.SolidLine)
        painter.setPen(QPen(edge, 2.8 if selected else 1.8, style))
        painter.setBrush(QBrush(fill))
        painter.drawEllipse(QPointF(0, 0), self.radius, self.radius)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#ECECEA"))
        painter.drawText(QRectF(-self.radius, -10, self.radius * 2, 20), Qt.AlignmentFlag.AlignCenter, self.label)
        if friendly:
            painter.setPen(QPen(QColor("#D7D8DA"), 1.0, style))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(0, 0), self.radius + 3, self.radius + 3)

    def apply_mode_theme_aware(self, mode: str) -> None:
        original_apply_mode(self, mode)
        if not _is_rylo():
            return
        for token in self._token_items():
            token.color = QColor(RYLO_TOKEN_COLORS.get(token.kind, "#666A6E"))
            token.update()
        for zone in self._zone_items():
            zone.color = QColor(RYLO_ZONE_COLORS.get(zone.zone_type, RYLO_ZONE_COLORS["Neutral"]))
            zone.update()
        self.view.setBackgroundBrush(QColor("#0B0B0D"))
        self.scene.update(); self.view.viewport().update()

    def refresh_board_theme(self) -> None:
        saved_tokens = [item.to_dict() for item in self._token_items()]
        saved_zones = [item.to_dict() for item in self._zone_items()]
        background = getattr(self, "_raid_map_background_path", None)
        self._draw_arena()
        for payload in saved_zones:
            zone = self._add_zone(
                payload["zone_type"], payload["label"],
                float(payload["x"]) * board.SCENE_W,
                float(payload["y"]) * board.SCENE_H,
                float(payload["radius"]),
                color=payload.get("color"),
            )
            zone._colorblind_friendly = getattr(self, "_encounter_color_vision_mode", "") == "colorblind_friendly"
        for payload in saved_tokens:
            self._add_token(
                payload["kind"], payload["label"],
                float(payload["x"]) * board.SCENE_W,
                float(payload["y"]) * board.SCENE_H,
                radius=float(payload.get("radius", 18.0)),
            )
        if background and hasattr(self, "_set_background_map"):
            self._set_background_map(background)
        mode = getattr(self, "_encounter_color_vision_mode", "standard")
        self._apply_color_vision_mode(mode)
        self.view.fit_arena()

    board.EncounterBoard._draw_arena = draw_arena_theme_aware
    board.EncounterToken.paint = token_paint_theme_aware
    board.EncounterZone.paint = zone_paint_theme_aware
    board.EncounterBoard._apply_color_vision_mode = apply_mode_theme_aware
    board.EncounterBoard.refresh_visual_theme = refresh_board_theme

    def apply_with_raid_map(self, app: QApplication) -> None:
        original_theme_apply(self, app)
        for top in app.topLevelWidgets():
            for encounter_board in top.findChildren(board.EncounterBoard):
                encounter_board.refresh_visual_theme()

    ThemeManager.apply = apply_with_raid_map
    _INSTALLED = True
