from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_RENDER_SLOTS = None
_ORIGINAL_REFRESH_CANDIDATES = None
_ORIGINAL_REFRESH_COVERAGE = None

# Keep the original matrix schema intact for every existing service/wrapper.
# Columns 3-7 remain the authoritative hidden storage for alternatives,
# responsibilities, providers and mechanics. Columns 8-10 are presentation only.
SUMMARY_CANDIDATE_COLUMN = 8
SUMMARY_CONSTRAINT_COLUMN = 9
SUMMARY_JOB_COLUMN = 10


def _card(page, title: str) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == title:
            return card
    return None


def _selected_row(page) -> int:
    row = page.matrix_table.currentRow()
    if row >= 0:
        return row
    return 0 if page.matrix_table.rowCount() else -1


def _slot_name(page, row: int) -> str:
    return page._cell_text(row, 0) or f"Slot {row + 1}"


def _summary_candidate(page, row: int) -> str:
    slot_name = _slot_name(page, row)
    candidate = getattr(page, "_comp_applied_candidates", {}).get(slot_name)
    if candidate is None:
        return "Open"
    source = "Saved" if candidate.source_kind == "saved_build" else "Reference"
    return f"{candidate.name} · {source}"


def _summary_constraints(page, row: int) -> str:
    bits: list[str] = []
    selected_class = page._selected_class(row).strip()
    if selected_class and selected_class.casefold() != "any class":
        bits.append(selected_class)
    gear = getattr(page, "_comp_required_gear_sets_by_slot", {}).get(_slot_name(page, row), ())
    if gear:
        bits.extend(gear)
    return " · ".join(bits) if bits else "Flexible"


def _summary_jobs(page, row: int) -> str:
    providers = page._split_values(page._cell_text(row, 6))
    mechanics = page._split_values(page._cell_text(row, 7))
    values = (*providers, *mechanics)
    if not values:
        return "None declared"
    shown = list(values[:3])
    if len(values) > 3:
        shown.append(f"+{len(values) - 3}")
    return " · ".join(shown)


def _set_summary_item(page, row: int, column: int, value: str) -> None:
    item = page.matrix_table.item(row, column)
    if item is None:
        item = QTableWidgetItem()
        page.matrix_table.setItem(row, column, item)
    item.setText(value)
    item.setToolTip(value)


def _refresh_overview_rows(page) -> None:
    if page.matrix_table.columnCount() <= SUMMARY_JOB_COLUMN:
        return
    for row in range(page.matrix_table.rowCount()):
        _set_summary_item(page, row, SUMMARY_CANDIDATE_COLUMN, _summary_candidate(page, row))
        _set_summary_item(page, row, SUMMARY_CONSTRAINT_COLUMN, _summary_constraints(page, row))
        _set_summary_item(page, row, SUMMARY_JOB_COLUMN, _summary_jobs(page, row))


def _hidden_editor(page, row: int, column: int) -> QLineEdit | None:
    widget = page.matrix_table.cellWidget(row, column)
    return widget if isinstance(widget, QLineEdit) else None


def _copy_hidden_value_to_detail(page, row: int, column: int, editor: QLineEdit) -> None:
    source = _hidden_editor(page, row, column)
    editor.blockSignals(True)
    editor.setText(source.text() if source is not None else page._cell_text(row, column))
    editor.blockSignals(False)


def _copy_detail_value_to_hidden(page, column: int, text: str) -> None:
    row = _selected_row(page)
    if row < 0:
        return
    target = _hidden_editor(page, row, column)
    if target is not None and target.text() != text:
        target.setText(text)
    _refresh_overview_rows(page)


