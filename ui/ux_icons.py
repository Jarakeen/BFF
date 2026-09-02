from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QToolButton, QWidget

from engine.config import get_resource_path
from services.accessibility_preferences import VISUAL_THEME_RYLO


_ICON_ROOTS = (
    ("assets", "icon"),
    ("assets", "icons"),
    ("assets", "themes", "bff", "icons"),
)

# The icon library is intentionally semantic: pages/cards/buttons ask for meaning,
# not a hard-coded filename. That keeps the visual language consistent.
_EXACT = {
    "raid engine overview": "dashboard",
    "overview": "dashboard",
    "encounters": "trial",
    "boss guide": "boss",
    "mechanics": "crossed-swords",
    "assignments": "assignment",
    "team optimization": "gears",
    "optimization": "optimization",
    "coverage & buff management": "compass",
    "coverage": "compass",
    "combat reference": "open-book",
    "reference data": "reference",
    "builds": "builds",
    "performance": "capabilities",
    "achievements": "achievement",
    "collections": "collections",
    "settings": "settings",
    "broadcast": "broadcast",
    "broadcast desk": "broadcast",
    "field notes": "field-notes",
    "live operations": "live-operations",
    "archive": "archive",
    "raid status": "check-mark",
    "coverage summary": "compass",
    "warnings": "hazard-sign",
    "raid roster": "users",
    "selected player": "person",
    "provides": "potion-ball",
    "current gear": "leather-armor",
    "key stats": "dashboard",
    "capability gap": "warning",
    "optimization highlights": "gears",
    "upcoming mechanics": "crossed-swords",
    "raid notes": "scroll-quill",
    "encounter": "boss",
    "encounter overview": "boss",
    "encounter facts": "book-open-text",
    "quick notes": "feather",
    "abilities": "crossed-swords",
    "phase & thresholds": "hourglass",
    "strategy overview": "treasure-map",
    "assignment summary": "assignment",
    "important call outs": "hazard-sign",
    "encounter timer": "stopwatch",
    "my notes": "feather",
    "key reminders": "lantern",
    "historical notes": "archive",
    "select boss": "boss",
    "positioning": "treasure-map",
    "player assignments": "assignment",
    "phase timeline overview": "hourglass",
    "event details": "stopwatch",
    "mechanics reference": "open-book",
    "mechanic details": "crossed-swords",
    "constraints": "gears",
    "available players": "users",
    "proposed team": "users",
    "team analysis": "binoculars",
    "support summary": "potion-ball",
    "key risks": "hazard-sign",
    "recommended changes": "gears",
    "gear recommendations": "leather-armor",
    "skill recommendations": "lunar-wand",
    "notes": "feather",
    "coverage plan": "compass",
    "most reliable providers": "users",
    "coverage notes": "scroll-quill",
    "reference index": "book-search",
    "reference entry": "open-book",
    "related effects / appears in": "compass",
    "why did we die?": "death-skull",
    "mechanic visual": "binoculars",
    "needs attention": "hazard-sign",
    "team summary": "users",
    "assignment notes": "scroll-quill",
    "roster": "roster",
    "personnel record": "person",
    "the foundry": "gears",
}

_KEYWORDS = (
    ("warning", "hazard-sign"), ("risk", "hazard-sign"), ("death", "death-skull"),
    ("timer", "stopwatch"), ("timeline", "hourglass"), ("phase", "hourglass"),
    ("mechanic", "crossed-swords"), ("boss", "boss"), ("encounter", "trial"),
    ("assignment", "assignment"), ("roster", "users"), ("team", "users"),
    ("player", "person"), ("gear", "leather-armor"), ("build", "builds"),
    ("skill", "lunar-wand"), ("coverage", "compass"), ("buff", "potion-ball"),
    ("reference", "open-book"), ("note", "feather"), ("archive", "archive"),
    ("optimization", "gears"), ("settings", "settings"),
)

_BUTTON_KEYWORDS = (
    ("save", "check-mark"), ("apply", "check-mark"), ("generate", "gears"),
    ("auto-fill", "check-mark"), ("edit", "pen-tool"), ("add", "plus"),
    ("new", "plus"), ("remove", "cancel"), ("delete", "cancel"),
    ("discard", "cancel"), ("clear", "cancel"), ("reset", "refresh"),
    ("refresh", "refresh"), ("search", "search"), ("view", "binoculars"),
    ("import", "download"), ("start", "stopwatch"), ("analyze", "binoculars"),
)

# Rylo icon colors are identity states, not semantic combat states. Keep them
# steel/stone so semantic blue/orange/gold remains meaningful elsewhere.
_RYLO_DEFAULT = "#AEB3B7"
_RYLO_ACTIVE = "#D4D1CB"
_RYLO_DISABLED = "#676B70"
_RYLO_SELECTED = "#B88A3C"


def _is_rylo_theme() -> bool:
    app = QApplication.instance()
    return bool(app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO)


def icon_path(name: str) -> Path | None:
    if not name:
        return None
    filename = name if name.lower().endswith(".svg") else f"{name}.svg"
    for parts in _ICON_ROOTS:
        candidate = get_resource_path(*parts, filename)
        if candidate.exists():
            return candidate
    return None


