# ==================================================
# Black Feather Foundry
# ui/collectibles_dashboard_page.py
# Dense fantasy progress overview for collectible completion.
# ==================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_status_bar import FoundryStatusBar


TEAL_ACCENTS = (
    "#2F7A80",
    "#3D898D",
    "#59AEB3",
    "#397D83",
    "#4A9599",
    "#287078",
)

SPRITE_COLUMNS = 6
SPRITE_ROWS = 4

# Badge artwork follows the generated 6x4 source sheet, not dashboard order.
# Keep this semantic so future card reordering never moves the paw badge onto
# something wholly undeserving of paws.
CATEGORY_BADGE_INDEX = {
    "Mounts": 0,
    "Pets": 1,
    "Armor Styles": 2,
    "Hats": 3,
    # Cells 4 and 8 are baked progress-ring art rather than category emblems;
    # the dashboard keeps its live ring meter for Skins and Polymorphs.
    "Costumes": 5,
    "Personalities": 6,
    "Emotes": 7,
    "Mementos": 9,
    "Furnishings": 10,
    "Assistants": 11,
    "Companions": 12,
    "Body Markings": 13,
    "Head Markings": 14,
    "Hair": 15,
    "Facial Hair / Horns": 16,
    "Piercing / Jewelry": 17,
    # Source-sheet cells 18/19/22/23 are Outfit Styles, Dyes,
    # Non-Combat Pets and Miscellaneous. They remain available for future
    # dashboard specs rather than being attached to unrelated current cards.
    "Tools & Upgrades": 20,
    "Customized Actions": 21,
}


@dataclass(frozen=True)
class DashboardSpec:
    label: str
    route: str
    type_keys: tuple[str, ...]
    meter: str
    glyph: str


# The first 24 cards mirror the visual mockup, but this list is deliberately
# extensible. New collectible groups can be appended without changing layout
# code; the grid simply flows into additional rows.
DASHBOARD_SPECS = (
    DashboardSpec("Mounts", "Mounts", ("mount",), "bar", "♞"),
    DashboardSpec("Pets", "Pets", ("pet",), "ring", "✦"),
    DashboardSpec("Armor Styles", "Armor Styles", ("armor_style",), "shield", "◆"),
    DashboardSpec("Weapon Styles", "Weapon Styles", ("weapon_style",), "bar", "†"),
    DashboardSpec("Skins", "Skins", ("skin",), "ring", "◉"),
    DashboardSpec("Costumes", "Costumes", ("costume",), "bar", "♜"),
    DashboardSpec("Personalities", "Personalities", ("personality",), "shield", "☽"),
    DashboardSpec("Emotes", "Emotes", ("emote",), "bar", "✧"),
    DashboardSpec("Polymorphs", "Polymorphs", ("polymorph",), "ring", "◌"),
    DashboardSpec("Mementos", "Mementos", ("memento",), "bar", "⌘"),
    DashboardSpec("Furnishings", "Furnishings", ("furnishing",), "shield", "⌂"),
    DashboardSpec("Assistants", "Allies / Assistants", ("assistant",), "bar", "♟"),
    DashboardSpec("Companions", "Allies / Assistants", ("companion",), "ring", "♢"),
    DashboardSpec("Body Markings", "Hairstyles & Adornments", ("body_marking",), "bar", "◇"),
    DashboardSpec("Head Markings", "Hairstyles & Adornments", ("head_marking",), "bar", "◈"),
    DashboardSpec("Hair", "Hairstyles & Adornments", ("hair",), "bar", "≈"),
    DashboardSpec("Hats", "Hairstyles & Adornments", ("hat",), "ring", "△"),
    DashboardSpec("Facial Accessories", "Hairstyles & Adornments", ("facial_accessory",), "bar", "✣"),
    DashboardSpec("Facial Hair / Horns", "Hairstyles & Adornments", ("facial_hair_horns",), "bar", "⌁"),
    DashboardSpec("Piercing / Jewelry", "Hairstyles & Adornments", ("piercing_jewelry",), "ring", "◊"),
    DashboardSpec("Houses", "Houses", ("house",), "shield", "⌂"),
    DashboardSpec("Customized Actions", "Customized Actions", ("customized_action",), "shield", "✤"),
    DashboardSpec("Fragments", "Fragments", ("fragment", "combination_fragment", "patron"), "vial", "✥"),
    DashboardSpec("Tools & Upgrades", "Tools & Upgrades", ("tool", "account_upgrade", "story", "skill_style"), "vial", "⚒"),
)


