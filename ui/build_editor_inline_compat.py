from __future__ import annotations

"""Persistent, non-native Build workspace tabs.

The Build Editor, Character Progression, and Scribed Skills editors all live
inside the existing Builds page. No top-level editor window is created, which
avoids the bright native-window flash seen on Windows and keeps navigation
predictable for photosensitive users.
"""

from collections import Counter

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from services.character_progression_service import CharacterProgressionService
from ui.components.foundry_button import ButtonRole, FoundryButton


DARK_SURFACE = "#0C171B"
_INSTALLED = False


def _force_dark_surface(widget: QWidget) -> None:
    widget.setAutoFillBackground(True)
    palette = widget.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(DARK_SURFACE))
    palette.setColor(QPalette.ColorRole.Base, QColor(DARK_SURFACE))
    widget.setPalette(palette)
    widget.setStyleSheet(f"background-color: {DARK_SURFACE};")


def _build_display_names(builds) -> list[str]:
    raw = [
        (getattr(build, "BuildName", "") or getattr(build, "Name", "") or getattr(build, "Gamertag", "") or f"Build {index + 1}").strip()
        for index, build in enumerate(builds)
    ]
    counts = Counter(name.casefold() for name in raw)
    labels: list[str] = []
    for index, (name, build) in enumerate(zip(raw, builds)):
        if counts[name.casefold()] > 1:
            character = (getattr(build, "Name", "") or getattr(build, "Gamertag", "") or str(index + 1)).strip()
            labels.append(f"{name} — {character}")
        else:
            labels.append(name)
    return labels


def _set_combo_index(combo: QComboBox, index: int) -> None:
    combo.blockSignals(True)
    match = combo.findData(index)
    combo.setCurrentIndex(match if match >= 0 else -1)
    combo.blockSignals(False)


