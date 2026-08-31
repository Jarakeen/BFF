from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QToolButton, QWidget

from engine.config import get_resource_path


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


def icon_path(name: str) -> Path | None:
    if not name:
        return None
    filename = name if name.lower().endswith(".svg") else f"{name}.svg"
    for parts in _ICON_ROOTS:
        candidate = get_resource_path(*parts, filename)
        if candidate.exists():
            return candidate
    return None


def icon(name: str) -> QIcon:
    path = icon_path(name)
    return QIcon(str(path)) if path is not None else QIcon()


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


def set_button_icon(button_widget: QPushButton | QToolButton, name: str | None = None, size: int = 15) -> None:
    icon_name = name or semantic_icon(button_widget.text(), button=True)
    value = icon(icon_name)
    if value.isNull():
        return
    button_widget.setIcon(value)
    button_widget.setIconSize(QSize(size, size))


def icon_label(name: str, size: int = 18, parent: QWidget | None = None) -> QLabel:
    label = QLabel(parent)
    label.setFixedSize(size, size)
    label.setScaledContents(True)
    path = icon_path(name)
    if path is not None:
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            label.setPixmap(pixmap)
    return label