def _sync_selected_chair(page) -> None:
    row = _selected_row(page)
    if row < 0:
        page.comp_chair_title_label.setText("SELECT A RAID CHAIR")
        return

    slot = _slot_name(page, row)
    role = page._cell_text(row, 1) or "Unresolved role"
    selected_class = page._selected_class(row) or "Any class"
    page.comp_chair_title_label.setText(f"{slot}  •  {role}  •  {selected_class}")

    _copy_hidden_value_to_detail(page, row, 4, page.comp_chair_required_input)
    _copy_hidden_value_to_detail(page, row, 5, page.comp_chair_optional_input)
    _copy_hidden_value_to_detail(page, row, 6, page.comp_chair_providers_input)
    _copy_hidden_value_to_detail(page, row, 7, page.comp_chair_mechanics_input)

    # Build Around already owns the authoritative per-chair gear constraint. Move
    # its existing widgets into this editor rather than inventing duplicate state.
    if hasattr(page, "comp_required_gear_sets_input"):
        slot_gear = getattr(page, "_comp_required_gear_sets_by_slot", {}).get(slot, ())
        page.comp_required_gear_sets_input.blockSignals(True)
        page.comp_required_gear_sets_input.setText(", ".join(slot_gear))
        page.comp_required_gear_sets_input.blockSignals(False)

    _refresh_overview_rows(page)


def _detail_field(label_text: str, placeholder: str) -> tuple[QWidget, QLineEdit]:
    host = QWidget()
    host.setProperty("compMakerDetailField", True)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(3)
    label = QLabel(label_text)
    label.setProperty("sidebarHeading", True)
    editor = QLineEdit()
    editor.setPlaceholderText(placeholder)
    layout.addWidget(label)
    layout.addWidget(editor)
    return host, editor


def _install_selected_chair_editor(page) -> None:
    details = _card(page, "Composition Details & Summary")
    if details is None:
        return

    details.title_label.setText("Selected Chair Setup & Evidence")
    details.setProperty("compMakerChairCard", True)

    # The trial/goal summary already exists in the header and composition overview.
    # Hiding these duplicates gives the selected-chair controls useful vertical room.
    for name in ("trial_label", "summary_label", "coverage_label"):
        widget = getattr(page, name, None)
        if widget is not None:
            widget.hide()

    scroll = next(iter(details.findChildren(QScrollArea)), None)
    body = scroll.widget() if scroll is not None else None
    layout = body.layout() if body is not None else None
    if layout is None:
        return

    page.comp_chair_title_label = QLabel("SELECT A RAID CHAIR")
    page.comp_chair_title_label.setWordWrap(True)
    page.comp_chair_title_label.setProperty("compMakerChairTitle", True)

    editor_host = QWidget()
    editor_host.setProperty("compMakerChairEditor", True)
    grid = QGridLayout(editor_host)
    grid.setContentsMargins(0, 0, 0, 6)
    grid.setHorizontalSpacing(10)
    grid.setVerticalSpacing(7)

    required_host, page.comp_chair_required_input = _detail_field(
        "REQUIRED RESPONSIBILITIES", "Required duties for this chair"
    )
    optional_host, page.comp_chair_optional_input = _detail_field(
        "OPTIONAL / FLEX", "Optional or flex duties"
    )
    provider_host, page.comp_chair_providers_input = _detail_field(
        "PROVIDER OBLIGATIONS", "Buff, debuff, or utility obligations"
    )
    mechanic_host, page.comp_chair_mechanics_input = _detail_field(
        "MECHANIC JOBS", "Portal, kite, tombs, add duty, etc."
    )

    grid.addWidget(required_host, 0, 0)
    grid.addWidget(optional_host, 0, 1)
    grid.addWidget(provider_host, 1, 0)
    grid.addWidget(mechanic_host, 1, 1)
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)

    layout.insertWidget(0, page.comp_chair_title_label)
    layout.insertWidget(1, editor_host)

    # Re-home the already-tested hard gear constraint immediately after duties.
    gear_label = getattr(page, "comp_required_gear_sets_label", None)
    gear_input = getattr(page, "comp_required_gear_sets_input", None)
    if gear_label is not None and gear_input is not None:
        gear_label.setProperty("compMakerConstraintLabel", True)
        gear_input.setProperty("compMakerConstraintInput", True)
        layout.removeWidget(gear_label)
        layout.removeWidget(gear_input)
        layout.insertWidget(2, gear_label)
        layout.insertWidget(3, gear_input)

    page.comp_chair_required_input.textChanged.connect(
        lambda text: _copy_detail_value_to_hidden(page, 4, text)
    )
    page.comp_chair_optional_input.textChanged.connect(
        lambda text: _copy_detail_value_to_hidden(page, 5, text)
    )
    page.comp_chair_providers_input.textChanged.connect(
        lambda text: _copy_detail_value_to_hidden(page, 6, text)
    )
    page.comp_chair_mechanics_input.textChanged.connect(
        lambda text: _copy_detail_value_to_hidden(page, 7, text)
    )

    page.matrix_table.currentCellChanged.connect(lambda *_: _sync_selected_chair(page))
    page.goal_combo.currentTextChanged.connect(lambda *_: _sync_selected_chair(page))


