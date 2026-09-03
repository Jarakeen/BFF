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
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from services.accessibility_preferences import VISUAL_THEME_RYLO
from ui.components.foundry_status_bar import FoundryStatusBar


@dataclass(frozen=True)
class DashboardTheme:
    key: str
    folder: str
    accents: tuple[str, ...]
    panel: str
    panel_hover: str
    border: str
    border_hover: str
    title: str
    subtitle: str
    text: str
    muted: str
    meter_background: str
    meter_border: str
    meter_text: str
    overall_chunk: str
    quote_background: str
    quote_text: str


BFF_THEME = DashboardTheme(
    key="bff",
    folder="Bff",
    accents=("#2F7A80", "#3D898D", "#59AEB3", "#397D83", "#4A9599", "#287078"),
    panel="rgba(12, 31, 34, 210)",
    panel_hover="rgba(19, 54, 58, 225)",
    border="#765D35",
    border_hover="#B8945F",
    title="#D9B977",
    subtitle="#59AEB3",
    text="#E5D8BD",
    muted="#7EB6B5",
    meter_background="#0A1719",
    meter_border="#6E5733",
    meter_text="#E8D0A0",
    overall_chunk="#3F9395",
    quote_background="#D8BF91",
    quote_text="#302719",
)

RYLO_THEME = DashboardTheme(
    key="rylo",
    folder="Rylo",
    accents=("#8B0E14", "#A72A30", "#6F1C22", "#B53B40", "#75272B", "#9A171E"),
    panel="rgba(15, 17, 20, 232)",
    panel_hover="rgba(28, 29, 33, 238)",
    border="#48494E",
    border_hover="#7A3035",
    title="#D7CDBD",
    subtitle="#A9A39A",
    text="#D8D0C2",
    muted="#A39C92",
    meter_background="#090B0E",
    meter_border="#505157",
    meter_text="#E0D6C5",
    overall_chunk="#8B0E14",
    quote_background="#26272B",
    quote_text="#D0C8B9",
)


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


@dataclass(frozen=True)
class SpriteRef:
    filename: str
    columns: int
    rows: int
    index: int
    inset_x: float = 0.0
    inset_y: float = 0.0


# BFF base sheet follows the original 6x4 mockup order. The extra 3x3 sheet
# fills the categories whose original cells were absent or contained baked
# progress art. Motifs/Antiquities/Lorebooks are reserved here for future cards.
BFF_BADGES: dict[str, SpriteRef] = {
    "Mounts": SpriteRef("badges.png", 6, 4, 0, 0.06, 0.03),
    "Pets": SpriteRef("badges.png", 6, 4, 1, 0.06, 0.03),
    "Armor Styles": SpriteRef("badges.png", 6, 4, 2, 0.06, 0.03),
    "Costumes": SpriteRef("badges.png", 6, 4, 5, 0.06, 0.03),
    "Personalities": SpriteRef("badges.png", 6, 4, 6, 0.06, 0.03),
    "Emotes": SpriteRef("badges.png", 6, 4, 7, 0.06, 0.03),
    "Mementos": SpriteRef("badges.png", 6, 4, 9, 0.06, 0.03),
    "Furnishings": SpriteRef("badges.png", 6, 4, 10, 0.06, 0.03),
    "Assistants": SpriteRef("badges.png", 6, 4, 11, 0.06, 0.03),
    "Companions": SpriteRef("badges.png", 6, 4, 12, 0.06, 0.03),
    "Body Markings": SpriteRef("badges.png", 6, 4, 13, 0.06, 0.03),
    "Head Markings": SpriteRef("badges.png", 6, 4, 14, 0.06, 0.03),
    "Hair": SpriteRef("badges.png", 6, 4, 15, 0.06, 0.03),
    "Hats": SpriteRef("badges.png", 6, 4, 3, 0.06, 0.03),
    "Facial Hair / Horns": SpriteRef("badges.png", 6, 4, 16, 0.06, 0.03),
    "Piercing / Jewelry": SpriteRef("badges.png", 6, 4, 17, 0.06, 0.03),
    "Tools & Upgrades": SpriteRef("badges.png", 6, 4, 20, 0.06, 0.03),
    "Customized Actions": SpriteRef("badges.png", 6, 4, 21, 0.06, 0.03),
    "Skins": SpriteRef("badges_2.png", 3, 3, 0, 0.03, 0.03),
    "Weapon Styles": SpriteRef("badges_2.png", 3, 3, 1, 0.03, 0.03),
    "Houses": SpriteRef("badges_2.png", 3, 3, 2, 0.03, 0.03),
    "Polymorphs": SpriteRef("badges_2.png", 3, 3, 3, 0.03, 0.03),
    "Facial Accessories": SpriteRef("badges_2.png", 3, 3, 4, 0.03, 0.03),
    "Fragments": SpriteRef("badges_2.png", 3, 3, 5, 0.03, 0.03),
    "Motifs": SpriteRef("badges_2.png", 3, 3, 6, 0.03, 0.03),
    "Antiquities": SpriteRef("badges_2.png", 3, 3, 7, 0.03, 0.03),
    "Lorebooks": SpriteRef("badges_2.png", 3, 3, 8, 0.03, 0.03),
}

