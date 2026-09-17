from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QToolButton, QWidget

from engine.config import get_resource_path
from services.accessibility_preferences import is_rylo_visual_theme


_ICON_ROOTS = (
    ("assets", "icon"),
    ("assets", "icons"),
    ("assets", "themes", "bff", "icons"),
)

# The icon library is intentionally semantic: pages/cards/buttons ask for meaning,
# not a hard-coded filename. That keeps the visual language consistent.
_EXACT = {
    "raid engine": "gears",
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
    "characters": "character",
    "comp maker": "maker",
    "builds": "builds",
    "rotations": "rotations",
    "performance": "capabilities",
    "achievements": "achievement",
    "collections": "collections",
    "collectibles": "collections",
    "tool": "tool",
    "tools": "tool",
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
    ("auto-fill", "check-mark"), ("edit", "pen"), ("add", "plus"),
    ("new", "plus"), ("remove", "cancel"), ("delete", "cancel"),
    ("discard", "cancel"), ("clear", "cancel"), ("reset", "refresh"),
    ("refresh", "refresh"), ("search", "search"), ("view", "binoculars"),
    ("import", "download"), ("start", "stopwatch"), ("analyze", "binoculars"),
)

# Friendly semantic aliases for the evolving canonical icon library. The project
# already contains a mixture of spaces, hyphens, underscores, singular/plural names,
# and older names. Callers should not need to care which spelling won that week.
_ICON_ALIASES = {
    "user": ("user", "person", "character"),
    "build": ("build", "builds"),
    "builds": ("builds", "build"),
    "field-office": ("field-office", "field_office", "field office", "notebook"),
    "field_office": ("field_office", "field-office", "field office", "notebook"),
    "book_open_text": ("book_open_text", "book-open-text", "open-book"),
    "book-open-text": ("book-open-text", "book_open_text", "open-book"),
    "crossed_swords": ("crossed_swords", "crossed-swords", "set"),
    "crossed-swords": ("crossed-swords", "crossed_swords", "set"),
    "swapping": ("swapping", "switch-weapon"),
    "drop": ("drop", "potion", "stamina"),
    "scales": ("scales", "balance", "optimization"),
    "pen-tool": ("pen-tool", "pen"),
    "stream-events": ("stream-events", "stream_events"),
    "stream_events": ("stream_events", "stream-events"),
    "health": ("health", "role-healer"),
    "role-healer": ("role-healer", "health"),
    "role-tank": ("role-tank", "shield"),
    "role-dd": ("role-dd", "set"),
    "role-support-dd": ("role-support-dd", "set"),
    "head": ("viking-helmet", "head"),
    "shoulder": ("spiked-shoulder-armor", "shoulder"),
    "shoulders": ("spiked-shoulder-armor", "shoulders"),
    "chest": ("leather-armor", "leather_armor", "chest"),
    "hands": ("mailed-fist", "hands"),
    "waist": ("metal-skirt", "metal_skirt", "waist"),
    "legs": ("greaves", "legs"),
    "feet": ("metal-boot", "metal_boot", "feet"),
    "neck": ("heart-necklace", "heart_necklace", "neck"),
    "ring": ("ring",),
    "main-hand": ("lunar-wand", "lunar_wand", "main-hand"),
    "off-hand": ("shield", "off-hand"),
    "food": ("food", "coffee"),
    "potion": ("potion",),
    "powered": ("Powered", "powered"),
    "charged": ("Charged", "charged"),
    "precise": ("Precise", "precise"),
    "infused": ("Infused", "infused"),
    "defending": ("Defending", "defending"),
    "training": ("Training", "training"),
    "sharpened": ("Sharpened", "sharpened"),
    "decisive": ("Decisive", "decisive"),
    "nirnhoned": ("drop", "Nirnhoned", "nirnhoned"),
    "sturdy": ("Sturdy", "sturdy"),
    "impenetrable": ("Impenetrable", "impenetrable"),
    "reinforced": ("Reinforced", "reinforced"),
    "well-fitted": ("Well-fitted", "well_fitted", "well-fitted"),
    "invigorating": ("Invigorating", "invigorating"),
    "divines": ("Divines", "divines"),
    "healthy": ("Health", "health", "Healthy", "healthy"),
    "arcane": ("magic", "Arcane", "arcane"),
    "robust": ("Robust", "robust"),
    "bloodthirsty": ("drop", "Bloodthirsty", "bloodthirsty"),
    "harmony": ("Harmony", "harmony"),
    "triune": ("Triune", "triune"),
    "protective": ("Protective", "protective"),
    "swift": ("Swift", "swift"),
    "scales": ("scales", "optimization"),
    "cog": ("cog", "gears"),
    "drop": ("drop", "potion"),
}

