from __future__ import annotations

from PySide6.QtWidgets import QLineEdit

from ui.components.team_progress_panels import coverage_from_declared_text


_INSTALLED = False
_ORIGINAL_COMP_INIT = None
_ORIGINAL_COMP_REFRESH_COVERAGE = None


def _matrix_text(table, row: int, column: int) -> str:
    widget = table.cellWidget(row, column)
    if isinstance(widget, QLineEdit):
        return widget.text().strip()
    item = table.item(row, column)
    return item.text().strip() if item is not None else ""


def _comp_declared_rows(page) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    table = page.matrix_table
    for row in range(table.rowCount()):
        slot_name = _matrix_text(table, row, 0) or f"Slot {row + 1}"
        text = " ".join(
            value
            for column in (4, 5, 6, 7)
            if (value := _matrix_text(table, row, column))
        )
        rows.append((slot_name, text))
    return tuple(rows)


def _refresh_comp_progress(page) -> None:
    if not hasattr(page, "progress_coverage_grid"):
        return
    page.progress_coverage_grid.set_items(
        coverage_from_declared_text(_comp_declared_rows(page))
    )


def _comp_refresh_coverage_with_progress(self, *args) -> None:
    assert _ORIGINAL_COMP_REFRESH_COVERAGE is not None
    _ORIGINAL_COMP_REFRESH_COVERAGE(self, *args)
    _refresh_comp_progress(self)


def _comp_init_with_progress(self, parent=None) -> None:
    """Comp Builder owns its coverage-card placement; this layer only refreshes it."""
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _refresh_comp_progress(self)


def install() -> None:
    global _INSTALLED
    global _ORIGINAL_COMP_INIT, _ORIGINAL_COMP_REFRESH_COVERAGE
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    _ORIGINAL_COMP_REFRESH_COVERAGE = CompBuilderPage._refresh_coverage
    CompBuilderPage.__init__ = _comp_init_with_progress
    CompBuilderPage._refresh_coverage = _comp_refresh_coverage_with_progress

    # Optimization deliberately stays free of the extra progress furniture. Its
    # job is to operate on the selected team, while Comp Builder owns the planning
    # coverage scoreboard and composition-detail surfaces.
    _INSTALLED = True