# Rylo's current red/black 6x4 sheet follows the generated semantic order.
# An optional badges_2.png uses the same 3x3 expansion order as BFF; when it is
# absent, those categories simply retain their glyph fallback rather than
# borrowing BFF artwork.
RYLO_BADGES: dict[str, SpriteRef] = {
    "Mounts": SpriteRef("badges.png", 6, 4, 0, 0.05, 0.03),
    "Pets": SpriteRef("badges.png", 6, 4, 1, 0.05, 0.03),
    "Armor Styles": SpriteRef("badges.png", 6, 4, 2, 0.05, 0.03),
    "Skins": SpriteRef("badges.png", 6, 4, 4, 0.05, 0.03),
    "Costumes": SpriteRef("badges.png", 6, 4, 5, 0.05, 0.03),
    "Personalities": SpriteRef("badges.png", 6, 4, 6, 0.05, 0.03),
    "Emotes": SpriteRef("badges.png", 6, 4, 7, 0.05, 0.03),
    "Polymorphs": SpriteRef("badges.png", 6, 4, 8, 0.05, 0.03),
    "Mementos": SpriteRef("badges.png", 6, 4, 9, 0.05, 0.03),
    "Furnishings": SpriteRef("badges.png", 6, 4, 10, 0.05, 0.03),
    "Assistants": SpriteRef("badges.png", 6, 4, 11, 0.05, 0.03),
    "Companions": SpriteRef("badges.png", 6, 4, 12, 0.05, 0.03),
    "Body Markings": SpriteRef("badges.png", 6, 4, 13, 0.05, 0.03),
    "Head Markings": SpriteRef("badges.png", 6, 4, 14, 0.05, 0.03),
    "Hair": SpriteRef("badges.png", 6, 4, 15, 0.05, 0.03),
    "Hats": SpriteRef("badges.png", 6, 4, 16, 0.05, 0.03),
    "Facial Accessories": SpriteRef("badges.png", 6, 4, 17, 0.05, 0.03),
    "Facial Hair / Horns": SpriteRef("badges.png", 6, 4, 18, 0.05, 0.03),
    "Piercing / Jewelry": SpriteRef("badges.png", 6, 4, 19, 0.05, 0.03),
    "Houses": SpriteRef("badges.png", 6, 4, 20, 0.05, 0.03),
    "Customized Actions": SpriteRef("badges.png", 6, 4, 21, 0.05, 0.03),
    "Fragments": SpriteRef("badges.png", 6, 4, 22, 0.05, 0.03),
    "Tools & Upgrades": SpriteRef("badges.png", 6, 4, 23, 0.05, 0.03),
    "Weapon Styles": SpriteRef("badges_2.png", 3, 3, 1, 0.03, 0.03),
    "Motifs": SpriteRef("badges_2.png", 3, 3, 6, 0.03, 0.03),
    "Antiquities": SpriteRef("badges_2.png", 3, 3, 7, 0.03, 0.03),
    "Lorebooks": SpriteRef("badges_2.png", 3, 3, 8, 0.03, 0.03),
}


