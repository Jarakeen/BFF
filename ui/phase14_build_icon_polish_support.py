from __future__ import annotations

"""Final Phase 14 Builds icon and action polish.

This layer is presentation-only. It reuses the canonical New Build action, decorates
library class/role cells, restores skill art in the read-first inspector, and adds the
reviewed equipment/consumable icon vocabulary without changing saved builds or ESO data.
"""

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QBrush, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from engine.config import get_data_dir, get_resource_path
from services.skill_choice_service import load_skill_choices
from ui.components.foundry_card import FoundryCard
from ui.ux_icons import icon as semantic_icon, refresh_theme_icons

_INSTALLED = False

_ROLE_PRESENTATION = {
    "healer": ("health", "#59AEB3"),
    "tank": ("shield", "#8FA8B8"),
    "damage": ("set", "#C8A46A"),
    "damage dealer": ("set", "#C8A46A"),
    "dd": ("set", "#C8A46A"),
    "support dd": ("set", "#C8A46A"),
}

_SLOT_ICONS = {
    "head": "viking-helmet",
    "shoulders": "spiked-shoulder-armor",
    "shoulder": "spiked-shoulder-armor",
    "chest": "leather_armor",
    "hands": "mailed-fist",
    "waist": "metal_skirt",
    "legs": "greaves",
    "feet": "metal_boot",
    "neck": "heart_necklace",
    "necklace": "heart_necklace",
    "ring 1": "ring",
    "ring 2": "ring",
    "ring1": "ring",
    "ring2": "ring",
    "main hand": "lunar_wand",
    "off hand": "shield",
}


def _role_presentation(role: str) -> tuple[str, str] | None:
    value = str(role or "").strip().casefold()
    if "heal" in value:
        return _ROLE_PRESENTATION["healer"]
    if "tank" in value:
        return _ROLE_PRESENTATION["tank"]
    if value in {"damage", "damage dealer", "dd", "support dd"} or "damage dealer" in value:
        return _ROLE_PRESENTATION["damage dealer"]
    return None


def _tinted_icon(name: str, color: str, size: int = 22) -> QIcon:
    base = semantic_icon(name)
    if base.isNull():
        return QIcon()
    pixmap = base.pixmap(QSize(size, size))
    if pixmap.isNull():
        return QIcon()
    tinted = QPixmap(pixmap.size())
    tinted.fill(Qt.GlobalColor.transparent)
    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(color))
    painter.end()
    return QIcon(tinted)


def _icon_label(name: str, *, size: int = 22, color: str | None = None) -> QLabel:
    label = QLabel()
    label.setFixedSize(size, size)
    value = _tinted_icon(name, color, size) if color else semantic_icon(name)
    if not value.isNull():
        label.setPixmap(value.pixmap(QSize(size, size)))
    label.setToolTip(name.replace("_", " ").replace("-", " ").title())
    return label


def _class_icon(class_name: str, size: int = 22) -> QIcon:
    raw = str(class_name or "").strip()
    for candidate in (raw, raw.casefold(), raw.replace(" ", "-"), raw.casefold().replace(" ", "-")):
        value = semantic_icon(candidate)
        if not value.isNull():
            return value
    return QIcon()


def _move_new_build_to_header(page) -> None:
    button = getattr(page, "phase14_create_build_button", None)
    header = getattr(page, "header", None)
    if button is None or header is None:
        return
    if header.context_layout.indexOf(button) < 0:
        header.context_layout.addWidget(button)
    button.setText("+ Create New Build")
    button.setMinimumWidth(176)
    button.setMinimumHeight(40)
    button.setMaximumHeight(42)
    button.setProperty("phase14GoldAction", True)
    # Explicitly gold in both supported visual themes. The text/icon contrast does
    # not depend on hue, and the button remains the unique primary creation action.
    button.setStyleSheet(
        "QPushButton { background: #C8A46A; color: #0C171B; border: 1px solid #E0C27A; "
        "border-radius: 6px; padding: 7px 14px; font-weight: 700; }"
        "QPushButton:hover { background: #D8B86F; border-color: #E8CF8C; }"
        "QPushButton:pressed { background: #B8904E; }"
        "QPushButton:disabled { background: #75684E; color: #BFC8C6; border-color: #75684E; }"
    )


