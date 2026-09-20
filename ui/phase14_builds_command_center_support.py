from __future__ import annotations

"""Phase 14 command-center shell for the Builds workspace.

Presentation only. Existing build/template/edit behavior remains canonical. The command
center owns the library browser geometry and selection bridge without introducing a
second build store or rewriting user build data.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_ORIGINAL_LOAD = None
_ORIGINAL_REFRESH_ROSTER = None
_ORIGINAL_REFRESH_DETAIL = None

_LIBRARY_TABS = ("All", "Mine", "Team", "Comp Builds", "Templates", "Favorites", "Archive")


def _role_for_row(page, build) -> str:
    explicit = str(getattr(build, "Role", "") or "").strip()
    if explicit:
        return explicit
    try:
        role, _status = page._role_for(build)
        return str(role or "").strip()
    except Exception:
        return ""


def _content_for_build(build) -> str:
    variants = tuple(getattr(build, "ContextVariants", ()) or ())
    boss_loadouts = tuple(getattr(build, "BossLoadouts", ()) or ())
    if variants or boss_loadouts:
        return "Trials"
    name = str(getattr(build, "BuildName", "") or "").casefold()
    if "parse" in name or "dummy" in name:
        return "Parsing"
    return "General"


def _template_mode(page) -> bool:
    tabs = getattr(page, "phase14_library_tabs", None)
    return bool(tabs is not None and tabs.currentIndex() >= 0 and tabs.tabText(tabs.currentIndex()) == "Templates")


def _active_library_mode(page) -> str:
    tabs = getattr(page, "phase14_library_tabs", None)
    if tabs is None or tabs.currentIndex() < 0:
        return "All"
    return str(tabs.tabText(tabs.currentIndex()) or "All")


def _build_matches_filters(page, build) -> bool:
    search = str(page.phase14_build_search.text() or "").strip().casefold()
    if search:
        haystack = " ".join(
            str(value or "")
            for value in (
                getattr(build, "Name", ""),
                getattr(build, "BuildName", ""),
                getattr(build, "Gamertag", ""),
                getattr(build, "EsoClass", ""),
                getattr(build, "Role", ""),
                _content_for_build(build),
            )
        ).casefold()
        if search not in haystack:
            return False

    selected_class = str(page.phase14_class_filter.currentText() or "All")
    if selected_class != "All" and selected_class.casefold() != str(getattr(build, "EsoClass", "") or "").strip().casefold():
        return False

    selected_role = str(page.phase14_role_filter.currentText() or "All")
    if selected_role != "All" and selected_role.casefold() != _role_for_row(page, build).casefold():
        return False

    selected_content = str(page.phase14_content_filter.currentText() or "All")
    if selected_content != "All" and selected_content.casefold() != _content_for_build(build).casefold():
        return False

    source_filter = getattr(page, "phase14_source_filter", None)
    selected_source = str(source_filter.currentData() or "") if source_filter is not None else ""
    build_kind = str(getattr(build, "BuildKind", "saved") or "saved").strip().casefold()
    if selected_source == "comp" and build_kind != "comp":
        return False
    if selected_source == "saved" and build_kind == "comp":
        return False
    return True


def _set_filters_from_library(page) -> None:
    classes = sorted(
        {str(getattr(build, "EsoClass", "") or "").strip() for build in page.roster.Members if str(getattr(build, "EsoClass", "") or "").strip()},
        key=str.casefold,
    )
    roles = sorted({_role_for_row(page, build) for build in page.roster.Members if _role_for_row(page, build)}, key=str.casefold)
    contents = sorted({_content_for_build(build) for build in page.roster.Members}, key=str.casefold)
    for combo, values in (
        (page.phase14_class_filter, classes),
        (page.phase14_role_filter, roles),
        (page.phase14_content_filter, contents),
    ):
        current = str(combo.currentText() or "All")
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("All")
        combo.addItems(values)
        if combo.findText(current) >= 0:
            combo.setCurrentText(current)
        combo.blockSignals(False)


def _populate_build_table(page) -> None:
    table = page.phase14_build_table
    table.blockSignals(True)
    table.setRowCount(0)
    page.phase14_table_source_rows = []

    if _template_mode(page):
        for source_row in range(page.roster_list.count()):
            item = page.roster_list.item(source_row)
            row = table.rowCount()
            table.insertRow(row)
            for column, value in enumerate(("☆", item.text(), "Template", "—", "Template", "Reusable")):
                table.setItem(row, column, QTableWidgetItem(value))
            page.phase14_table_source_rows.append(source_row)
        table.blockSignals(False)
        if table.rowCount():
            table.selectRow(0)
        return

    mode = _active_library_mode(page)

    for build_index, build in enumerate(page.roster.Members):
        build_kind = str(getattr(build, "BuildKind", "saved") or "saved").strip().casefold()
        if mode == "Comp Builds" and build_kind != "comp":
            continue
        if mode not in {"All", "Mine", "Comp Builds"}:
            continue
        if not _build_matches_filters(page, build):
            continue
        row = table.rowCount()
        table.insertRow(row)
        character = str(getattr(build, "Name", "") or "").strip() or "Unnamed Character"
        build_name = str(getattr(build, "BuildName", "") or "").strip() or "Default"
        values = (
            "☆",
            f"{character} — {build_name}",
            character,
            str(getattr(build, "EsoClass", "") or "").strip() or "—",
            _role_for_row(page, build) or "—",
            _content_for_build(build),
        )
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(value))
        page.phase14_table_source_rows.append(build_index)

    table.blockSignals(False)
    if table.rowCount():
        desired = page.phase14_table_source_rows.index(page.selected_index) if page.selected_index in page.phase14_table_source_rows else 0
        table.selectRow(desired)


def _select_command_center_row(page, row: int, _column: int = 0) -> None:
    if row < 0 or row >= len(getattr(page, "phase14_table_source_rows", ())):
        return
    source_row = page.phase14_table_source_rows[row]
    if _template_mode(page):
        page.roster_list.setCurrentRow(source_row)
        return
    if source_row < 0 or source_row >= len(page.roster.Members):
        return
    page.selected_index = source_row
    page._refresh_detail()


def _switch_library_mode(page, index: int) -> None:
    mode = str(page.phase14_library_tabs.tabText(index) or "All")
    if mode == "Templates":
        if page.view_combo.findText("Templates") >= 0:
            page.view_combo.setCurrentText("Templates")
        else:
            page.status.warning("Template browsing is not installed in this app session.")
            return
    elif page.view_combo.findText("All Builds") >= 0:
        page.view_combo.setCurrentText("All Builds")
    _populate_build_table(page)


def _select_library_mode(page, mode: str) -> None:
    tabs = getattr(page, "phase14_library_tabs", None)
    if tabs is None:
        return
    wanted = str(mode or "All").strip() or "All"
    for index in range(tabs.count()):
        if tabs.tabText(index) != wanted:
            continue
        tabs.blockSignals(True)
        try:
            tabs.setCurrentIndex(index)
        finally:
            tabs.blockSignals(False)
        return


def _reset_library_filters(page, *, mode: str = "All") -> None:
    """Make an explicit navigation target visible regardless of stale library UI state."""
    _select_library_mode(page, mode)
    search = getattr(page, "phase14_build_search", None)
    if search is not None:
        search.blockSignals(True)
        try:
            search.clear()
        finally:
            search.blockSignals(False)
    for name in (
        "phase14_class_filter",
        "phase14_role_filter",
        "phase14_content_filter",
        "phase14_source_filter",
    ):
        combo = getattr(page, name, None)
        if combo is None:
            continue
        combo.blockSignals(True)
        try:
            if combo.count():
                combo.setCurrentIndex(0)
        finally:
            combo.blockSignals(False)

    view = getattr(page, "view_combo", None)
    if view is not None and view.findText("All Builds") >= 0:
        view.blockSignals(True)
        try:
            view.setCurrentText("All Builds")
        finally:
            view.blockSignals(False)


def _create_command_center(page) -> QWidget:
    host = QWidget()
    host.setObjectName("phase14BuildLibrary")
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(7)

    tabs_row = QHBoxLayout()
    tabs_row.setContentsMargins(0, 0, 0, 0)
    tabs_row.setSpacing(7)

    page.phase14_library_tabs = QTabBar()
    page.phase14_library_tabs.setDocumentMode(False)
    page.phase14_library_tabs.setExpanding(True)
    page.phase14_library_tabs.setUsesScrollButtons(True)
    page.phase14_library_tabs.setElideMode(Qt.TextElideMode.ElideNone)
    page.phase14_library_tabs.setMinimumWidth(650)
    for name in _LIBRARY_TABS:
        page.phase14_library_tabs.addTab(name)
    tabs_row.addWidget(page.phase14_library_tabs, 1)
    layout.addLayout(tabs_row)

    top = QHBoxLayout()
    top.setContentsMargins(0, 0, 0, 0)
    top.setSpacing(7)

    page.phase14_build_search = QLineEdit()
    page.phase14_build_search.setPlaceholderText("Search builds…")
    page.phase14_build_search.setClearButtonEnabled(True)
    page.phase14_build_search.setMinimumWidth(210)
    top.addWidget(page.phase14_build_search, 1)

    page.phase14_create_build_button = FoundryButton("+ Create New Build", role=ButtonRole.PRIMARY)
    page.phase14_create_build_button.setMinimumWidth(150)
    top.addWidget(page.phase14_create_build_button)
    layout.addLayout(top)

    filters = QHBoxLayout()
    filters.setContentsMargins(0, 0, 0, 0)
    filters.setSpacing(6)
    filters.addStretch(1)
    page.phase14_class_filter = QComboBox()
    page.phase14_role_filter = QComboBox()
    page.phase14_content_filter = QComboBox()
    page.phase14_source_filter = QComboBox()
    page.phase14_source_filter.addItem("All Sources", "")
    page.phase14_source_filter.addItem("Comp Builds", "comp")
    page.phase14_source_filter.addItem("Saved Builds", "saved")
    for label, combo in (
        ("Class", page.phase14_class_filter),
        ("Role", page.phase14_role_filter),
        ("Content", page.phase14_content_filter),
        ("Source", page.phase14_source_filter),
    ):
        filters.addWidget(QLabel(label))
        if combo is not page.phase14_source_filter:
            combo.addItem("All")
        combo.setMinimumWidth(115)
        filters.addWidget(combo)
    layout.addLayout(filters)

    table_card = FoundryCard("Build Library", "▤")
    page.phase14_build_table = QTableWidget(0, 6)
    page.phase14_build_table.setHorizontalHeaderLabels(["★", "Name", "Character", "Class", "Role", "Content"])
    page.phase14_build_table.verticalHeader().setVisible(False)
    page.phase14_build_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    page.phase14_build_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    page.phase14_build_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    page.phase14_build_table.horizontalHeader().setStretchLastSection(True)
    page.phase14_build_table.setMinimumWidth(650)
    page.phase14_build_table.setColumnWidth(0, 42)
    page.phase14_build_table.setColumnWidth(1, 225)
    page.phase14_build_table.setColumnWidth(2, 150)
    page.phase14_build_table.setColumnWidth(3, 130)
    page.phase14_build_table.setColumnWidth(4, 120)
    table_card.addWidget(page.phase14_build_table)
    layout.addWidget(table_card, 1)

    page.phase14_library_tabs.currentChanged.connect(lambda i: _switch_library_mode(page, i))
    page.phase14_build_search.textChanged.connect(lambda _text: _populate_build_table(page))
    page.phase14_class_filter.currentTextChanged.connect(lambda _text: _populate_build_table(page))
    page.phase14_role_filter.currentTextChanged.connect(lambda _text: _populate_build_table(page))
    page.phase14_content_filter.currentTextChanged.connect(lambda _text: _populate_build_table(page))
    page.phase14_source_filter.currentIndexChanged.connect(lambda _index: _populate_build_table(page))
    page.phase14_build_table.cellClicked.connect(lambda row, col: _select_command_center_row(page, row, col))
    return host


def _wire_new_build_button(page) -> None:
    existing = getattr(page, "create_character_button", None)
    if existing is not None:
        page.phase14_create_build_button.clicked.connect(existing.click)
        page.phase14_create_build_button.setEnabled(existing.isEnabled())
    else:
        page.phase14_create_build_button.setEnabled(False)

    action_host = getattr(page, "new_build_action_host", None)
    if action_host is not None:
        action_host.hide()


def _quiet_overview_action_bar(page) -> None:
    """The library/inspector view should not look like an open editor."""
    for name in (
        "save_build_button",
        "cancel_build_button",
        "delete_build_button",
        "copy_build_button",
        "template_build_button",
        "save_button",
        "export_button",
    ):
        button = getattr(page, name, None)
        if button is not None:
            button.hide()


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI, _ORIGINAL_LOAD, _ORIGINAL_REFRESH_ROSTER, _ORIGINAL_REFRESH_DETAIL
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    _ORIGINAL_BUILD_UI = BuildsPage._build_ui
    _ORIGINAL_LOAD = BuildsPage._load
    _ORIGINAL_REFRESH_ROSTER = BuildsPage._refresh_roster
    _ORIGINAL_REFRESH_DETAIL = BuildsPage._refresh_detail
    original_show_player_builds = BuildsPage.show_player_builds

    def build_ui_phase14(self):
        _ORIGINAL_BUILD_UI(self)
        self.header.subtitle.setText("Create. Refine. Compare. Save what works.")

        command_center = _create_command_center(self)
        old_roster_card = self.splitter.widget(0)
        replaced = self.splitter.replaceWidget(0, command_center)
        if replaced is not None:
            replaced.hide()
            replaced.setParent(self)
        elif old_roster_card is not None:
            old_roster_card.hide()

        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([860, 650])

        self.roster_list.hide()
        self.trial_combo.parentWidget().hide()
        self.view_combo.parentWidget().hide()
        _wire_new_build_button(self)
        _quiet_overview_action_bar(self)

    def load_phase14(self):
        _ORIGINAL_LOAD(self)
        _set_filters_from_library(self)
        _populate_build_table(self)

    def refresh_roster_phase14(self, *_args):
        result = _ORIGINAL_REFRESH_ROSTER(self, *_args)
        if hasattr(self, "phase14_build_table"):
            _set_filters_from_library(self)
            _populate_build_table(self)
        return result

    def refresh_detail_phase14(self, *_args):
        result = _ORIGINAL_REFRESH_DETAIL(self, *_args)
        if hasattr(self, "phase14_build_table") and not _template_mode(self):
            if self.selected_index in getattr(self, "phase14_table_source_rows", ()):
                row = self.phase14_table_source_rows.index(self.selected_index)
                self.phase14_build_table.blockSignals(True)
                self.phase14_build_table.selectRow(row)
                self.phase14_build_table.blockSignals(False)
        return result

    def show_build_by_id(self, build_id: str) -> bool:
        wanted = str(build_id or "").strip().casefold()
        if not wanted:
            return False
        self._player_build_filter = ""
        self.roster = self.build_service.load()
        match = next(
            (
                index
                for index, build in enumerate(self.roster.Members)
                if str(getattr(build, "BuildId", "") or "").strip().casefold() == wanted
            ),
            None,
        )
        if match is None:
            _set_filters_from_library(self)
            _populate_build_table(self)
            self.status.warning(f"Canonical build {build_id!r} is not available in Builds.")
            return False

        self.selected_index = int(match)
        comp_kind = str(
            getattr(self.roster.Members[match], "BuildKind", "saved") or "saved"
        ).strip().casefold()
        wanted_tab = "Comp Builds" if comp_kind == "comp" else "All"
        _reset_library_filters(self, mode=wanted_tab)
        _set_filters_from_library(self)
        _populate_build_table(self)
        self._refresh_detail()
        self.status.info(
            f"Opened build: {self.roster.Members[match].BuildName or build_id}."
        )
        return True

    BuildsPage._build_ui = build_ui_phase14
    BuildsPage._load = load_phase14
    BuildsPage._refresh_roster = refresh_roster_phase14
    BuildsPage._refresh_detail = refresh_detail_phase14

    def show_player_builds_phase14(self, gamertag: str) -> None:
        _reset_library_filters(self, mode="All")
        original_show_player_builds(self, gamertag)
        if hasattr(self, "phase14_build_table"):
            _set_filters_from_library(self)
            _populate_build_table(self)

    BuildsPage.show_player_builds = show_player_builds_phase14
    BuildsPage.show_build_by_id = show_build_by_id
    _INSTALLED = True


__all__ = ["install"]