class SpriteSheet:
    """Lazy grid PNG slicer with optional in-cell crop padding and caching."""

    def __init__(
        self,
        path: Path,
        columns: int,
        rows: int,
        inset_x: float = 0.0,
        inset_y: float = 0.0,
    ) -> None:
        self.path = path
        self.columns = columns
        self.rows = rows
        self.inset_x = max(0.0, min(0.45, inset_x))
        self.inset_y = max(0.0, min(0.45, inset_y))
        self._sheet: QPixmap | None = None
        self._cache: dict[int, QPixmap] = {}

    def _load(self) -> None:
        if self._sheet is None:
            self._sheet = QPixmap(str(self.path))

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
        left = column * cell_width + cell_width * self.inset_x
        top = row * cell_height + cell_height * self.inset_y
        right = (column + 1) * cell_width - cell_width * self.inset_x
        bottom = (row + 1) * cell_height - cell_height * self.inset_y
        cropped = self._sheet.copy(
            round(left),
            round(top),
            max(1, round(right - left)),
            max(1, round(bottom - top)),
        )
        self._cache[index] = cropped
        return cropped


_SPRITE_SHEETS: dict[tuple[str, int, int, float, float], SpriteSheet] = {}


def _theme_root(theme: DashboardTheme) -> Path:
    root = Path(__file__).resolve().parents[1] / "assets" / "themes"
    preferred = root / theme.folder / "collectibles"
    if preferred.exists():
        return preferred
    return root / theme.folder.casefold() / "collectibles"


def _active_theme() -> DashboardTheme:
    app = QApplication.instance()
    visual_theme = app.property("visualTheme") if app is not None else None
    return RYLO_THEME if visual_theme == VISUAL_THEME_RYLO else BFF_THEME


def _sheet_for(theme: DashboardTheme, ref: SpriteRef) -> SpriteSheet:
    path = _theme_root(theme) / ref.filename
    key = (str(path), ref.columns, ref.rows, ref.inset_x, ref.inset_y)
    sheet = _SPRITE_SHEETS.get(key)
    if sheet is None:
        sheet = SpriteSheet(path, ref.columns, ref.rows, ref.inset_x, ref.inset_y)
        _SPRITE_SHEETS[key] = sheet
    return sheet


def _badge_sprite(theme: DashboardTheme, label: str) -> QPixmap | None:
    manifest = RYLO_BADGES if theme.key == "rylo" else BFF_BADGES
    ref = manifest.get(label)
    if ref is None:
        return None
    return _sheet_for(theme, ref).cell(ref.index)


def _number_sprite(theme: DashboardTheme, index: int) -> QPixmap | None:
    ref = SpriteRef("numbers.png", 6, 4, index, 0.05, 0.04)
    return _sheet_for(theme, ref).cell(index)


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
    def __init__(self, accent: str, theme: DashboardTheme, parent=None):
        super().__init__(parent)
        self.value = 0
        self.accent = QColor(accent)
        self.theme = theme
        self.setFixedSize(76, 76)

    def setValue(self, value: int) -> None:
        self.value = max(0, min(100, int(value)))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(8, 8, self.width() - 16, self.height() - 16)
        painter.setPen(QPen(QColor(self.theme.meter_background), 8))
        painter.drawArc(rect, 0, 360 * 16)
        painter.setPen(QPen(self.accent, 8))
        painter.drawArc(rect, 90 * 16, -round(360 * 16 * self.value / 100))
        painter.setPen(QColor(self.theme.meter_text))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.value}%")