def _clear_host(host: QWidget) -> None:
    layout = host.layout()
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from ui.phase5_build_ui_support import CharacterProgressionDialog, _character_id_for_page

    original_build_ui = BuildsPage._build_ui
    original_load = BuildsPage._load
    original_select_member = BuildsPage._select_member
    original_refresh_detail = BuildsPage._refresh_detail

    def build_ui_with_permanent_tabs(self) -> None:
        original_build_ui(self)

        # Editing is now a first-class tab, not an action button.
        self.edit_button.hide()

        self.workspace_layout.removeWidget(self.splitter)

        tabs = QTabWidget(self.workspace_widget)
        tabs.setObjectName("buildWorkspaceTabs")
        tabs.setDocumentMode(True)
        tabs.setMovable(False)
        tabs.setTabsClosable(False)
        _force_dark_surface(tabs)
        _force_dark_surface(tabs.tabBar())

        roster_tab = QWidget(tabs)
        _force_dark_surface(roster_tab)
        roster_layout = QVBoxLayout(roster_tab)
        roster_layout.setContentsMargins(0, 0, 0, 0)
        roster_layout.addWidget(self.splitter, 1)
        tabs.addTab(roster_tab, "Roster")

        edit_tab = QWidget(tabs)
        _force_dark_surface(edit_tab)
        edit_layout = QVBoxLayout(edit_tab)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(8)
        edit_selector_row = QHBoxLayout()
        edit_selector_row.addWidget(QLabel("Character Name"))
        self.edit_build_selector = QComboBox(edit_tab)
        self.edit_build_selector.setMinimumWidth(320)
        edit_selector_row.addWidget(self.edit_build_selector)
        edit_selector_row.addStretch()
        edit_layout.addLayout(edit_selector_row)
        self.edit_build_scroll = QScrollArea(edit_tab)
        self.edit_build_scroll.setWidgetResizable(True)
        self.edit_build_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.edit_build_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.edit_build_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        _force_dark_surface(self.edit_build_scroll)
        _force_dark_surface(self.edit_build_scroll.viewport())
        self.edit_build_placeholder = QWidget()
        _force_dark_surface(self.edit_build_placeholder)
        placeholder_layout = QVBoxLayout(self.edit_build_placeholder)
        placeholder_layout.addWidget(QLabel("Select a saved build from Roster or the Character Name list."))
        placeholder_layout.addStretch()
        self.edit_build_scroll.setWidget(self.edit_build_placeholder)
        edit_layout.addWidget(self.edit_build_scroll, 1)
        tabs.addTab(edit_tab, "Edit")

        progression_tab = QWidget(tabs)
        _force_dark_surface(progression_tab)
        progression_layout = QVBoxLayout(progression_tab)
        progression_layout.setContentsMargins(0, 0, 0, 0)
        progression_layout.setSpacing(8)
        progression_selector_row = QHBoxLayout()
        progression_selector_row.addWidget(QLabel("Character Name"))
        self.progression_build_selector = QComboBox(progression_tab)
        self.progression_build_selector.setMinimumWidth(320)
        progression_selector_row.addWidget(self.progression_build_selector)
        progression_selector_row.addStretch()
        progression_layout.addLayout(progression_selector_row)
        self.progression_host = QWidget(progression_tab)
        _force_dark_surface(self.progression_host)
        self.progression_host.setLayout(QVBoxLayout())
        self.progression_host.layout().setContentsMargins(0, 0, 0, 0)
        progression_layout.addWidget(self.progression_host, 1)
        self.save_progression_button = FoundryButton(
            "Save Character Progression", role=ButtonRole.SUCCESS, compact=True
        )
        progression_actions = QHBoxLayout()
        progression_actions.addStretch()
        progression_actions.addWidget(self.save_progression_button)
        progression_layout.addLayout(progression_actions)
        tabs.addTab(progression_tab, "Character Progression")

        scribed_tab = QWidget(tabs)
        _force_dark_surface(scribed_tab)
        scribed_layout = QVBoxLayout(scribed_tab)
        scribed_layout.setContentsMargins(0, 0, 0, 0)
        scribed_layout.setSpacing(8)
        scribed_selector_row = QHBoxLayout()
        scribed_selector_row.addWidget(QLabel("Character Name"))
        self.scribed_build_selector = QComboBox(scribed_tab)
        self.scribed_build_selector.setMinimumWidth(320)
        scribed_selector_row.addWidget(self.scribed_build_selector)
        scribed_selector_row.addStretch()
        scribed_layout.addLayout(scribed_selector_row)
        note = QLabel(
            "Choose the scribed skills this character has access to. Selected skills become eligible for this build's skill bars."
        )
        note.setWordWrap(True)
        scribed_layout.addWidget(note)
        self.scribed_skill_choices = QListWidget(scribed_tab)
        scribed_layout.addWidget(self.scribed_skill_choices, 1)
        self.save_scribed_button = FoundryButton(
            "Save Scribed Access", role=ButtonRole.SUCCESS, compact=True
        )
        scribed_actions = QHBoxLayout()
        scribed_actions.addStretch()
        scribed_actions.addWidget(self.save_scribed_button)
        scribed_layout.addLayout(scribed_actions)
        tabs.addTab(scribed_tab, "Scribed Skills")

        self.workspace_layout.addWidget(tabs, 1)
        self.build_tabs = tabs
        self._build_editor = None
        self._build_editor_index = None
        self._progression_panel = None
        self._progression_index = None
        self._progression_character_id = None
        self._scribed_index = None
        self._syncing_build_selectors = False

        tabs.currentChanged.connect(lambda index: self._build_workspace_tab_changed(index))
        self.edit_build_selector.currentIndexChanged.connect(
            lambda *_: self._build_selector_changed(self.edit_build_selector, 1)
        )
        self.progression_build_selector.currentIndexChanged.connect(
            lambda *_: self._build_selector_changed(self.progression_build_selector, 2)
        )
        self.scribed_build_selector.currentIndexChanged.connect(
            lambda *_: self._build_selector_changed(self.scribed_build_selector, 3)
        )
        self.save_progression_button.clicked.connect(lambda *_: self._save_progression_tab())
        self.save_scribed_button.clicked.connect(lambda *_: self._save_scribed_tab())

    def refresh_build_selectors(self) -> None:
        labels = _build_display_names(self.roster.Members)
        self._syncing_build_selectors = True
        try:
            for combo in (
                self.edit_build_selector,
                self.progression_build_selector,
                self.scribed_build_selector,
            ):
                combo.blockSignals(True)
                combo.clear()
                for index, label in enumerate(labels):
                    combo.addItem(label, index)
                if self.roster.Members:
                    _set_combo_index(combo, min(max(self.selected_index, 0), len(self.roster.Members) - 1))
                combo.blockSignals(False)
        finally:
            self._syncing_build_selectors = False

    def load_with_build_tabs(self) -> None:
        original_load(self)
        refresh_build_selectors(self)

    def select_member_with_tabs(self, row: int) -> None:
        original_select_member(self, row)
        if row < 0 or row >= len(self.roster.Members) or not hasattr(self, "edit_build_selector"):
            return
        self._syncing_build_selectors = True
        try:
            for combo in (
                self.edit_build_selector,
                self.progression_build_selector,
                self.scribed_build_selector,
            ):
                _set_combo_index(combo, self.selected_index)
        finally:
            self._syncing_build_selectors = False

    def refresh_detail_without_legacy_edit_buttons(self, *_args) -> None:
        original_refresh_detail(self, *_args)
        if not hasattr(self, "detail"):
            return
        for button in self.detail.findChildren(QPushButton):
            if button.text().strip() in {"Character Progression", "Choose Scribed Skills"}:
                button.hide()

    def build_selector_changed(self, combo: QComboBox, tab_index: int) -> None:
        if self._syncing_build_selectors:
            return
        index = combo.currentData()
        if index is None:
            return
        try:
            index = int(index)
        except (TypeError, ValueError):
            return
        if index < 0 or index >= len(self.roster.Members):
            return
        self.selected_index = index
        self.roster_list.setCurrentRow(index)
        if self.build_tabs.currentIndex() == tab_index:
            self._build_workspace_tab_changed(tab_index)

    def workspace_tab_changed(self, tab_index: int) -> None:
        if not self.roster.Members:
            return
        index = min(max(self.selected_index, 0), len(self.roster.Members) - 1)
        if tab_index == 1:
            self._load_edit_tab(index)
        elif tab_index == 2:
            self._load_progression_tab(index)
        elif tab_index == 3:
            self._load_scribed_tab(index)

    def load_edit_tab(self, index: int) -> None:
        if index < 0 or index >= len(self.roster.Members):
            return
        if self._build_editor is not None and self._build_editor_index == index:
            return

        build = self.roster.Members[index]
        editor = self._editor(build)
        _force_dark_surface(editor)
        editor.load(build)

        # The visible Character Name control is the saved-build selector above.
        # Keep the editor's actual character-name field as hidden model state so
        # saving still preserves the canonical character name.
        if hasattr(editor, "name"):
            editor.name.hide()
        for label in editor.findChildren(QLabel):
            if label.text().strip() == "Character Name":
                label.hide()

        editor.saveRequested.connect(lambda: self._save_edit_tab())
        editor.cancelRequested.connect(lambda: self._cancel_edit_tab())

        self.edit_build_scroll.takeWidget()
        self.edit_build_scroll.setWidget(editor)
        self._build_editor = editor
        self._build_editor_index = index
        _set_combo_index(self.edit_build_selector, index)

    def save_edit_tab(self) -> None:
        editor = self._build_editor
        index = self._build_editor_index
        if editor is None or index is None or index < 0 or index >= len(self.roster.Members):
            return
        original = self.roster.Members[index]
        updated = editor.model
        updated.ScribedSkills = list(getattr(original, "ScribedSkills", []))
        if hasattr(original, "CharacterId") and hasattr(updated, "CharacterId"):
            updated.CharacterId = getattr(original, "CharacterId", "")
        self.roster.Members[index] = updated
        self.selected_index = index
        self._save()
        self._refresh_roster()
        refresh_build_selectors(self)
        _set_combo_index(self.edit_build_selector, index)

    def cancel_edit_tab(self) -> None:
        index = self._build_editor_index
        if index is None or index < 0 or index >= len(self.roster.Members):
            return
        self._build_editor.load(self.roster.Members[index])

    def load_progression_tab(self, index: int) -> None:
        if index < 0 or index >= len(self.roster.Members):
            return
        if self._progression_panel is not None and self._progression_index == index:
            return

        build = self.roster.Members[index]
        character_id = _character_id_for_page(self, build)
        _clear_host(self.progression_host)
        self._progression_panel = None
        self._progression_index = index
        self._progression_character_id = character_id
        _set_combo_index(self.progression_build_selector, index)

        if not character_id:
            self.progression_host.layout().addWidget(
                QLabel("Character progression could not resolve a canonical character identity.")
            )
            return
        catalog_service = self.build_service.canonical.catalog_service
        character = catalog_service.get_character(character_id)
        if character is None:
            self.progression_host.layout().addWidget(QLabel("Canonical character record was not found."))
            return

        panel = CharacterProgressionDialog(reference=self.reference, character=character, parent=self.progression_host)
        panel.setWindowFlags(Qt.WindowType.Widget)
        panel.setWindowTitle("")
        for button in panel.findChildren(QPushButton):
            if button.text().strip() in {"Cancel", "Save Character Progression"}:
                button.hide()
        _force_dark_surface(panel)
        self.progression_host.layout().addWidget(panel, 1)
        panel.show()
        self._progression_panel = panel

    def save_progression_tab(self) -> None:
        panel = self._progression_panel
        character_id = self._progression_character_id
        if panel is None or not character_id:
            return
        service = CharacterProgressionService(self.build_service.canonical.catalog_service)
        saved = service.save(
            character_id=character_id,
            owned_skill_lines=panel.owned_skill_lines,
            passive_ranks=panel.passive_ranks,
            passive_cp_points=panel.passive_cp_points,
        )
        if saved is None:
            self.status.error("Character progression could not be saved.")
            return
        self.status.success("Character progression saved. All builds for this character share it.")
        self._refresh_detail()

    def load_scribed_tab(self, index: int) -> None:
        if index < 0 or index >= len(self.roster.Members):
            return
        if self._scribed_index == index and self.scribed_skill_choices.count():
            return
        build = self.roster.Members[index]
        selected = {
            str(name).strip().casefold()
            for name in getattr(build, "ScribedSkills", [])
            if str(name).strip()
        }
        self.scribed_skill_choices.clear()
        for name in self._scribed_skill_names():
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if name.casefold() in selected else Qt.CheckState.Unchecked
            )
            self.scribed_skill_choices.addItem(item)
        self._scribed_index = index
        _set_combo_index(self.scribed_build_selector, index)

    def save_scribed_tab(self) -> None:
        index = self._scribed_index
        if index is None or index < 0 or index >= len(self.roster.Members):
            return
        self.roster.Members[index].ScribedSkills = [
            self.scribed_skill_choices.item(item_index).text().strip()
            for item_index in range(self.scribed_skill_choices.count())
            if self.scribed_skill_choices.item(item_index).checkState() == Qt.CheckState.Checked
        ]
        self.selected_index = index
        self._save()
        self.status.success("Scribed skill access saved for this build.")
        if self._build_editor_index == index:
            old_editor = self._build_editor
            self._build_editor = None
            self._build_editor_index = None
            if old_editor is not None:
                old_editor.deleteLater()
            self._load_edit_tab(index)

    BuildsPage._build_ui = build_ui_with_permanent_tabs
    BuildsPage._load = load_with_build_tabs
    BuildsPage._select_member = select_member_with_tabs
    BuildsPage._refresh_detail = refresh_detail_without_legacy_edit_buttons
    BuildsPage._refresh_build_tab_selectors = refresh_build_selectors
    BuildsPage._build_selector_changed = build_selector_changed
    BuildsPage._build_workspace_tab_changed = workspace_tab_changed
    BuildsPage._load_edit_tab = load_edit_tab
    BuildsPage._save_edit_tab = save_edit_tab
    BuildsPage._cancel_edit_tab = cancel_edit_tab
    BuildsPage._load_progression_tab = load_progression_tab
    BuildsPage._save_progression_tab = save_progression_tab
    BuildsPage._load_scribed_tab = load_scribed_tab
    BuildsPage._save_scribed_tab = save_scribed_tab

    # Keep compatibility names used by older tests/extensions, but route them to
    # the permanent Edit tab rather than creating a transient editor surface.
    BuildsPage._edit_selected = lambda self: self.build_tabs.setCurrentIndex(1)
    BuildsPage._finish_inline_build_edit = lambda self, save=False: self._save_edit_tab() if save else self._cancel_edit_tab()
    BuildsPage._finish_build_tab_edit = BuildsPage._finish_inline_build_edit

    _INSTALLED = True
