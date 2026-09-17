from __future__ import annotations

"""Phase 14 read-first Build inspector.

The Builds library stays a browser. The right pane is a compact dossier with the
approved Overview/Gear/Skills/CP/Consumables/Scribing/Notes tabs. Heavy canonical
editors remain in the existing workspace tabs and are opened only when requested.
"""

from collections import Counter

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard

_INSTALLED = False


def _selected_build(page):
    index = int(getattr(page, "selected_index", -1))
    if index < 0 or index >= len(page.roster.Members):
        return None
    return page.roster.Members[index]


def _text(value, fallback: str = "—") -> str:
    cleaned = str(value or "").strip()
    return cleaned or fallback


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        child = item.widget()
        nested = item.layout()
        if child is not None:
            child.deleteLater()
        elif nested is not None:
            _clear(nested)


def _sync_outer_chrome(page, index: int) -> None:
    tabs = getattr(page, "build_tabs", None)
    if tabs is None:
        return
    library_mode = int(index) == 0
    tabs.tabBar().setVisible(not library_mode)

    action_host = getattr(page, "edit_button", None)
    action_host = action_host.parentWidget() if action_host is not None else None
    if action_host is not None:
        action_host.setVisible(int(index) == 1)

    if int(index) == 1:
        for name in ("cancel_build_button", "save_build_button", "delete_build_button"):
            button = getattr(page, name, None)
            if button is not None:
                button.show()


def _open_workspace_tab(page, index: int) -> None:
    tabs = getattr(page, "build_tabs", None)
    if tabs is None or index < 0 or index >= tabs.count():
        return
    tabs.setCurrentIndex(index)

    selector_name = {
        1: "edit_build_selector",
        2: "progression_build_selector",
        3: "scribed_build_selector",
    }.get(index, "")
    selector = getattr(page, selector_name, None) if selector_name else None
    if selector is not None:
        match = selector.findData(page.selected_index)
        if match >= 0:
            selector.setCurrentIndex(match)


def _action_button(page, label: str = "Edit", *, workspace_tab: int = 1) -> FoundryButton:
    button = FoundryButton(label, role=ButtonRole.SECONDARY, compact=True)
    button.clicked.connect(lambda: _open_workspace_tab(page, workspace_tab))
    return button


def _header(page, build) -> QWidget:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(10, 7, 10, 7)
    text = QVBoxLayout()
    title = QLabel(f"{_text(build.Name, 'Unnamed Character')} — {_text(build.BuildName, 'Default')}")
    title.setProperty("pageTitle", True)
    subtitle = QLabel("  •  ".join(value for value in (_text(build.EsoClass), _text(build.Role), _text(build.Race)) if value != "—"))
    subtitle.setProperty("pageSubtitle", True)
    text.addWidget(title)
    text.addWidget(subtitle)
    layout.addLayout(text, 1)

    ready = QLabel("Ready" if bool(getattr(build, "ReadyForRaid", False)) else "Not Ready")
    ready.setProperty("cardBadge", True)
    layout.addWidget(ready)
    layout.addWidget(_action_button(page))
    return host


def _row(label: str, value: str) -> QWidget:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 2, 0, 2)
    layout.addWidget(QLabel(label))
    layout.addStretch(1)
    value_label = QLabel(value)
    value_label.setWordWrap(True)
    layout.addWidget(value_label)
    return host