class ShieldMeter(QWidget):
    def __init__(self, accent: str, theme: DashboardTheme, parent=None):
        super().__init__(parent)
        self.value = 0
        self.accent = QColor(accent)
        self.theme = theme
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
        painter.fillPath(path, QColor(self.theme.meter_background))
        painter.setPen(QPen(QColor(self.theme.meter_border), 2))
        painter.drawPath(path)
        painter.save()
        painter.setClipPath(path)
        fill_height = self.height() * self.value / 100
        painter.fillRect(0, self.height() - fill_height, self.width(), fill_height, self.accent)
        painter.restore()
        painter.setPen(QColor(self.theme.meter_text))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.value}%")


class VialMeter(QWidget):
    def __init__(self, accent: str, theme: DashboardTheme, parent=None):
        super().__init__(parent)
        self.value = 0
        self.accent = QColor(accent)
        self.theme = theme
        self.setFixedSize(58, 88)

    def setValue(self, value: int) -> None:
        self.value = max(0, min(100, int(value)))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        tube = QRectF(18, 10, 22, 68)
        painter.setBrush(QColor(self.theme.meter_background))
        painter.setPen(QPen(QColor(self.theme.meter_border), 2))
        painter.drawRoundedRect(tube, 8, 8)
        inner = tube.adjusted(4, 4, -4, -4)
        fill_height = inner.height() * self.value / 100
        painter.fillRect(
            QRectF(inner.left(), inner.bottom() - fill_height, inner.width(), fill_height),
            self.accent,
        )
        painter.setBrush(QColor(self.theme.border_hover))
        painter.drawRect(QRectF(14, 5, 30, 8))
        painter.setPen(QColor(self.theme.meter_text))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(QRectF(0, 68, self.width(), 20), Qt.AlignmentFlag.AlignCenter, f"{self.value}%")