def _asset_path(filename: str) -> Path:
    """Resolve theme art on Windows while remaining safe on case-sensitive CI."""
    root = Path(__file__).resolve().parents[1] / "assets" / "themes"
    preferred = root / "Bff" / "collectibles" / filename
    if preferred.exists():
        return preferred
    return root / "bff" / "collectibles" / filename


class SpriteSheet:
    """Lazy 6x4 PNG sprite slicer with cached QPixmap cells."""

    def __init__(self, path: Path, columns: int = SPRITE_COLUMNS, rows: int = SPRITE_ROWS):
        self.path = path
        self.columns = columns
        self.rows = rows
        self._sheet: QPixmap | None = None
        self._cache: dict[int, QPixmap] = {}

    @property
    def available(self) -> bool:
        self._load()
        return self._sheet is not None and not self._sheet.isNull()

    def _load(self) -> None:
        if self._sheet is not None:
            return
        pixmap = QPixmap(str(self.path))
        self._sheet = pixmap

    def cell(self, index: int) -> QPixmap | None:
        if index < 0 or index >= self.columns * self.rows:
            return None
        if index in self._cache:
            return self._cache[index]
        self._load()
        if self._sheet is None or self._sheet.isNull():
            return None

        cell_width = self._sheet.width() / self.columns
        cell_height = self._sheet.height() / self.rows
        column = index % self.columns
        row = index // self.columns
        left = round(column * cell_width)
        top = round(row * cell_height)
        right = round((column + 1) * cell_width)
        bottom = round((row + 1) * cell_height)
        cropped = self._sheet.copy(left, top, right - left, bottom - top)
        self._cache[index] = cropped
        return cropped


NUMBER_SPRITES = SpriteSheet(_asset_path("numbers.png"))
BADGE_SPRITES = SpriteSheet(_asset_path("badges.png"))


def _percent(owned: int, total: int) -> int:
    if total <= 0:
        return 0
    return max(0, min(100, round((owned / total) * 100)))


def _progress_epithet(percent: int, total: int) -> str:
    if total <= 0:
        return "No catalog entries yet"
    if percent >= 100:
        return "Archive complete"
    if percent >= 80:
        return "Nearly legendary"
    if percent >= 60:
        return "Formidable hoard"
    if percent >= 40:
        return "Vault is filling"
    if percent >= 20:
        return "Respectable beginning"
    if percent > 0:
        return "First relics secured"
    return "Unexplored territory"