# Rylo icon colors are identity states, not semantic combat states. Keep them
# steel/stone so semantic blue/orange/gold remains meaningful elsewhere.
_FOUNDRY_DEFAULT = "#C8A46A"
_FOUNDRY_ACTIVE = "#D8B86F"
_FOUNDRY_DISABLED = "#73777C"
_FOUNDRY_SELECTED = "#E0C27A"

_RYLO_DEFAULT = "#AEB3B7"
_RYLO_ACTIVE = "#D4D1CB"
_RYLO_DISABLED = "#676B70"
_RYLO_SELECTED = "#B88A3C"


def _is_rylo_theme() -> bool:
    app = QApplication.instance()
    theme = app.property("visualTheme") if app is not None else ""
    return is_rylo_visual_theme(str(theme or ""))


def _icon_name_candidates(name: str) -> tuple[str, ...]:
    raw = str(name or "").strip()
    if not raw:
        return ()
    stem = raw[:-4] if raw.lower().endswith(".svg") else raw
    values: list[str] = []
    for candidate in _ICON_ALIASES.get(stem, (stem,)):
        for variant in (
            candidate,
            candidate.replace("_", "-"),
            candidate.replace("_", " "),
            candidate.replace("-", "_"),
            candidate.replace("-", " "),
            candidate.replace(" ", "-"),
            candidate.replace(" ", "_"),
        ):
            if variant and variant not in values:
                values.append(variant)
    return tuple(values)


def _normalized_icon_stem(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


@lru_cache(maxsize=512)
def icon_path(name: str) -> Path | None:
    candidates = _icon_name_candidates(name)

    # Fast path: exact reviewed filenames and spelling aliases.
    for candidate_name in candidates:
        filename = f"{candidate_name}.svg"
        for parts in _ICON_ROOTS:
            candidate = get_resource_path(*parts, filename)
            if candidate.exists():
                return candidate

    # The icon folder is intentionally user-extensible and has accumulated
    # spaces, hyphens, underscores, capitalization, and Windows localized-name
    # oddities. Resolve those differences by normalized stem instead of silently
    # dropping the icon. This also means newly added class/trait icons work
    # without another code edit merely because their filename uses TitleCase.
    wanted = {_normalized_icon_stem(candidate) for candidate in candidates}
    wanted.discard("")
    for parts in _ICON_ROOTS:
        root = get_resource_path(*parts)
        if not root.is_dir():
            continue
        try:
            files = tuple(root.iterdir())
        except OSError:
            continue
        for candidate in files:
            if candidate.suffix.casefold() != ".svg":
                continue
            if _normalized_icon_stem(candidate.stem) in wanted:
                return candidate
    return None



def _strip_full_canvas_background(svg: str) -> str:
    """Remove opaque 512x512 backing tiles while preserving the source glyph colors."""
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
    return svg


@lru_cache(maxsize=512)
def _source_svg_pixmap(path_text: str, size: int) -> QPixmap:
    """Render SVGs explicitly instead of depending on QIcon's SVG plugin path."""
    path = Path(path_text)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return QPixmap()

    renderer = QSvgRenderer(
        QByteArray(_strip_full_canvas_background(source).encode("utf-8"))
    )
    if not renderer.isValid():
        return QPixmap()

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def _source_svg_icon(path: Path, size: int = 48) -> QIcon:
    pixmap = _source_svg_pixmap(str(path), size)
    return QIcon(pixmap) if not pixmap.isNull() else QIcon()


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
    if path.suffix.casefold() == ".svg":
        if _is_rylo_theme():
            value = _rylo_icon(path)
            if not value.isNull():
                return value

        # Prefer Qt's native icon loader first. Some Windows/PySide builds are
        # happier loading the SVG as a QIcon than through an explicit renderer.
        # If that path fails, fall back to the explicit renderer used to strip
        # opaque backing tiles. The icon service should not become all-or-nothing
        # merely because one SVG code path is fussy.
        direct = QIcon(str(path))
        if not direct.isNull():
            return direct

        rendered = _source_svg_icon(path)
        if not rendered.isNull():
            return rendered
        return QIcon()

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
    button_widget.setProperty("semanticIconName", icon_name)
    value = icon(icon_name)
    if value.isNull():
        button_widget.setIcon(QIcon())
        return
    button_widget.setIcon(value)
    button_widget.setIconSize(QSize(size, size))


def icon_label(name: str, size: int = 18, parent: QWidget | None = None) -> QLabel:
    label = QLabel(parent)
    label.setFixedSize(size, size)
    label.setScaledContents(True)
    label.setProperty("semanticIconName", name)
    value = icon(name)
    if not value.isNull():
        label.setPixmap(value.pixmap(size, size))
    return label


def refresh_theme_icons(root: QWidget | QApplication | None = None) -> None:
    """Refresh semantic icons, page headers, and brand marks after an in-app theme switch."""
    # Icon assets are intentionally user-extensible. A previous miss must not
    # remain cached after files are added/pulled while the app is running.
    icon_path.cache_clear()
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