def _overview_tab(page, build) -> QWidget:
    tab = QWidget()
    layout = QGridLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    status = FoundryCard("Build Status", "◆")
    for label, value in page._status_rows(build):
        status.addWidget(_row(label, value))
    layout.addWidget(status, 0, 0)

    sets = FoundryCard("Set Bonuses", "◇")
    counts = Counter()
    for slot in page._all_gear(build):
        name = slot.Set.strip() if hasattr(slot, "Set") else str(slot.get("Set", "")).strip()
        if name:
            counts[name] += 1
    if counts:
        for name, count in counts.most_common():
            sets.addWidget(_row(name, f"{count}/5"))
    else:
        sets.addWidget(QLabel("No equipped sets recorded."))
    layout.addWidget(sets, 0, 1)

    identity = FoundryCard("Build Identity", "✦")
    identity.addWidget(_row("Character", _text(build.Name)))
    identity.addWidget(_row("Class", _text(build.EsoClass)))
    identity.addWidget(_row("Race", _text(build.Race)))
    identity.addWidget(_row("Role", _text(build.Role)))
    identity.addWidget(_row("Mundus", _text(build.Mundus)))
    layout.addWidget(identity, 1, 0, 1, 2)
    layout.setRowStretch(2, 1)
    return tab


def _gear_summary(slot) -> str:
    if hasattr(slot, "Set"):
        bits = [slot.Set, slot.Trait, slot.Enchant]
    else:
        bits = [slot.get("Set", ""), slot.get("Trait", ""), slot.get("Enchant", "")]
    return "  •  ".join(str(value).strip() for value in bits if str(value or "").strip()) or "Not configured"


def _gear_card(page, title: str, rows: list[tuple[str, object]]) -> FoundryCard:
    card = FoundryCard(title, "◆")
    for slot, value in rows:
        card.addWidget(_row(slot, _gear_summary(value)))
    actions = QHBoxLayout()
    actions.addStretch(1)
    actions.addWidget(_action_button(page))
    card.addLayout(actions)
    return card


def _gear_tab(page, build) -> QWidget:
    tab = QWidget()
    layout = QGridLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    armor = [(slot, value) for slot, value in build.Armor.items()]
    jewelry = [("Neck", build.Necklace), ("Ring 1", build.Ring1), ("Ring 2", build.Ring2)]
    front = [("Main Hand", build.FrontBarWeapon), ("Off Hand", build.FrontBarOffHand)]
    back = [("Main Hand", build.BackBarWeapon), ("Off Hand", build.BackBarOffHand)]

    layout.addWidget(_gear_card(page, "Armor", armor), 0, 0, 1, 2)
    layout.addWidget(_gear_card(page, "Jewelry", jewelry), 1, 0, 1, 2)
    layout.addWidget(_gear_card(page, "Front Bar", front), 2, 0)
    layout.addWidget(_gear_card(page, "Back Bar", back), 2, 1)
    layout.setRowStretch(3, 1)
    return tab


def _skills_tab(page, build) -> QWidget:
    tab = QWidget()
    layout = QHBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for title, values in (("Front Bar", build.FrontBarSkills), ("Back Bar", build.BackBarSkills)):
        card = FoundryCard(title, "◇")
        for index, skill in enumerate(values, start=1):
            card.addWidget(_row(f"Slot {index}", _text(skill)))
        card.addWidget(_action_button(page))
        layout.addWidget(card, 1)
    return tab


def _cp_tab(page, build) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    card = FoundryCard("Champion Points", "◆")
    entries = [entry for entry in build.ChampionPoints if str(entry.Name or "").strip()]
    if entries:
        for entry in entries:
            card.addWidget(_row(entry.Name, _text(entry.Points, "0")))
    else:
        card.addWidget(QLabel("No Champion Points recorded."))
    card.addWidget(_action_button(page))
    card.addWidget(_action_button(page, "Character Progression", workspace_tab=2))
    layout.addWidget(card)
    layout.addStretch(1)
    return tab


def _consumables_tab(page, build) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    card = FoundryCard("Consumables", "◆")
    card.addWidget(_row("Food", _text(build.Food, "Not selected")))
    card.addWidget(_row("Potion", _text(build.Potion, "Not selected")))
    card.addWidget(_action_button(page))
    layout.addWidget(card)
    layout.addStretch(1)
    return tab