def _configure_overview_table(page) -> None:
    table = page.matrix_table
    table.setColumnCount(11)
    table.setHorizontalHeaderLabels(
        (
            "SLOT",
            "ROLE",
            "CLASS",
            "ALTERNATIVES",
            "REQUIRED",
            "OPTIONAL / FLEX",
            "PROVIDERS",
            "MECHANIC JOBS",
            "APPLIED CANDIDATE",
            "BUILD AROUND",
            "PROVIDERS / JOBS",
        )
    )

    for column in range(3, 8):
        table.setColumnHidden(column, True)

    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setWordWrap(False)
    table.setProperty("compMakerOverview", True)

    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    for column in (0, 1, 2):
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
    for column in (SUMMARY_CANDIDATE_COLUMN, SUMMARY_CONSTRAINT_COLUMN, SUMMARY_JOB_COLUMN):
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)

    # Twelve trial chairs fit without making the whole page absurdly tall. The page
    # itself still scrolls vertically for the editor/evidence below.
    table.setMinimumHeight(430)
    table.setMaximumHeight(430)


def _render_slots_with_workspace(self, slots) -> None:
    assert _ORIGINAL_RENDER_SLOTS is not None
    _ORIGINAL_RENDER_SLOTS(self, slots)
    if self.matrix_table.columnCount() < 11:
        _configure_overview_table(self)
    _refresh_overview_rows(self)
    if hasattr(self, "comp_chair_title_label"):
        _sync_selected_chair(self)


def _install_workspace(page) -> None:
    _configure_overview_table(page)
    _install_selected_chair_editor(page)
    _refresh_overview_rows(page)
    if page.matrix_table.rowCount() and page.matrix_table.currentRow() < 0:
        page.matrix_table.selectRow(0)
    _sync_selected_chair(page)


def install() -> None:
    global _INSTALLED, _ORIGINAL_RENDER_SLOTS, _ORIGINAL_REFRESH_CANDIDATES, _ORIGINAL_REFRESH_COVERAGE
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage
    from ui import comp_builder_build_candidate_support as candidate_support

    _ORIGINAL_RENDER_SLOTS = CompBuilderPage._render_slots
    CompBuilderPage._render_slots = _render_slots_with_workspace

    _ORIGINAL_REFRESH_CANDIDATES = candidate_support._refresh_candidates

    def refresh_candidates_with_overview(page) -> None:
        assert _ORIGINAL_REFRESH_CANDIDATES is not None
        _ORIGINAL_REFRESH_CANDIDATES(page)
        _refresh_overview_rows(page)
        if hasattr(page, "comp_chair_title_label"):
            _sync_selected_chair(page)

    candidate_support._refresh_candidates = refresh_candidates_with_overview

    _ORIGINAL_REFRESH_COVERAGE = CompBuilderPage._refresh_coverage

    def refresh_coverage_with_overview(self, *args) -> None:
        assert _ORIGINAL_REFRESH_COVERAGE is not None
        _ORIGINAL_REFRESH_COVERAGE(self, *args)
        _refresh_overview_rows(self)

    CompBuilderPage._refresh_coverage = refresh_coverage_with_overview

    original_init = CompBuilderPage.__init__

    def init_with_vertical_workspace(self, parent=None):
        original_init(self, parent)
        _install_workspace(self)

    CompBuilderPage.__init__ = init_with_vertical_workspace
    _INSTALLED = True