class RingMeter(QWidget):
    def __init__(self, accent: str, parent=None):
        super().__init__(parent)
        self.value = 0
        self.accent = QColor(accent)
        self.setFixedSize(76, 76)

    def setValue(self, value: int) -> None:
        self.value = max(0, min(100, int(value)))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(8, 8, self.width() - 16, self.height() - 16)
        painter.setPen(QPen(QColor("#24383A"), 8))
        painter.drawArc(rect, 0, 360 * 16)
        painter.setPen(QPen(self.accent, 8))
        painter.drawArc(rect, 90 * 16, -round(360 * 16 * self.value / 100))
        painter.setPen(QColor("#E8D0A0"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.value}%")


class ShieldMeter(QWidget):
    def __init__(self, accent: str, parent=None):
        super().__init__(parent)
        self.value = 0
        self.accent = QColor(accent)
        self.setFixedSize(84, 78)

    def setValue(self, value: int) -> None:
        self.value = max(0, min(100, int(value)))
        self.update()

    def _shield_path(self) -> QPainterPath:
        w = float(self.width())
        h = float(self.height())
        path = QPainterPath()
        path.moveTo(w * 0.15, h * 0.10)
        path.lineTo(w * 0.85, h * 0.10)
        path.lineTo(w * 0.82, h * 0.60)
        path.quadTo(w * 0.70, h * 0.82, w * 0.50, h * 0.94)
        path.quadTo(w * 0.30, h * 0.82, w * 0.18, h * 0.60)
        path.closeSubpath()
        return path

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = self._shield_path()
        painter.fillPath(path, QColor("#10282C"))
        painter.setPen(QPen(QColor("#8A6F42"), 2))
        painter.drawPath(path)

        painter.save()
        painter.setClipPath(path)
        fill_height = self.height() * self.value / 100
        painter.fillRect(
            0,
            self.height() - fill_height,
            self.width(),
            fill_height,
            self.accent,
        )
        painter.restore()
        painter.setPen(QColor("#E8D0A0"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.value}%")


class VialMeter(QWidget):
    def __init__(self, accent: str, parent=None):
        super().__init__(parent)
        self.value = 0
        self.accent = QColor(accent)
        self.setFixedSize(58, 88)

    def setValue(self, value: int) -> None:
        self.value = max(0, min(100, int(value)))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        tube = QRectF(18, 10, 22, 68)
        painter.setBrush(QColor("#10262A"))
        painter.setPen(QPen(QColor("#8A6F42"), 2))
        painter.drawRoundedRect(tube, 8, 8)
        inner = tube.adjusted(4, 4, -4, -4)
        fill_height = inner.height() * self.value / 100
        painter.fillRect(
            QRectF(inner.left(), inner.bottom() - fill_height, inner.width(), fill_height),
            self.accent,
        )
        painter.setBrush(QColor("#A98752"))
        painter.drawRect(QRectF(14, 5, 30, 8))
        painter.setPen(QColor("#E8D0A0"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(QRectF(0, 68, self.width(), 20), Qt.AlignmentFlag.AlignCenter, f"{self.value}%")


class ProgressTile(QFrame):
    clicked = Signal(str)

    def __init__(self, spec: DashboardSpec, index: int, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.index = index
        self.percent = 0
        self.owned = 0
        self.total = 0
        self.accent = TEAL_ACCENTS[(index - 1) % len(TEAL_ACCENTS)]
        self.setProperty("collectibleDashboardTile", True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumSize(178, 154)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(
            "QFrame[collectibleDashboardTile='true'] {"
            " background-color: rgba(12, 31, 34, 210);"
            " border: 1px solid #765D35;"
            " border-radius: 4px;"
            "}"
            "QFrame[collectibleDashboardTile='true']:hover {"
            " background-color: rgba(19, 54, 58, 225);"
            " border: 1px solid #B8945F;"
            "}"
        )
        self._build_ui()

    @staticmethod
    def _set_sprite(label: QLabel, pixmap: QPixmap | None, size: int) -> bool:
        if pixmap is None or pixmap.isNull():
            return False
        scaled = pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(scaled)
        return True

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        heading = QHBoxLayout()
        number = QLabel(str(self.index))
        number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number.setFixedSize(32, 32)
        number_sprite = NUMBER_SPRITES.cell(self.index - 1)
        if not self._set_sprite(number, number_sprite, 32):
            number.setStyleSheet(
                "color:#C8A46A; border:1px solid #8A6F42; border-radius:2px; font-weight:700;"
            )
        title = QLabel(self.spec.label.upper())
        title.setWordWrap(True)
        title.setStyleSheet("color:#D9B977; font-weight:700; letter-spacing:1px;")
        heading.addWidget(number)
        heading.addWidget(title, 1)
        layout.addLayout(heading)

        center = QHBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(8)

        self.glyph = QLabel(self.spec.glyph)
        self.glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.glyph.setFixedSize(72, 72)
        badge_index = CATEGORY_BADGE_INDEX.get(self.spec.label)
        badge_sprite = BADGE_SPRITES.cell(badge_index) if badge_index is not None else None
        if not self._set_sprite(self.glyph, badge_sprite, 72):
            self.glyph.setStyleSheet(
                f"color:{self.accent}; font-size:27px; border:1px solid #65502F; "
                "border-radius:36px; background:#102629;"
            )

        if self.spec.meter == "ring":
            self.meter = RingMeter(self.accent)
            center.addStretch(1)
            center.addWidget(self.glyph)
            center.addWidget(self.meter)
            center.addStretch(1)
        elif self.spec.meter == "shield":
            self.meter = ShieldMeter(self.accent)
            center.addStretch(1)
            center.addWidget(self.glyph)
            center.addWidget(self.meter)
            center.addStretch(1)
        elif self.spec.meter == "vial":
            self.meter = VialMeter(self.accent)
            center.addStretch(1)
            center.addWidget(self.glyph)
            center.addWidget(self.meter)
            center.addStretch(1)
        else:
            self.meter = QProgressBar()
            self.meter.setRange(0, 100)
            self.meter.setTextVisible(False)
            self.meter.setFixedHeight(13)
            self.meter.setStyleSheet(
                "QProgressBar {background:#0A1719; border:1px solid #6E5733; border-radius:5px;}"
                f"QProgressBar::chunk {{background:{self.accent}; border-radius:4px;}}"
            )
            center.addStretch(1)
            center.addWidget(self.glyph)
            center.addStretch(1)

        layout.addLayout(center, 1)
        if self.spec.meter == "bar":
            layout.addWidget(self.meter)

        self.count_label = QLabel("0 / 0")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setStyleSheet("color:#E5D8BD; font-weight:600;")
        self.state_label = QLabel("Unexplored territory")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setStyleSheet("color:#7EB6B5; font-size:10px;")
        layout.addWidget(self.count_label)
        layout.addWidget(self.state_label)

    def set_progress(self, owned: int, total: int) -> None:
        self.owned = int(owned)
        self.total = int(total)
        self.percent = _percent(self.owned, self.total)
        self.meter.setValue(self.percent)
        self.count_label.setText(f"{self.owned:,} / {self.total:,}")
        self.state_label.setText(_progress_epithet(self.percent, self.total))
        self.setToolTip(f"Open {self.spec.route} · {self.owned:,}/{self.total:,} collected")

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.spec.route)
        super().mouseReleaseEvent(event)


class CollectiblesDashboardPage(QWidget):
    """Main Collections landing page styled after the fantasy dashboard mockup."""

    categoryRequested = Signal(str)
    GRID_COLUMNS = 6

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._tiles: list[ProgressTile] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(14)

        title_block = QVBoxLayout()
        title = QLabel("COLLECTIBLES DASHBOARD")
        title.setStyleSheet("color:#D4AA6A; font-size:28px; font-weight:700; letter-spacing:2px;")
        subtitle = QLabel("ACCOUNT PROGRESS OVERVIEW")
        subtitle.setStyleSheet("color:#59AEB3; font-size:14px; letter-spacing:2px;")
        rule = QLabel("────── ✦ ──────")
        rule.setStyleSheet("color:#8A6F42;")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        title_block.addWidget(rule)
        top.addLayout(title_block, 2)

        overall_box = QFrame()
        overall_box.setStyleSheet(
            "QFrame {background:rgba(11, 32, 35, 220); border:1px solid #765D35; border-radius:4px;}"
        )
        overall_layout = QVBoxLayout(overall_box)
        overall_layout.setContentsMargins(12, 8, 12, 8)
        overall_label = QLabel("✥  OVERALL PROGRESS")
        overall_label.setStyleSheet("color:#D4AA6A; font-weight:700; letter-spacing:1px;")
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setFixedHeight(22)
        self.overall_progress.setStyleSheet(
            "QProgressBar {background:#0A1719; border:1px solid #6E5733; border-radius:6px; color:#E8D0A0; text-align:center;}"
            "QProgressBar::chunk {background:#3F9395; border-radius:5px;}"
        )
        self.overall_count = QLabel("0 / 0 collectibles secured")
        self.overall_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.overall_count.setStyleSheet("color:#E5D8BD;")
        overall_layout.addWidget(overall_label)
        overall_layout.addWidget(self.overall_progress)
        overall_layout.addWidget(self.overall_count)
        top.addWidget(overall_box, 2)

        quote = QFrame()
        quote.setStyleSheet(
            "QFrame {background:#D8BF91; border:1px solid #765D35; border-radius:3px;}"
        )
        quote_layout = QVBoxLayout(quote)
        quote_layout.setContentsMargins(12, 10, 12, 10)
        quote_text = QLabel("“Every discovery\nadds to your legend.”")
        quote_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quote_text.setStyleSheet("color:#302719; font-size:12px; font-style:italic; font-weight:600;")
        quote_layout.addWidget(quote_text)
        top.addWidget(quote, 1)
        root.addLayout(top)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color:#6E5733;")
        root.addWidget(divider)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(7)
        for column in range(self.GRID_COLUMNS):
            grid.setColumnStretch(column, 1)

        for index, spec in enumerate(DASHBOARD_SPECS, start=1):
            tile = ProgressTile(spec, index)
            tile.clicked.connect(self.categoryRequested.emit)
            self._tiles.append(tile)
            row = (index - 1) // self.GRID_COLUMNS
            column = (index - 1) % self.GRID_COLUMNS
            grid.addWidget(tile, row, column)

        root.addLayout(grid)

        footer = QLabel("✦  New discoveries await beyond the known.  ✦")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color:#59AEB3; font-size:11px; letter-spacing:1px;")
        root.addWidget(footer)

        self.status = FoundryStatusBar()
        root.addWidget(self.status)

    def _progress_for_types(self, type_keys: tuple[str, ...]) -> tuple[int, int]:
        if not self.service.available or not type_keys:
            return 0, 0
        placeholders = ",".join("?" for _ in type_keys)
        row = self.service.connection.execute(
            f"""
            SELECT
                SUM(CASE WHEN COALESCE(p.owned, 0) = 1 THEN 1 ELSE 0 END) AS owned_count,
                COUNT(*) AS total_count
            FROM collectible c
            LEFT JOIN collectible_progress p ON p.collectible_id = c.id
            WHERE c.canonical_type_key IN ({placeholders})
            """,
            tuple(type_keys),
        ).fetchone()
        return int(row["owned_count"] or 0), int(row["total_count"] or 0)

    def refresh(self) -> None:
        if not self.service.available:
            self.overall_progress.setValue(0)
            self.overall_progress.setFormat("Catalog unavailable")
            self.overall_count.setText("Collection ledger unavailable")
            for tile in self._tiles:
                tile.set_progress(0, 0)
            self.status.warning(self.service.bootstrap_message or "Collectible reference data is unavailable.")
            return

        overall_owned, overall_total = self.service.progress_summary()
        overall_percent = _percent(overall_owned, overall_total)
        self.overall_progress.setValue(overall_percent)
        self.overall_progress.setFormat(f"{overall_percent}%")
        self.overall_count.setText(f"{overall_owned:,} / {overall_total:,} collectibles secured")

        populated = 0
        for tile in self._tiles:
            owned, total = self._progress_for_types(tile.spec.type_keys)
            tile.set_progress(owned, total)
            if total:
                populated += 1

        self.status.info(
            f"{populated} populated dashboard ledgers · {overall_owned:,}/{overall_total:,} total collectibles secured."
        )