def _scribing_tab(page, build) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    card = FoundryCard("Scribing", "◇")
    recipes = tuple(getattr(build, "ScribedSkillRecipes", ()) or ())
    names = [str(getattr(recipe, "ResultName", "") or "").strip() for recipe in recipes]
    names = [name for name in names if name] or [str(name).strip() for name in getattr(build, "ScribedSkills", ()) or () if str(name).strip()]
    if names:
        for name in names:
            card.addWidget(QLabel(name))
    else:
        card.addWidget(QLabel("No scribed skills recorded."))
    card.addWidget(_action_button(page, "Open Scribed Skills", workspace_tab=3))
    layout.addWidget(card)
    layout.addStretch(1)
    return tab


def _notes_tab(page, build) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    card = FoundryCard("Notes", "✎")
    note = QLabel(_text(build.Notes, "No build notes recorded."))
    note.setWordWrap(True)
    card.addWidget(note)
    card.addWidget(_action_button(page))
    layout.addWidget(card)
    layout.addStretch(1)
    return tab


def _proxy_click(page, name: str) -> None:
    button = getattr(page, name, None)
    if button is not None:
        button.click()


def _footer(page) -> QWidget:
    host = QWidget()
    row = QHBoxLayout(host)
    row.setContentsMargins(0, 4, 0, 0)

    copy = FoundryButton("Copy Build To…", role=ButtonRole.SECONDARY, compact=True)
    copy.clicked.connect(lambda: _proxy_click(page, "copy_build_button"))
    template = FoundryButton("Save as Template", role=ButtonRole.SECONDARY, compact=True)
    template.clicked.connect(lambda: _proxy_click(page, "template_build_button"))
    save = FoundryButton("Save", role=ButtonRole.SUCCESS)
    save.clicked.connect(page._save)

    row.addWidget(copy)
    row.addWidget(template)
    row.addStretch(1)
    row.addWidget(save)
    return host


def _render_inspector(page) -> None:
    from ui import phase14_build_profile_support as profile_support
    from ui import phase14_builds_command_center_support as command_center

    if command_center._template_mode(page):
        return
    build = _selected_build(page)
    if build is None:
        return

    _clear(page.detail_layout)
    page.detail_layout.setSpacing(8)
    page.detail_layout.addWidget(_header(page, build))
    page.detail_layout.addWidget(profile_support._baseline_card(page, build))

    tabs = QTabWidget()
    tabs.setDocumentMode(False)
    tabs.setMovable(False)
    tabs.addTab(_overview_tab(page, build), "Overview")
    tabs.addTab(_gear_tab(page, build), "Gear")
    tabs.addTab(_skills_tab(page, build), "Skills")
    tabs.addTab(_cp_tab(page, build), "CP")
    tabs.addTab(_consumables_tab(page, build), "Consumables")
    tabs.addTab(_scribing_tab(page, build), "Scribing")
    tabs.addTab(_notes_tab(page, build), "Notes")
    page.phase14_build_inspector_tabs = tabs
    page.detail_layout.addWidget(tabs, 1)
    page.detail_layout.addWidget(_footer(page))


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    original_build_ui = BuildsPage._build_ui
    original_refresh_detail = BuildsPage._refresh_detail

    def build_ui_phase14_inspector(self):
        original_build_ui(self)
        tabs = getattr(self, "build_tabs", None)
        if tabs is not None:
            tabs.currentChanged.connect(lambda index: _sync_outer_chrome(self, index))
            _sync_outer_chrome(self, tabs.currentIndex())

    def refresh_detail_phase14_inspector(self, *_args):
        result = original_refresh_detail(self, *_args)
        from ui import phase14_builds_command_center_support as command_center
        if not command_center._template_mode(self):
            _render_inspector(self)
        return result

    BuildsPage._build_ui = build_ui_phase14_inspector
    BuildsPage._refresh_detail = refresh_detail_phase14_inspector
    _INSTALLED = True


__all__ = ["install"]
