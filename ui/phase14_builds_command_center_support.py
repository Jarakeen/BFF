from __future__ import annotations

"""Phase 14 command-center shell for the Builds workspace.

This is deliberately a presentation layer over the existing BuildsPage and its
already-installed template/copy/edit support. It does not introduce a second build
store, rewrite builds.json, or infer ownership/favorite/archive metadata that the
current persistence model does not yet own.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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


_LIBRARY_TABS = ("All", "Mine", "Team", "Templates", "Favorites", "Archive")


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
    return getattr(page, "phase14_library_tabs", None) is not None and (
        page.phase14_library_tabs.tabText(page.phase14_library_tabs.currentIndex()) == "Templates"
    )


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
    if selected_class != "All" and selected_class.casefold() != str(
        getattr(build, "EsoClass", "") or ""
    ).strip().casefold():
        return False

    selected_role = str(page.phase14_role_filter.currentText() or "All")
    if selected_role != "All" and selected_role.casefold() != _role_for_row(page, build).casefold():
        return False

    selected_content = str(page.phase14_content_filter.currentText() or "All")
    if selected_content != "All" and selected_content.casefold() != _content_for_build(build).casefold():
        return False
    return True


def _set_filters_from_library(page) -> None:
    classes = sorted(
        {
            str(getattr(build, "EsoClass", "") or "").strip()
            for build in page.roster.Members
            if str(getattr(build, "EsoClass", "") or "").strip()
        },
        key=str.casefold,
    )
    roles = sorted(
        {_role_for_row(page, build) for build in page.roster.Members if _role_for_row(page, build)},
        key=str.casefold,
    )
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
        # The existing build-reuse feature remains authoritative for template loading,
        # selection, and applying a template. Mirror its rows instead of reading a
        # second template source here.
        for source_row in range(page.roster_list.count()):
            item = page.roster_list.item(source_row)
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem("☆"))
            table.setItem(row, 1, QTableWidgetItem(item.text()))
            table.setItem(row, 2, QTableWidgetItem("Template"))
            table.setItem(row, 3, QTableWidgetItem("—"))
            table.setItem(row, 4, QTableWidgetItem("Template"))
            table.setItem(row, 5, QTableWidgetItem("Reusable"))
            page.phase14_table_source_rows.append(source_row)
        table.blockSignals(False)
        if table.rowCount():
            table.selectRow(0)
        return

    mode = _active_library_mode(page)
    if mode not in {"All", "Mine"}:
        table.blockSignals(False)
        return

    for build_index, build in enumerate(page.roster.Members):
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
        desired = 0
        if page.selected_index in page.phase14_table_source_rows:
            desired = page.phase14_table_source_rows.index(page.selected_index)
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
    else:
        if page.view_combo.findText("All Builds") >= 0:
            page.view_combo.setCurrentText("All Builds")

    unsupported = {
        "Team": "Team/shared ownership metadata is the next Phase 14 persistence slice.",
        "Favorites": "Favorites metadata is the next Phase 14 persistence slice.",
        "Archive": "Archive metadata is the next Phase 14 persistence slice.",
    }
    page.phase14_library_notice.setText(unsupported.get(mode, ""))
    page.phase14_library_notice.setVisible(mode in unsupported)
    _populate_build_table(page)


def _create_command_center(page) -> QWidget:
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    controls = QWidget()
    controls_layout = QHBoxLayout(controls)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(8)

    page.phase14_library_tabs = QTabBar()
    page.phase14_library_tabs.setDocumentMode(True)
    page.phase14_library_tabs.setExpanding(False)
    for name in _LIBRARY_TABS:
        page.phase14_library_tabs.addTab(name)
    controls_layout.addWidget(page.phase14_library_tabs, 1)

    page.phase14_build_search = QLineEdit()
    page.phase14_build_search.setPlaceholderText("Search builds…")
    page.phase14_build_search.setClearButtonEnabled(True)
    page.phase14_build_search.setMinimumWidth(220)
    controls_layout.addWidget(page.phase14_build_search)

    page.phase14_create_build_button = FoundryButton("+ Create New Build", role=ButtonRole.PRIMARY)
    page.phase14_create_build_button.setToolTip(
        "Create New Build remains routed through the existing character/build creation workflow."
    )
    # Existing BuildsPage has no canonical blank-build creation action. Keep this
    # honest instead of silently inventing an incomplete record.
    page.phase14_create_build_button.setEnabled(False)
    controls_layout.addWidget(page.phase14_create_build_button)
    layout.addWidget(controls)

    filters = QWidget()
    filter_layout = QHBoxLayout(filters)
    filter_layout.setContentsMargins(0, 0, 0, 0)
    filter_layout.addStretch()
    page.phase14_class_filter = QComboBox()
    page.phase14_role_filter = QComboBox()
    page.phase14_content_filter = QComboBox()
    for label, combo in (
        ("Class", page.phase14_class_filter),
        ("Role", page.phase14_role_filter),
        ("Content", page.phase14_content_filter),
    ):
        filter_layout.addWidget(QLabel(label))
        combo.addItem("All")
        combo.setMinimumWidth(120)
        filter_layout.addWidget(combo)
    layout.addWidget(filters)

    page.phase14_library_notice = QLabel("")
    page.phase14_library_notice.setWordWrap(True)
    page.phase14_library_notice.setProperty("muted", True)
    page.phase14_library_notice.hide()
    layout.addWidget(page.phase14_library_notice)

    table_card = FoundryCard("Build Library", "▤")
    page.phase14_build_table = QTableWidget(0, 6)
    page.phase14_build_table.setHorizontalHeaderLabels(
        ["★", "Name", "Character", "Class", "Role", "Content"]
    )
    page.phase14_build_table.verticalHeader().setVisible(False)
    page.phase14_build_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    page.phase14_build_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    page.phase14_build_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    page.phase14_build_table.horizontalHeader().setStretchLastSection(True)
    page.phase14_build_table.setMinimumWidth(520)
    table_card.addWidget(page.phase14_build_table)
    layout.addWidget(table_card, 1)

    page.phase14_library_tabs.currentChanged.connect(lambda i: _switch_library_mode(page, i))
    page.phase14_build_search.textChanged.connect(lambda _text: _populate_build_table(page))
    page.phase14_class_filter.currentTextChanged.connect(lambda _text: _populate_build_table(page))
    page.phase14_role_filter.currentTextChanged.connect(lambda _text: _populate_build_table(page))
    page.phase14_content_filter.currentTextChanged.connect(lambda _text: _populate_build_table(page))
    page.phase14_build_table.cellClicked.connect(lambda row, col: _select_command_center_row(page, row, col))
    return host


def install() -> None:
    """Install the Phase 14 Builds command-center shell exactly once."""
    global _INSTALLED, _ORIGINAL_BUILD_UI, _ORIGINAL_LOAD, _ORIGINAL_REFRESH_ROSTER, _ORIGINAL_REFRESH_DETAIL
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    _ORIGINAL_BUILD_UI = BuildsPage._build_ui
    _ORIGINAL_LOAD = BuildsPage._load
    _ORIGINAL_REFRESH_ROSTER = BuildsPage._refresh_roster
    _ORIGINAL_REFRESH_DETAIL = BuildsPage._refresh_detail

    def build_ui_phase14(self):
        _ORIGINAL_BUILD_UI(self)
        self.header.subtitle.setText("Create. Refine. Compare. Save what works.")

        # Keep the decorated roster/list machinery alive as the compatibility bridge,
        # but remove its visual ownership of the page. Selection and template actions
        # still flow through the existing methods.
        self.roster_list.hide()
        roster_card = self.roster_list.parentWidget()
        if roster_card is not None:
            roster_card.hide()

        command_center = _create_command_center(self)
        self.splitter.insertWidget(0, command_center)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)

        # Legacy header selectors remain data/compatibility controls. They no longer
        # need to consume visual space in the command-center presentation.
        self.trial_combo.parentWidget().hide()
        self.view_combo.parentWidget().hide()

        # The mockup's quiet action hierarchy keeps Save visible while secondary
        # operations remain in the existing inspector/edit surfaces.
        self.export_button.hide()

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
            # Keep the command-center selection aligned after edits/reloads without
            # causing another detail refresh signal loop.
            if self.selected_index in getattr(self, "phase14_table_source_rows", ()):
                row = self.phase14_table_source_rows.index(self.selected_index)
                self.phase14_build_table.blockSignals(True)
                self.phase14_build_table.selectRow(row)
                self.phase14_build_table.blockSignals(False)
        return result

    BuildsPage._build_ui = build_ui_phase14
    BuildsPage._load = load_phase14
    BuildsPage._refresh_roster = refresh_roster_phase14
    BuildsPage._refresh_detail = refresh_detail_phase14
    _INSTALLED = True


__all__ = ["install"]
