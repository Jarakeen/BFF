from __future__ import annotations

import json

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QBrush,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir


SCENE_W = 960.0
SCENE_H = 540.0
MAX_MINI_BOSSES = 6

ZONE_PRESETS = {
    "Small": 45.0,
    "Medium": 80.0,
    "Large": 125.0,
}

ZONE_STYLES = {
    "Danger": "#8A351F",
    "Safe": "#2E6651",
    "Stack": "#64722E",
    "Neutral": "#375F69",
}


class EncounterToken(QGraphicsObject):
    """Small draggable encounter marker with a readable label."""

    def __init__(self, kind: str, label: str, color: str, radius: float = 18.0, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.label = label
        self.color = QColor(color)
        self.radius = radius
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setZValue(10)

    def boundingRect(self) -> QRectF:
        """Return the complete painted area so movement never leaves stale pixels."""
        r = self.radius
        if self.kind == "boss":
            outer = r + 22
            top_extra = 12
            label_h = 30
            pad = 6
            return QRectF(
                -outer - pad,
                -outer - top_extra - pad,
                (outer + pad) * 2,
                (outer + pad) * 2 + top_extra + label_h,
            )

        pad = 5
        label_h = 24
        return QRectF(
            -60,
            -r - pad,
            120,
            (r + pad) * 2 + label_h,
        )

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        r = self.radius
        if self.kind == "boss":
            outer = r + 22
            path.addEllipse(QPointF(0, 0), outer, outer)
        else:
            path.addEllipse(QPointF(0, 0), r, r)
        return path

    def paint(self, painter: QPainter, option, widget=None):
        r = self.radius
        selected = self.isSelected()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self.kind == "boss":
            # Restrained danger ring around a more character-like boss marker.
            painter.setPen(QPen(QColor(185, 52, 42, 120), 2.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(0, 0), r + 18, r + 18)

            painter.setPen(
                QPen(
                    QColor("#E0B86A") if selected else QColor("#A1844F"),
                    2.4 if selected else 1.6,
                )
            )
            painter.setBrush(QBrush(QColor("#4A2420")))
            painter.drawEllipse(QPointF(0, 0), r + 4, r + 4)

            painter.setPen(QPen(QColor("#6E4D3E"), 1.0))
            painter.setBrush(QBrush(QColor("#211715")))
            painter.drawEllipse(QPointF(0, 0), r - 3, r - 3)

            # Simple boss silhouette: head, shoulders, torso, and crown/horns.
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#161110")))
            painter.drawEllipse(QPointF(0, -11), 6.5, 6.5)

            torso = QPainterPath()
            torso.moveTo(0, -4)
            torso.lineTo(-14, 8)
            torso.lineTo(-10, 20)
            torso.lineTo(10, 20)
            torso.lineTo(14, 8)
            torso.closeSubpath()
            painter.drawPath(torso)

            painter.setPen(QPen(QColor("#C6A361"), 1.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(-9, -16, -3, -8)
            painter.drawLine(9, -16, 3, -8)

            label_font = QFont("Montserrat", 8)
            label_font.setBold(True)
            painter.setFont(label_font)
            painter.setPen(QColor("#E7D7B3"))
            painter.drawText(
                QRectF(-58, r + 8, 116, 20),
                Qt.AlignmentFlag.AlignHCenter,
                self.label,
            )
            return

        if self.kind == "mini_boss":
            # Mini-bosses are deliberately related to, but clearly smaller than,
            # the primary boss marker. A diamond frame keeps them readable when
            # several share the arena.
            edge = QColor("#E0B86A" if selected else "#A7784D")
            painter.setPen(QPen(edge, 2.2 if selected else 1.5))
            painter.setBrush(QBrush(self.color))
            diamond = QPolygonF([
                QPointF(0, -r - 4),
                QPointF(r + 4, 0),
                QPointF(0, r + 4),
                QPointF(-r - 4, 0),
            ])
            painter.drawPolygon(diamond)

            painter.setPen(QPen(QColor("#6E4D3E"), 1.0))
            painter.setBrush(QBrush(QColor("#211715")))
            painter.drawEllipse(QPointF(0, 0), r - 5, r - 5)

            font = QFont("Montserrat", 9)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor("#F0D9AF"))
            painter.drawText(QRectF(-r, -r, r * 2, r * 2), Qt.AlignmentFlag.AlignCenter, "M")

            label_font = QFont("Montserrat", 8)
            label_font.setBold(True)
            painter.setFont(label_font)
            painter.setPen(QColor("#E3D5BC"))
            painter.drawText(QRectF(-58, r + 7, 116, 18), Qt.AlignmentFlag.AlignHCenter, self.label)
            return

        edge = QColor("#E0B86A" if selected else "#A1844F")
        painter.setPen(QPen(edge, 2.2 if selected else 1.4))
        painter.setBrush(QBrush(self.color))
        painter.drawEllipse(QPointF(0, 0), r, r)

        glyph = {
            "tank": "T",
            "healer": "H",
            "dps": "D",
            "portal": "P",
            "aoe": "!",
            "stack": "+",
        }.get(self.kind, "•")
        font = QFont("Montserrat", 10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#F4E7CB"))
        painter.drawText(QRectF(-r, -r, r * 2, r * 2), Qt.AlignmentFlag.AlignCenter, glyph)

        label_font = QFont("Montserrat", 8)
        painter.setFont(label_font)
        painter.setPen(QColor("#D8CFBE"))
        painter.drawText(QRectF(-58, r + 4, 116, 18), Qt.AlignmentFlag.AlignHCenter, self.label)

    def mousePressEvent(self, event):
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._clamp_to_scene()
        if self.scene() is not None:
            self.scene().update()
        super().mouseReleaseEvent(event)

    def _clamp_to_scene(self):
        p = self.pos()
        margin = max(62, self.radius + 26 if self.kind == "boss" else self.radius + 8)
        self.setPos(
            max(margin, min(SCENE_W - margin, p.x())),
            max(margin, min(SCENE_H - margin - 24, p.y())),
        )

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            "kind": self.kind,
            "label": self.label,
            "color": self.color.name(),
            "x": round(p.x() / SCENE_W, 5),
            "y": round(p.y() / SCENE_H, 5),
            "radius": self.radius,
        }


class EncounterZone(QGraphicsObject):
    """Draggable, resizable circular mechanic area."""

    MIN_RADIUS = 20.0
    MAX_RADIUS = 220.0

    def __init__(
        self,
        zone_type: str,
        label: str,
        color: str,
        radius: float = 80.0,
        parent=None,
    ):
        super().__init__(parent)
        self.zone_type = zone_type
        self.label = label
        self.color = QColor(color)
        self.radius = self._bounded_radius(radius)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setZValue(2)

    @classmethod
    def _bounded_radius(cls, radius: float) -> float:
        return max(cls.MIN_RADIUS, min(cls.MAX_RADIUS, float(radius)))

    def boundingRect(self) -> QRectF:
        r = self.radius
        pad = 6
        return QRectF(-r - pad, -r - pad, (r + pad) * 2, (r + pad) * 2)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), self.radius, self.radius)
        return path

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        selected = self.isSelected()

        fill = QColor(self.color)
        fill.setAlpha(72 if not selected else 92)
        edge = QColor(self.color)
        edge = edge.lighter(150 if selected else 120)
        edge.setAlpha(220 if selected else 160)

        painter.setPen(
            QPen(
                edge,
                2.4 if selected else 1.5,
                Qt.PenStyle.DashLine if selected else Qt.PenStyle.SolidLine,
            )
        )
        painter.setBrush(QBrush(fill))
        painter.drawEllipse(QPointF(0, 0), self.radius, self.radius)

        font = QFont("Montserrat", 8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#E7DDC8"))
        painter.drawText(
            QRectF(-self.radius, -10, self.radius * 2, 20),
            Qt.AlignmentFlag.AlignCenter,
            self.label,
        )

    def mousePressEvent(self, event):
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._clamp_to_scene()
        if self.scene() is not None:
            self.scene().update()
        super().mouseReleaseEvent(event)

    def set_radius(self, radius: float):
        bounded = self._bounded_radius(radius)
        if bounded == self.radius:
            return
        self.prepareGeometryChange()
        self.radius = bounded
        self._clamp_to_scene()
        self.update()

    def _clamp_to_scene(self):
        p = self.pos()
        margin = self.radius + 8
        max_x = max(margin, SCENE_W - margin)
        max_y = max(margin, SCENE_H - margin)
        self.setPos(
            max(margin, min(max_x, p.x())),
            max(margin, min(max_y, p.y())),
        )

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            "zone_type": self.zone_type,
            "label": self.label,
            "color": self.color.name(),
            "x": round(p.x() / SCENE_W, 5),
            "y": round(p.y() / SCENE_H, 5),
            "radius": self.radius,
        }


class EncounterBoardView(QGraphicsView):
    """Zoomable tactical arena view."""

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        # The board is small enough that a full repaint while dragging is cheap,
        # and it completely prevents ghost trails from complex antialiased tokens.
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setMinimumHeight(420)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QColor("#061315"))

    def wheelEvent(self, event):
        factor = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
        current = self.transform().m11()
        next_scale = current * factor
        if 0.55 <= next_scale <= 2.5:
            self.scale(factor, factor)
        event.accept()

    def fit_arena(self):
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class EncounterBoard(QWidget):
    """Interactive encounter positioning editor for Encounters > Mechanics."""

    snapshotSaved = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_dir = get_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.data_dir / "encounter_positioning.json"
        self.snapshot_path = self.data_dir / "encounter_positioning.png"
        self._counts = {
            "tank": 0,
            "healer": 0,
            "dps": 0,
            "portal": 0,
            "aoe": 0,
            "stack": 0,
            "mini_boss": 0,
            "zone": 0,
        }

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, SCENE_W, SCENE_H)
        self.view = EncounterBoardView(self.scene)

        self._build_ui()
        self._draw_arena()
        if not self.load_state():
            self._seed_default_layout()
        self._refresh_mini_boss_button()
        self.view.fit_arena()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        primary_toolbar = QHBoxLayout()
        primary_toolbar.setSpacing(5)

        caption = QLabel("TACTICAL BOARD")
        caption.setProperty("sidebarHeading", True)
        primary_toolbar.addWidget(caption)

        self.boss_mode = QComboBox()
        self.boss_mode.addItems(["1 Boss", "2 Bosses"])
        self.boss_mode.currentIndexChanged.connect(self._set_boss_count)
        primary_toolbar.addWidget(self.boss_mode)

        self.mini_boss_button = QPushButton("+ Mini-Boss")
        self.mini_boss_button.clicked.connect(lambda: self.add_token("mini_boss"))
        primary_toolbar.addWidget(self.mini_boss_button)

        for text, kind in (
            ("+ Tank", "tank"),
            ("+ Healer", "healer"),
            ("+ DD", "dps"),
            ("+ Portal", "portal"),
            ("+ AOE", "aoe"),
            ("+ Stack", "stack"),
        ):
            button = QPushButton(text)
            button.clicked.connect(lambda _=False, k=kind: self.add_token(k))
            primary_toolbar.addWidget(button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self.delete_selected)
        primary_toolbar.addWidget(delete_button)

        primary_toolbar.addStretch(1)
        fit_button = QPushButton("Fit Arena")
        fit_button.clicked.connect(self.view.fit_arena)
        primary_toolbar.addWidget(fit_button)
        save_button = QPushButton("Save Layout")
        save_button.clicked.connect(self.save_state)
        primary_toolbar.addWidget(save_button)
        capture_button = QPushButton("Capture Positioning")
        capture_button.setProperty("primary", True)
        capture_button.clicked.connect(self.capture_snapshot)
        primary_toolbar.addWidget(capture_button)
        root.addLayout(primary_toolbar)

        zone_toolbar = QHBoxLayout()
        zone_toolbar.setSpacing(5)

        zone_caption = QLabel("CIRCLE ZONES")
        zone_caption.setProperty("sidebarHeading", True)
        zone_toolbar.addWidget(zone_caption)

        self.zone_type_combo = QComboBox()
        for zone_type in ZONE_STYLES:
            self.zone_type_combo.addItem(zone_type)
        zone_toolbar.addWidget(self.zone_type_combo)

        self.zone_size_combo = QComboBox()
        for name, radius in ZONE_PRESETS.items():
            self.zone_size_combo.addItem(name, radius)
        self.zone_size_combo.addItem("Custom", None)
        self.zone_size_combo.setCurrentText("Medium")
        self.zone_size_combo.currentIndexChanged.connect(self._zone_preset_changed)
        zone_toolbar.addWidget(self.zone_size_combo)

        self.zone_radius_spin = QSpinBox()
        self.zone_radius_spin.setRange(int(EncounterZone.MIN_RADIUS), int(EncounterZone.MAX_RADIUS))
        self.zone_radius_spin.setValue(int(ZONE_PRESETS["Medium"]))
        self.zone_radius_spin.setSuffix(" px")
        self.zone_radius_spin.setToolTip("Radius of the selected or next circle zone")
        self.zone_radius_spin.valueChanged.connect(self._custom_zone_radius_changed)
        zone_toolbar.addWidget(self.zone_radius_spin)

        add_zone_button = QPushButton("+ Circle Zone")
        add_zone_button.clicked.connect(self.add_zone)
        zone_toolbar.addWidget(add_zone_button)

        zone_toolbar.addStretch(1)
        root.addLayout(zone_toolbar)

        hint = QLabel(
            "Drag markers and circle zones to position them. Select a zone, then use a size preset or radius value to resize it. "
            "Mouse wheel zooms. Up to six mini-boss markers may be placed. The captured image feeds the Assignments positioning card."
        )
        hint.setProperty("muted", True)
        hint.setWordWrap(True)
        root.addWidget(hint)
        root.addWidget(self.view, 1)

    def _draw_arena(self):
        """Draw a reusable dungeon-style tactical floor without encounter-specific art."""
        self.scene.clear()

        shell = QColor("#081416")
        stone_dark = QColor("#0E1A1B")
        stone_mid = QColor("#122224")
        stone_light = QColor("#163033")
        seam = QColor("#2D3C3A")
        brass = QColor("#6F5A37")
        faint_brass = QColor("#5A4630")

        self.scene.addRect(
            8,
            8,
            SCENE_W - 16,
            SCENE_H - 16,
            QPen(brass, 2),
            QBrush(shell),
        ).setZValue(-120)

        # Side platforms / alcoves give the board a dungeon-room silhouette.
        self.scene.addRect(78, 184, 92, 172, QPen(seam, 1.2), QBrush(stone_mid)).setZValue(-112)
        self.scene.addRect(790, 184, 92, 172, QPen(seam, 1.2), QBrush(stone_mid)).setZValue(-112)

        outer = QPolygonF([
            QPointF(210, 62),
            QPointF(750, 62),
            QPointF(862, 160),
            QPointF(862, 380),
            QPointF(750, 478),
            QPointF(210, 478),
            QPointF(98, 380),
            QPointF(98, 160),
        ])
        self.scene.addPolygon(outer, QPen(brass, 2), QBrush(stone_dark)).setZValue(-110)

        inner = QPolygonF([
            QPointF(260, 110),
            QPointF(700, 110),
            QPointF(790, 190),
            QPointF(790, 350),
            QPointF(700, 430),
            QPointF(260, 430),
            QPointF(170, 350),
            QPointF(170, 190),
        ])
        self.scene.addPolygon(inner, QPen(QColor("#4A5A55"), 1.2), QBrush(stone_mid)).setZValue(-100)

        self.scene.addEllipse(
            318,
            170,
            324,
            200,
            QPen(faint_brass, 1.5),
            QBrush(stone_light),
        ).setZValue(-95)
        self.scene.addEllipse(
            382,
            215,
            196,
            110,
            QPen(QColor("#7A5C33"), 1.2),
            QBrush(QColor("#112021")),
        ).setZValue(-90)

        # Stone/radial seams keep positioning readable without becoming a grid.
        self.scene.addLine(480, 104, 480, 436, QPen(seam, 1.0)).setZValue(-88)
        self.scene.addLine(178, 270, 782, 270, QPen(seam, 1.0)).setZValue(-88)
        self.scene.addLine(250, 145, 710, 395, QPen(QColor("#243331"), 0.8)).setZValue(-88)
        self.scene.addLine(710, 145, 250, 395, QPen(QColor("#243331"), 0.8)).setZValue(-88)

        for x, y in (
            (230, 140),
            (480, 118),
            (730, 140),
            (198, 270),
            (762, 270),
            (230, 400),
            (480, 422),
            (730, 400),
        ):
            self.scene.addEllipse(
                x - 9,
                y - 9,
                18,
                18,
                QPen(brass, 1.0),
                QBrush(QColor("#142D2F")),
            ).setZValue(-84)

        for x, y in ((125, 88), (835, 88), (125, 452), (835, 452)):
            self.scene.addEllipse(
                x - 7,
                y - 7,
                14,
                14,
                QPen(brass, 1.0),
                QBrush(QColor("#142D2F")),
            ).setZValue(-82)

        title = self.scene.addText("ENCOUNTER ARENA")
        title.setDefaultTextColor(QColor("#9B7B49"))
        title.setFont(QFont("Cinzel", 10))
        title.setPos(410, 24)
        title.setZValue(-70)

    def _seed_default_layout(self):
        self._set_boss_count(0)
        defaults = [
            ("tank", "Main Tank", 480, 205),
            ("tank", "Off Tank", 570, 245),
            ("healer", "Healer 1", 390, 335),
            ("healer", "Healer 2", 570, 335),
            ("dps", "DD Stack", 480, 365),
        ]
        for kind, label, x, y in defaults:
            self._add_token(kind, label, x, y)
            self._counts[kind] = self._counts.get(kind, 0) + 1

    def _token_items(self) -> list[EncounterToken]:
        return [item for item in self.scene.items() if isinstance(item, EncounterToken)]

    def _boss_items(self) -> list[EncounterToken]:
        return [item for item in self._token_items() if item.kind == "boss"]

    def _mini_boss_items(self) -> list[EncounterToken]:
        return [item for item in self._token_items() if item.kind == "mini_boss"]

    def _zone_items(self) -> list[EncounterZone]:
        return [item for item in self.scene.items() if isinstance(item, EncounterZone)]

    def _selected_zones(self) -> list[EncounterZone]:
        return [item for item in self.scene.selectedItems() if isinstance(item, EncounterZone)]

    def _set_boss_count(self, _index: int):
        desired = 2 if self.boss_mode.currentIndex() == 1 else 1
        existing = self._boss_items()
        for item in existing[desired:]:
            self.scene.removeItem(item)
        existing = existing[:desired]

        if desired == 1:
            if existing:
                existing[0].label = "Boss"
                existing[0].setPos(480, 260)
                existing[0].update()
            else:
                self._add_token("boss", "Boss", 480, 260, radius=27)
        else:
            if not existing:
                existing.append(self._add_token("boss", "Boss A", 420, 260, radius=27))
            existing[0].label = "Boss A"
            existing[0].setPos(420, 260)
            existing[0].update()
            if len(existing) < 2:
                self._add_token("boss", "Boss B", 540, 260, radius=27)
            else:
                existing[1].label = "Boss B"
                existing[1].setPos(540, 260)
                existing[1].update()
        self.scene.update()

    def add_token(self, kind: str):
        if kind == "mini_boss" and len(self._mini_boss_items()) >= MAX_MINI_BOSSES:
            self._refresh_mini_boss_button()
            return

        self._counts[kind] = self._counts.get(kind, 0) + 1
        number = self._counts[kind]
        labels = {
            "tank": f"Tank {number}",
            "healer": f"Healer {number}",
            "dps": "DD Stack" if number == 1 else f"DD {number}",
            "portal": f"Portal {number}",
            "aoe": f"AOE {number}",
            "stack": f"Stack {number}",
            "mini_boss": f"Mini-Boss {number}",
        }
        offset = (number - 1) * 24
        if kind == "mini_boss":
            self._add_token(kind, labels[kind], 330 + (offset % 300), 180 + (offset % 140), radius=22)
        else:
            self._add_token(kind, labels[kind], 300 + offset, 400 - (offset % 100))
        self._refresh_mini_boss_button()

    def _add_token(self, kind: str, label: str, x: float, y: float, radius: float = 18.0) -> EncounterToken:
        colors = {
            "boss": "#4A2420",
            "mini_boss": "#63372A",
            "tank": "#24445A",
            "healer": "#365A3E",
            "dps": "#5A302C",
            "portal": "#41305A",
            "aoe": "#673B1E",
            "stack": "#586028",
        }
        token = EncounterToken(kind, label, colors.get(kind, "#3A4444"), radius)
        token.setPos(x, y)
        self.scene.addItem(token)
        return token

    def _refresh_mini_boss_button(self):
        if not hasattr(self, "mini_boss_button"):
            return
        count = len(self._mini_boss_items())
        self.mini_boss_button.setEnabled(count < MAX_MINI_BOSSES)
        self.mini_boss_button.setText(f"+ Mini-Boss ({count}/{MAX_MINI_BOSSES})")
        self.mini_boss_button.setToolTip(
            "Add another mini-boss marker" if count < MAX_MINI_BOSSES else "Six mini-boss markers are already on the board"
        )

    def add_zone(self):
        self._counts["zone"] += 1
        number = self._counts["zone"]
        zone_type = self.zone_type_combo.currentText() or "Neutral"
        radius = float(self.zone_radius_spin.value())
        label = f"{zone_type} Zone {number}"
        offset = (number - 1) * 28
        self._add_zone(
            zone_type,
            label,
            480 + ((offset % 220) - 110),
            270 + ((offset % 160) - 80),
            radius,
        )

    def _add_zone(
        self,
        zone_type: str,
        label: str,
        x: float,
        y: float,
        radius: float,
        color: str | None = None,
    ) -> EncounterZone:
        zone = EncounterZone(
            zone_type=zone_type,
            label=label,
            color=color or ZONE_STYLES.get(zone_type, ZONE_STYLES["Neutral"]),
            radius=radius,
        )
        zone.setPos(x, y)
        zone._clamp_to_scene()
        self.scene.addItem(zone)
        return zone

    def _zone_preset_changed(self, _index: int):
        radius = self.zone_size_combo.currentData()
        if radius is None:
            return
        self.zone_radius_spin.blockSignals(True)
        self.zone_radius_spin.setValue(int(radius))
        self.zone_radius_spin.blockSignals(False)
        self._resize_selected_zones(float(radius))

    def _custom_zone_radius_changed(self, value: int):
        preset_radius = self.zone_size_combo.currentData()
        if preset_radius is None or int(preset_radius) != value:
            self.zone_size_combo.blockSignals(True)
            self.zone_size_combo.setCurrentText("Custom")
            self.zone_size_combo.blockSignals(False)
        self._resize_selected_zones(float(value))

    def _resize_selected_zones(self, radius: float):
        for zone in self._selected_zones():
            zone.set_radius(radius)
        if self._selected_zones():
            self.scene.update()

    def delete_selected(self):
        for item in list(self.scene.selectedItems()):
            if isinstance(item, EncounterZone):
                self.scene.removeItem(item)
            elif isinstance(item, EncounterToken) and item.kind != "boss":
                self.scene.removeItem(item)
        self._refresh_mini_boss_button()
        self.scene.update()

    def save_state(self):
        tokens = self._token_items()
        payload = {
            "version": 2,
            "boss_count": 2 if self.boss_mode.currentIndex() == 1 else 1,
            # Keep the original items collection stable for version-1 readers and
            # store the two new object families separately.
            "items": [item.to_dict() for item in tokens if item.kind != "mini_boss"],
            "mini_bosses": [item.to_dict() for item in tokens if item.kind == "mini_boss"],
            "zones": [zone.to_dict() for zone in self._zone_items()],
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_state(self) -> bool:
        if not self.state_path.exists():
            return False
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            items = payload.get("items", [])
            mini_bosses = payload.get("mini_bosses", [])
            zones = payload.get("zones", [])
            if not isinstance(items, list):
                items = []
            if not isinstance(mini_bosses, list):
                mini_bosses = []
            if not isinstance(zones, list):
                zones = []
            if not items and not mini_bosses and not zones:
                return False

            self.boss_mode.blockSignals(True)
            self.boss_mode.setCurrentIndex(1 if int(payload.get("boss_count", 1)) == 2 else 0)
            self.boss_mode.blockSignals(False)

            for record in items:
                self._load_token_record(record)

            # Version-1 files simply have no mini_bosses/zones keys, so both
            # collections naturally load empty without migration or guessing.
            for record in mini_bosses:
                self._load_token_record(record, forced_kind="mini_boss")

            for record in zones:
                if not isinstance(record, dict):
                    continue
                zone_type = str(record.get("zone_type", "Neutral"))
                label = str(record.get("label", f"{zone_type} Zone"))
                x = float(record.get("x", 0.5)) * SCENE_W
                y = float(record.get("y", 0.5)) * SCENE_H
                radius = float(record.get("radius", ZONE_PRESETS["Medium"]))
                color = str(record.get("color", ZONE_STYLES.get(zone_type, ZONE_STYLES["Neutral"])))
                self._add_zone(zone_type, label, x, y, radius, color=color)
                self._counts["zone"] += 1

            self._refresh_mini_boss_button()
            self.scene.update()
            return True
        except Exception:
            return False

    def _load_token_record(self, record: dict, forced_kind: str | None = None):
        if not isinstance(record, dict):
            return
        kind = forced_kind or str(record.get("kind", ""))
        if not kind:
            return
        if kind == "mini_boss" and len(self._mini_boss_items()) >= MAX_MINI_BOSSES:
            return
        label = str(record.get("label", kind.title()))
        x = float(record.get("x", 0.5)) * SCENE_W
        y = float(record.get("y", 0.5)) * SCENE_H
        default_radius = 22.0 if kind == "mini_boss" else 18.0
        radius = float(record.get("radius", default_radius))
        token = self._add_token(kind, label, x, y, radius=radius)
        if record.get("color"):
            token.color = QColor(str(record["color"]))
        if kind in self._counts:
            self._counts[kind] += 1

    def capture_snapshot(self):
        self.save_state()
        image = QImage(int(SCENE_W), int(SCENE_H), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("#061315"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.scene.render(painter, QRectF(0, 0, SCENE_W, SCENE_H), self.scene.sceneRect())
        painter.end()
        image.save(str(self.snapshot_path), "PNG")
        self.snapshotSaved.emit(str(self.snapshot_path))