def _recolor_svg(svg: str, tone: str) -> str:
    """Flatten a source SVG into Rylo's matte steel icon language.

    The existing library contains a mix of gold glyphs and full-canvas dark
    backing squares. Rylo keeps the shapes, removes those tiles, and treats
    color as state rather than decoration.
    """
    svg = re.sub(
        r'<path(?=[^>]*d=["\']M0\s+0h512v512H0z["\'])[^>]*/?>',
        '',
        svg,
        flags=re.IGNORECASE,
    )
    svg = re.sub(
        r'<path(?=[^>]*d=["\']M0\s+0\s+h512\s+v512\s+H0\s+z["\'])[^>]*/?>',
        '',
        svg,
        flags=re.IGNORECASE,
    )

    svg = re.sub(r'fill=["\']#[0-9A-Fa-f]{3,8}["\']', f'fill="{tone}"', svg)
    svg = re.sub(r'stroke=["\']#[0-9A-Fa-f]{3,8}["\']', f'stroke="{tone}"', svg)
    svg = re.sub(r'fill\s*:\s*#[0-9A-Fa-f]{3,8}', f'fill:{tone}', svg)
    svg = re.sub(r'stroke\s*:\s*#[0-9A-Fa-f]{3,8}', f'stroke:{tone}', svg)
    return svg


@lru_cache(maxsize=512)
def _rylo_pixmap(path_text: str, tone: str, size: int) -> QPixmap:
    path = Path(path_text)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return QPixmap()

    renderer = QSvgRenderer(QByteArray(_recolor_svg(source, tone).encode("utf-8")))
    if not renderer.isValid():
        return QPixmap()

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def _rylo_icon(path: Path, size: int = 32) -> QIcon:
    result = QIcon()
    result.addPixmap(_rylo_pixmap(str(path), _RYLO_DEFAULT, size), QIcon.Mode.Normal, QIcon.State.Off)
    result.addPixmap(_rylo_pixmap(str(path), _RYLO_ACTIVE, size), QIcon.Mode.Active, QIcon.State.Off)
    result.addPixmap(_rylo_pixmap(str(path), _RYLO_SELECTED, size), QIcon.Mode.Selected, QIcon.State.Off)
    result.addPixmap(_rylo_pixmap(str(path), _RYLO_DISABLED, size), QIcon.Mode.Disabled, QIcon.State.Off)
    result.addPixmap(_rylo_pixmap(str(path), _RYLO_SELECTED, size), QIcon.Mode.Normal, QIcon.State.On)
    return result


def icon(name: str) -> QIcon:
    path = icon_path(name)
    if path is None:
        return QIcon()
    if _is_rylo_theme() and path.suffix.casefold() == ".svg":
        return _rylo_icon(path)
    return QIcon(str(path))


def semantic_icon(text: str, *, button: bool = False) -> str:
    value = (text or "").strip().lower()
    value = value.replace("▸", "").replace("▾", "").strip()
    if value in _EXACT:
        return _EXACT[value]
    source = _BUTTON_KEYWORDS if button else _KEYWORDS
    for needle, name in source:
        if needle in value:
            return name
    return ""


def set_button_icon(
    button_widget: QPushButton | QToolButton,
    name: str | None = None,
    size: int = 15,
) -> None:
    icon_name = name or semantic_icon(button_widget.text(), button=True)
    value = icon(icon_name)
    if value.isNull():
        return
    button_widget.setIcon(value)
    button_widget.setIconSize(QSize(size, size))
    button_widget.setProperty("semanticIconName", icon_name)


def icon_label(name: str, size: int = 18, parent: QWidget | None = None) -> QLabel:
    label = QLabel(parent)
    label.setFixedSize(size, size)
    label.setScaledContents(True)
    value = icon(name)
    if not value.isNull():
        label.setPixmap(value.pixmap(size, size))
        label.setProperty("semanticIconName", name)
    return label


def refresh_theme_icons(root: QWidget | QApplication | None = None) -> None:
    """Refresh semantic icons, page headers, and brand marks after an in-app theme switch."""
    app = QApplication.instance()
    if app is None:
        return

    roots = app.topLevelWidgets() if root is None or isinstance(root, QApplication) else [root]
    for top in roots:
        buttons = list(top.findChildren(QPushButton)) + list(top.findChildren(QToolButton))
        for button in buttons:
            name = button.property("semanticIconName") or semantic_icon(button.text(), button=True)
            if name:
                set_button_icon(button, str(name), button.iconSize().width() or 15)

        for label in top.findChildren(QLabel):
            name = label.property("semanticIconName")
            if not name:
                continue
            size = max(1, min(label.width() or 18, label.height() or 18))
            value = icon(str(name))
            if not value.isNull():
                label.setPixmap(value.pixmap(size, size))

        try:
            from ui.components.foundry_header import FoundryHeader
            for header in top.findChildren(FoundryHeader):
                header.refresh_visual_theme()
        except ImportError:
            pass

        try:
            from ui.components.foundry_card import FoundryCard
            for card in top.findChildren(FoundryCard):
                name = getattr(card, "_icon_name", "")
                if name:
                    card.set_icon(name)
        except ImportError:
            pass

        sidebar = getattr(top, "sidebar", None)
        if sidebar is not None and hasattr(sidebar, "refresh_brand_mark"):
            sidebar.refresh_brand_mark()
