# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_relationship_graph.py
#
# Purpose:
# Generic canvas of positioned, labeled nodes.
#
# Covers the boss-positioning map (players placed around
# an arena) but has no idea what a "portal" or "boss" is
# -- it just places nodes at normalized coordinates,
# optionally over a background image, with optional
# connector arrows and zone overlays. Any future
# "who relates to whom, positioned how" diagram can reuse
# it (e.g. group composition).
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget

from ui.theme.colors import Colors
from ui.theme.fonts import Fonts


class FoundryRelationshipGraph(QWidget):
    """
    A canvas of nodes placed by normalized (0..1) x/y
    coordinate, with optional connectors and zones.

        FoundryRelationshipGraph(
            nodes=[
                {"id": "mt", "label": "MT", "x": 0.35, "y": 0.15,
                 "color": Colors.INFO},
                {"id": "boss", "label": "BOSS", "x": 0.5, "y": 0.05,
                 "color": Colors.ERROR, "radius": 16},
            ],
            connectors=[{"from": "mt", "to": "boss", "color": Colors.GOLD}],
            zones=[{"points": [(0.3,0.3),(0.7,0.3),(0.5,0.6)],
                    "color": Colors.SUCCESS}],
            background=QPixmap("arena.png"),  # optional
        )
    """

    def __init__(
        self,
        nodes: list[dict] | None = None,
        connectors: list[dict] | None = None,
        zones: list[dict] | None = None,
        background: QPixmap | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._nodes = nodes or []
        self._connectors = connectors or []
        self._zones = zones or []
        self._background = background

        self.setMinimumSize(200, 200)

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_data(
        self,
        nodes: list[dict] | None = None,
        connectors: list[dict] | None = None,
        zones: list[dict] | None = None,
        background: QPixmap | None = None,
    ):

        if nodes is not None:
            self._nodes = nodes

        if connectors is not None:
            self._connectors = connectors

        if zones is not None:
            self._zones = zones

        if background is not None:
            self._background = background

        self.update()

    # --------------------------------------------------
    # Geometry
    # --------------------------------------------------

    def _canvas_rect(self) -> QRectF:
        """The largest centered square, since arena-style
        graphs read most naturally at 1:1."""

        side = min(self.width(), self.height())

        x = (self.width() - side) / 2
        y = (self.height() - side) / 2

        return QRectF(x, y, side, side)

    def _point(self, rect: QRectF, x: float, y: float) -> QPointF:

        return QPointF(
            rect.left() + x * rect.width(),
            rect.top() + y * rect.height(),
        )

    def _node_by_id(self, node_id):

        for n in self._nodes:

            if n.get("id") == node_id:
                return n

        return None

    # --------------------------------------------------
    # Painting
    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        rect = self._canvas_rect()

        # Background
        if self._background is not None and not self._background.isNull():

            painter.drawPixmap(
                rect.toRect(),
                self._background,
            )

        else:

            painter.setPen(
                QPen(QColor(Colors.BORDER))
            )

            painter.setBrush(
                QBrush(QColor(Colors.SURFACE))
            )

            painter.drawEllipse(rect)

        # Zones
        for zone in self._zones:

            color = QColor(zone.get("color", Colors.SUCCESS))

            color.setAlpha(60)

            polygon = QPolygonF(
                [
                    self._point(rect, px, py)
                    for px, py in zone.get("points", [])
                ]
            )

            painter.setPen(Qt.PenStyle.NoPen)

            painter.setBrush(QBrush(color))

            painter.drawPolygon(polygon)

        # Connectors
        for conn in self._connectors:

            a = self._node_by_id(conn.get("from"))

            b = self._node_by_id(conn.get("to"))

            if not a or not b:
                continue

            pen = QPen(
                QColor(conn.get("color", Colors.GOLD)),
                2,
                Qt.PenStyle.DashLine,
            )

            painter.setPen(pen)

            painter.drawLine(
                self._point(rect, a["x"], a["y"]),
                self._point(rect, b["x"], b["y"]),
            )

        # Nodes
        font = Fonts.sidebar()

        font.setPointSize(8)

        painter.setFont(font)

        for node in self._nodes:

            center = self._point(
                rect, node.get("x", 0.5), node.get("y", 0.5)
            )

            radius = node.get("radius", 14)

            color = QColor(
                node.get("color", Colors.GOLD)
            )

            painter.setPen(
                QPen(color, 2)
            )

            painter.setBrush(
                QBrush(color.darker(160))
            )

            painter.drawEllipse(center, radius, radius)

            painter.setPen(QColor(Colors.TEXT))

            painter.drawText(
                QRectF(
                    center.x() - 30,
                    center.y() - 8,
                    60,
                    16,
                ),
                Qt.AlignmentFlag.AlignCenter,
                node.get("label", ""),
            )
