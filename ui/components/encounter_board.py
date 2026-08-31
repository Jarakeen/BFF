from __future__ import annotations

import json

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont, QImage, QPainter, QPen
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
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir


SCENE_W = 960.0
SCENE_H = 540.0


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
        r = self.radius
        return QRectF(-60, -r - 4, 120, r * 2 + 31)

    def paint(self, painter: QPainter, option, widget=None):
        r = self.radius
        selected = self.isSelected()
        edge = QColor("#E0B86A" if selected else "#A1844F")
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(edge, 2.2 if selected else 1.4))
        painter.setBrush(QBrush(self.color))
        painter.drawEllipse(QPointF(0, 0), r, r)

        glyph = {
            "boss": "B",
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
        label_font.setBold(self.kind == "boss")
        painter.setFont(label_font)
        painter.setPen(QColor("#D8CFBE"))
        painter.drawText(QRectF(-58, r + 4, 116, 18), Qt.AlignmentFlag.AlignHCenter, self.label)

    def mousePressEvent(self, event):
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._clamp_to_scene()
        super().mouseReleaseEvent(event)

    def _clamp_to_scene(self):
        p = self.pos()
        margin = max(62, self.radius + 8)
        self.setPos(
            max(margin, min(SCENE_W - margin, p.x())),
            max(self.radius + 8, min(SCENE_H - self.radius - 28, p.y())),
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


class EncounterBoardView(QGraphicsView):
    """Zoomable tactical arena view."""

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
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
    """Stage-one encounter positioning editor for the Encounters > Mechanics tab."""

    snapshotSaved = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_dir = get_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.data_dir / "encounter_positioning.json"
        self.snapshot_path = self.data_dir / "encounter_positioning.png"
        self._counts = {"tank": 0, "healer": 0, "dps": 0, "portal": 0, "aoe": 0, "stack": 0}

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, SCENE_W, SCENE_H)
        self.view = EncounterBoardView(self.scene)

        self._build_ui()
        self._draw_arena()
        if not self.load_state():
            self._seed_default_layout()
        self.view.fit_arena()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)

        caption = QLabel("TACTICAL BOARD")
        caption.setProperty("sidebarHeading", True)
        toolbar.addWidget(caption)

        self.boss_mode = QComboBox()
        self.boss_mode.addItems(["1 Boss", "2 Bosses"])
        self.boss_mode.currentIndexChanged.connect(self._set_boss_count)
        toolbar.addWidget(self.boss_mode)

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
            toolbar.addWidget(button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self.delete_selected)
        toolbar.addWidget(delete_button)

        toolbar.addStretch(1)
        fit_button = QPushButton("Fit Arena")
        fit_button.clicked.connect(self.view.fit_arena)
        toolbar.addWidget(fit_button)
        save_button = QPushButton("Save Layout")
        save_button.clicked.connect(self.save_state)
        toolbar.addWidget(save_button)
        capture_button = QPushButton("Capture Positioning")
        capture_button.setProperty("primary", True)
        capture_button.clicked.connect(self.capture_snapshot)
        toolbar.addWidget(capture_button)
        root.addLayout(toolbar)

        hint = QLabel("Drag markers to position them. Mouse wheel zooms. The captured image feeds the Assignments positioning card.")
        hint.setProperty("muted", True)
        root.addWidget(hint)
        root.addWidget(self.view, 1)

    def _draw_arena(self):
        self.scene.clear()
        floor = QColor("#0A1B1D")
        brass = QColor("#6F5A37")
        faint = QColor("#16383A")
        inner = QColor("#0E2628")

        self.scene.addRect(8, 8, SCENE_W - 16, SCENE_H - 16, QPen(brass, 2), QBrush(floor)).setZValue(-100)
        self.scene.addEllipse(150, 42, 660, 456, QPen(brass, 2), QBrush(inner)).setZValue(-90)
        self.scene.addEllipse(230, 96, 500, 348, QPen(QColor("#3A4E45"), 1), QBrush(Qt.BrushStyle.NoBrush)).setZValue(-80)
        self.scene.addEllipse(335, 168, 290, 204, QPen(QColor("#5D4A2F"), 1), QBrush(Qt.BrushStyle.NoBrush)).setZValue(-80)

        for x in range(190, 771, 80):
            self.scene.addLine(x, 270, 480, 270, QPen(faint, 0.8)).setZValue(-70)
        for y in range(90, 451, 60):
            self.scene.addLine(480, y, 480, 270, QPen(faint, 0.8)).setZValue(-70)

        for x, y in ((120, 70), (840, 70), (120, 470), (840, 470)):
            self.scene.addEllipse(x - 7, y - 7, 14, 14, QPen(brass, 1), QBrush(QColor("#142D2F"))).setZValue(-60)

        title = self.scene.addText("ENCOUNTER ARENA")
        title.setDefaultTextColor(QColor("#846A40"))
        title.setFont(QFont("Cinzel", 10))
        title.setPos(408, 18)
        title.setZValue(-50)

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

    def add_token(self, kind: str):
        self._counts[kind] = self._counts.get(kind, 0) + 1
        number = self._counts[kind]
        labels = {
            "tank": f"Tank {number}",
            "healer": f"Healer {number}",
            "dps": "DD Stack" if number == 1 else f"DD {number}",
            "portal": f"Portal {number}",
            "aoe": f"AOE {number}",
            "stack": f"Stack {number}",
        }
        offset = (number - 1) * 24
        self._add_token(kind, labels[kind], 300 + offset, 400 - (offset % 100))

    def _add_token(self, kind: str, label: str, x: float, y: float, radius: float = 18.0) -> EncounterToken:
        colors = {
            "boss": "#4A2420",
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

    def delete_selected(self):
        for item in list(self.scene.selectedItems()):
            if isinstance(item, EncounterToken) and item.kind != "boss":
                self.scene.removeItem(item)

    def save_state(self):
        payload = {
            "version": 1,
            "boss_count": 2 if self.boss_mode.currentIndex() == 1 else 1,
            "items": [item.to_dict() for item in self._token_items()],
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_state(self) -> bool:
        if not self.state_path.exists():
            return False
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            items = payload.get("items", [])
            if not isinstance(items, list) or not items:
                return False
            self.boss_mode.blockSignals(True)
            self.boss_mode.setCurrentIndex(1 if int(payload.get("boss_count", 1)) == 2 else 0)
            self.boss_mode.blockSignals(False)
            for record in items:
                kind = str(record.get("kind", ""))
                label = str(record.get("label", kind.title()))
                x = float(record.get("x", 0.5)) * SCENE_W
                y = float(record.get("y", 0.5)) * SCENE_H
                radius = float(record.get("radius", 18.0))
                token = self._add_token(kind, label, x, y, radius=radius)
                if record.get("color"):
                    token.color = QColor(str(record["color"]))
                if kind in self._counts:
                    self._counts[kind] += 1
            return True
        except Exception:
            return False

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