class ProgressTile(QFrame):
    clicked = Signal(str)

    def __init__(self, spec: DashboardSpec, index: int, theme: DashboardTheme, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.index = index
        self.theme = theme
        self.percent = 0
        self.owned = 0
        self.total = 0
        self.accent = theme.accents[(index - 1) % len(theme.accents)]
        self.setProperty("collectibleDashboardTile", True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumSize(178, 154)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(
            "QFrame[collectibleDashboardTile='true'] {"
            f" background-color: {theme.panel}; border: 1px solid {theme.border}; border-radius: 4px;"
            "}"
            "QFrame[collectibleDashboardTile='true']:hover {"
            f" background-color: {theme.panel_hover}; border: 1px solid {theme.border_hover};"
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
        if not self._set_sprite(number, _number_sprite(self.theme, self.index - 1), 32):
            number.setStyleSheet(
                f"color:{self.theme.title}; border:1px solid {self.theme.border}; "
                "border-radius:2px; font-weight:700;"
            )
        title = QLabel(self.spec.label.upper())
        title.setWordWrap(True)
        title.setStyleSheet(f"color:{self.theme.title}; font-weight:700; letter-spacing:1px;")
        heading.addWidget(number)
        heading.addWidget(title, 1)
        layout.addLayout(heading)

        center = QHBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(8)

        self.glyph = QLabel(self.spec.glyph)
        self.glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.glyph.setFixedSize(72, 72)
        if not self._set_sprite(self.glyph, _badge_sprite(self.theme, self.spec.label), 72):
            self.glyph.setStyleSheet(
                f"color:{self.accent}; font-size:27px; border:1px solid {self.theme.border}; "
                f"border-radius:36px; background:{self.theme.meter_background};"
            )

        if self.spec.meter == "ring":
            self.meter = RingMeter(self.accent, self.theme)
            center.addStretch(1)
            center.addWidget(self.glyph)
            center.addWidget(self.meter)
            center.addStretch(1)
        elif self.spec.meter == "shield":
            self.meter = ShieldMeter(self.accent, self.theme)
            center.addStretch(1)
            center.addWidget(self.glyph)
            center.addWidget(self.meter)
            center.addStretch(1)
        elif self.spec.meter == "vial":
            self.meter = VialMeter(self.accent, self.theme)
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
                f"QProgressBar {{background:{self.theme.meter_background}; border:1px solid {self.theme.meter_border}; border-radius:5px;}}"
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
        self.count_label.setStyleSheet(f"color:{self.theme.text}; font-weight:600;")
        self.state_label = QLabel("Unexplored territory")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setStyleSheet(f"color:{self.theme.muted}; font-size:10px;")
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
    """Shared main Collections dashboard with theme-specific presentation."""

    categoryRequested = Signal(str)
    GRID_COLUMNS = 6

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.theme = _active_theme()
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
        title.setStyleSheet(f"color:{self.theme.title}; font-size:28px; font-weight:700; letter-spacing:2px;")
        subtitle = QLabel("ACCOUNT PROGRESS OVERVIEW")
        subtitle.setStyleSheet(f"color:{self.theme.subtitle}; font-size:14px; letter-spacing:2px;")
        rule = QLabel("────── ✦ ──────")
        rule.setStyleSheet(f"color:{self.theme.border_hover};")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        title_block.addWidget(rule)
        top.addLayout(title_block, 2)

        overall_box = QFrame()
        overall_box.setStyleSheet(
            f"QFrame {{background:{self.theme.panel}; border:1px solid {self.theme.border}; border-radius:4px;}}"
        )
        overall_layout = QVBoxLayout(overall_box)
        overall_layout.setContentsMargins(12, 8, 12, 8)
        overall_label = QLabel("✥  OVERALL PROGRESS")
        overall_label.setStyleSheet(f"color:{self.theme.title}; font-weight:700; letter-spacing:1px;")
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setFixedHeight(22)
        self.overall_progress.setStyleSheet(
            f"QProgressBar {{background:{self.theme.meter_background}; border:1px solid {self.theme.meter_border}; "
            f"border-radius:6px; color:{self.theme.meter_text}; text-align:center;}}"
            f"QProgressBar::chunk {{background:{self.theme.overall_chunk}; border-radius:5px;}}"
        )
        self.overall_count = QLabel("0 / 0 collectibles secured")
        self.overall_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.overall_count.setStyleSheet(f"color:{self.theme.text};")
        overall_layout.addWidget(overall_label)
        overall_layout.addWidget(self.overall_progress)
        overall_layout.addWidget(self.overall_count)
        top.addWidget(overall_box, 2)

        quote = QFrame()
        quote.setStyleSheet(
            f"QFrame {{background:{self.theme.quote_background}; border:1px solid {self.theme.border}; border-radius:3px;}}"
        )
        quote_layout = QVBoxLayout(quote)
        quote_layout.setContentsMargins(12, 10, 12, 10)
        quote_text = QLabel(
            "“Every discovery\nadds to your legend.”"
            if self.theme.key == "bff"
            else "“Catalog it.\nThen get the rest.”"
        )
        quote_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quote_text.setStyleSheet(
            f"color:{self.theme.quote_text}; font-size:12px; font-style:italic; font-weight:600;"
        )
        quote_layout.addWidget(quote_text)
        top.addWidget(quote, 1)
        root.addLayout(top)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color:{self.theme.border};")
        root.addWidget(divider)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(7)
        for column in range(self.GRID_COLUMNS):
            grid.setColumnStretch(column, 1)

        for index, spec in enumerate(DASHBOARD_SPECS, start=1):
            tile = ProgressTile(spec, index, self.theme)
            tile.clicked.connect(self.categoryRequested.emit)
            self._tiles.append(tile)
            row = (index - 1) // self.GRID_COLUMNS
            column = (index - 1) % self.GRID_COLUMNS
            grid.addWidget(tile, row, column)

        root.addLayout(grid)

        footer_text = (
            "✦  New discoveries await beyond the known.  ✦"
            if self.theme.key == "bff"
            else "◆  Inventory incomplete. Continue.  ◆"
        )
        footer = QLabel(footer_text)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color:{self.theme.subtitle}; font-size:11px; letter-spacing:1px;")
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