def _decorate_library_table(page) -> None:
    table = getattr(page, "phase14_build_table", None)
    sources = tuple(getattr(page, "phase14_table_source_rows", ()) or ())
    if table is None or not sources:
        return
    for row, source_index in enumerate(sources):
        kind_item = table.item(row, 2)
        if kind_item is not None and str(kind_item.text() or "").strip() == "Template":
            continue
        if source_index < 0 or source_index >= len(page.roster.Members):
            continue
        build = page.roster.Members[source_index]
        class_item = table.item(row, 3)
        role_item = table.item(row, 4)
        if class_item is not None:
            class_icon = _class_icon(str(getattr(build, "EsoClass", "") or ""), 20)
            if not class_icon.isNull():
                class_item.setIcon(class_icon)
        if role_item is not None:
            presentation = _role_presentation(str(getattr(build, "Role", "") or ""))
            if presentation is not None:
                role_icon_name, role_color = presentation
                role_icon = _tinted_icon(role_icon_name, role_color, 20)
                if not role_icon.isNull():
                    role_item.setIcon(role_icon)
                role_item.setForeground(QBrush(QColor(role_color)))


def _value_row(label: str, value: str, *, icon_name: str = "", icon_color: str | None = None) -> QWidget:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 3, 0, 3)
    layout.setSpacing(8)
    if icon_name:
        layout.addWidget(_icon_label(icon_name, size=22, color=icon_color))
    name = QLabel(label)
    name.setMinimumWidth(84)
    layout.addWidget(name)
    layout.addStretch(1)
    value_label = QLabel(value)
    value_label.setWordWrap(True)
    value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(value_label, 1)
    return host


def _header(page, build) -> QWidget:
    from ui import phase14_build_inspector_support as inspector

    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(10)

    class_icon = _class_icon(str(getattr(build, "EsoClass", "") or ""), 34)
    class_label = QLabel()
    class_label.setFixedSize(36, 36)
    if not class_icon.isNull():
        class_label.setPixmap(class_icon.pixmap(QSize(34, 34)))
    layout.addWidget(class_label)

    text = QVBoxLayout()
    text.setSpacing(3)
    title = QLabel(f"{inspector._text(build.Name, 'Unnamed Character')} — {inspector._text(build.BuildName, 'Default')}")
    title.setProperty("pageTitle", True)
    text.addWidget(title)

    meta = QHBoxLayout()
    meta.setContentsMargins(0, 0, 0, 0)
    meta.setSpacing(6)
    eso_class = inspector._text(getattr(build, "EsoClass", ""))
    if eso_class != "—":
        meta.addWidget(_icon_label(eso_class.casefold(), size=16))
        meta.addWidget(QLabel(eso_class))
    role = inspector._text(getattr(build, "Role", ""))
    presentation = _role_presentation(role) if role != "—" else None
    if presentation is not None:
        role_icon, role_color = presentation
        meta.addWidget(_icon_label(role_icon, size=16, color=role_color))
        role_label = QLabel(role)
        role_label.setStyleSheet(f"color: {role_color};")
        meta.addWidget(role_label)
    elif role != "—":
        meta.addWidget(QLabel(role))
    race = inspector._text(getattr(build, "Race", ""))
    if race != "—":
        meta.addWidget(QLabel(f"•  {race}"))
    meta.addStretch(1)
    text.addLayout(meta)
    layout.addLayout(text, 1)

    ready = QCheckBox("Ready")
    ready.setToolTip(
        "Mark this saved build as ready for raid. This is your own check, "
        "not a team or encounter check."
    )
    ready.setChecked(bool(getattr(build, "ReadyForRaid", False)))
    ready.toggled.connect(
        lambda checked, selected=build: page._set_build_ready(selected, checked)
    )
    layout.addWidget(ready)
    layout.addWidget(inspector._action_button(page))
    return host


def _gear_card(page, title: str, rows: list[tuple[str, object]]) -> FoundryCard:
    from ui import phase14_build_inspector_support as inspector

    card_icon = {
        "Armor": "leather_armor",
        "Jewelry": "heart_necklace",
        "Front Bar": "crossed-swords",
        "Back Bar": "crossed-swords",
    }.get(title, "leather_armor")
    card = FoundryCard(title, card_icon)
    for slot, value in rows:
        icon_name = _SLOT_ICONS.get(str(slot or "").strip().casefold(), "")
        card.addWidget(_value_row(slot, inspector._gear_summary(value), icon_name=icon_name))
    actions = QHBoxLayout()
    actions.addStretch(1)
    actions.addWidget(inspector._action_button(page))
    card.addLayout(actions)
    return card


@lru_cache(maxsize=1)
def _skill_texture_index() -> dict[str, str]:
    try:
        rows = load_skill_choices(get_data_dir() / "eso.db")
    except Exception:
        return {}
    result: dict[str, str] = {}
    for row in rows:
        name = str(row.get("name", "") or "").strip()
        texture = str(row.get("texture", "") or "").strip()
        if name and texture and name.casefold() not in result:
            result[name.casefold()] = texture
    return result


def _skill_icon(skill_name: str, size: int = 38) -> QIcon:
    texture = _skill_texture_index().get(str(skill_name or "").strip().casefold(), "")
    if not texture:
        return QIcon()
    filename = Path(texture.replace("\\", "/")).name
    local = get_resource_path("assets", "AbilityIcons", "icons", "128", str(Path(filename).with_suffix(".png")))
    return QIcon(str(local)) if local.exists() else QIcon()


def _skill_row(index: int, skill) -> QWidget:
    from ui import phase14_build_inspector_support as inspector

    name = inspector._text(skill, "Empty slot")
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 4, 0, 4)
    layout.setSpacing(9)
    icon_value = _skill_icon(name, 38)
    icon = QLabel()
    icon.setFixedSize(40, 40)
    if not icon_value.isNull():
        icon.setPixmap(icon_value.pixmap(QSize(38, 38)))
    layout.addWidget(icon)
    slot = QLabel(f"{index}")
    slot.setProperty("cardBadge", True)
    slot.setFixedWidth(24)
    layout.addWidget(slot)
    skill_label = QLabel(name)
    skill_label.setWordWrap(True)
    layout.addWidget(skill_label, 1)
    return host


def _skills_tab(page, build) -> QWidget:
    from ui import phase14_build_inspector_support as inspector

    tab = QWidget()
    layout = QHBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for title, values in (("Front Bar", build.FrontBarSkills), ("Back Bar", build.BackBarSkills)):
        card = FoundryCard(title, "lunar_wand")
        for index, skill in enumerate(values, start=1):
            card.addWidget(_skill_row(index, skill))
        card.addWidget(inspector._action_button(page))
        layout.addWidget(card, 1)
    return tab


def _consumables_tab(page, build) -> QWidget:
    from ui import phase14_build_inspector_support as inspector

    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    card = FoundryCard("Consumables", "potion")
    card.addWidget(_value_row("Food", inspector._text(build.Food, "Not selected"), icon_name="food"))
    card.addWidget(_value_row("Potion", inspector._text(build.Potion, "Not selected"), icon_name="potion"))
    card.addWidget(inspector._action_button(page))
    layout.addWidget(card)
    layout.addStretch(1)
    return tab


def _install_runtime_patches() -> None:
    from ui import phase14_build_inspector_support as inspector
    from ui import phase14_builds_command_center_support as command_center

    original_populate = command_center._populate_build_table

    def populate_with_icons(page) -> None:
        original_populate(page)
        _decorate_library_table(page)

    command_center._populate_build_table = populate_with_icons
    inspector._header = _header
    inspector._gear_card = _gear_card
    inspector._skills_tab = _skills_tab
    inspector._consumables_tab = _consumables_tab


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    _install_runtime_patches()

    from ui.themed_builds_page import BuildsPage as ThemedBuildsPage

    original_build_ui = ThemedBuildsPage._build_ui
    original_show_event = ThemedBuildsPage.showEvent

    def build_ui_with_phase14_icon_polish(self):
        original_build_ui(self)
        _move_new_build_to_header(self)
        _decorate_library_table(self)
        refresh_theme_icons(self)

    def show_event_with_phase14_icons(self, event):
        original_show_event(self, event)
        # Phase 14 is assembled through several compatibility layers. Reassert
        # semantic icons after the final visible widget tree exists so icons
        # added to assets/icons locally are not lost merely because an earlier
        # decorator constructed the label/button before the final dossier.
        _move_new_build_to_header(self)
        _decorate_library_table(self)
        refresh_theme_icons(self)

    ThemedBuildsPage._build_ui = build_ui_with_phase14_icon_polish
    ThemedBuildsPage.showEvent = show_event_with_phase14_icons
    _INSTALLED = True


__all__ = ["install"]
