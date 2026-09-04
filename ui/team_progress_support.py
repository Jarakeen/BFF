from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from ui.components.foundry_card import FoundryCard
from ui.components.team_progress_panels import (
    coverage_from_builds,
    coverage_from_declared_text,
    make_coverage_card,
)


_INSTALLED = False
_ORIGINAL_COMP_INIT = None
_ORIGINAL_COMP_REFRESH_COVERAGE = None
_ORIGINAL_OPT_INIT = None
_ORIGINAL_OPT_UPDATE_ANALYSIS = None


def _comp_declared_rows(page) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    table = page.matrix_table
    for row in range(table.rowCount()):
        slot_item = table.item(row, 0)
        responsibilities_item = table.item(row, 4)
        providers_item = table.item(row, 5)
        slot_name = slot_item.text().strip() if slot_item is not None else f"Slot {row + 1}"
        text = " ".join(
            value
            for value in (
                responsibilities_item.text().strip() if responsibilities_item is not None else "",
                providers_item.text().strip() if providers_item is not None else "",
            )
            if value
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


def _rename_comp_actions_card(page) -> None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Roster Handoff":
            card.set_title("Actions")
            return


def _comp_init_with_progress(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)

    _rename_comp_actions_card(self)
    card, grid = make_coverage_card()
    self.progress_coverage_card = card
    self.progress_coverage_grid = grid
    self.workspace_layout.insertWidget(0, card)
    _refresh_comp_progress(self)


def _selected_optimization_builds(page) -> tuple:
    table = page.team_table
    if hasattr(page, "team_tabs") and page.team_tabs.currentIndex() == 1:
        table = page.team_b_table

    builds: list = []
    used: set[int] = set()
    for row in range(table.rowCount()):
        selector = table.cellWidget(row, 1)
        selection = selector.currentData() if selector is not None else None
        if not isinstance(selection, int):
            continue
        if selection in used or not (0 <= selection < len(page.roster.Members)):
            continue
        used.add(selection)
        builds.append(page.roster.Members[selection])
    return tuple(builds)


def _optimization_details_text(page) -> str:
    target = len(page._role_slots())
    table = (
        page.team_b_table
        if hasattr(page, "team_tabs") and page.team_tabs.currentIndex() == 1
        else page.team_table
    )
    saved, recruits = page._team_counts(table)
    goal = page.goal_combo.currentText().strip() or "Custom Goal"
    return (
        "2 Tanks • 2 Healers • 8 Damage Dealers\n\n"
        f"PRIMARY OBJECTIVE\n• {goal}\n\n"
        f"TEAM STATE\n• {saved} saved player(s)\n"
        f"• {recruits} open recruit chair(s)\n"
        f"• {saved + recruits}/{target} planned slot(s)\n\n"
        "Coverage is resolved from the selected saved builds, not inferred from class alone."
    )


def _refresh_optimization_progress(page) -> None:
    if not hasattr(page, "progress_coverage_grid"):
        return
    builds = _selected_optimization_builds(page)
    items = coverage_from_builds(builds)
    page.progress_coverage_grid.set_items(items)
    covered = sum(1 for item in items if item.covered)
    page.progress_details_label.setText(_optimization_details_text(page))
    page.progress_summary_label.setText(
        f"{covered}/{len(items)} displayed group effects currently evidenced by the selected builds."
    )


def _send_optimization_team(page) -> None:
    window = page.window()
    handler = getattr(window, "_send_optimized_team_to_roster", None)
    if callable(handler):
        handler()
    else:
        page.status.warning("Roster handoff is not available from this window.")


def _build_optimization_progress_row(page) -> QWidget:
    wrapper = QWidget()
    row = QHBoxLayout(wrapper)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)

    details = FoundryCard("Composition Details", "✦")
    page.progress_details_label = QLabel()
    page.progress_details_label.setWordWrap(True)
    page.progress_summary_label = QLabel()
    page.progress_summary_label.setWordWrap(True)
    details.addWidget(page.progress_details_label)
    details.addWidget(page.progress_summary_label)
    row.addWidget(details, 2)

    actions = FoundryCard("Actions", "➜")
    note = QLabel(
        "Improve the existing team here. Keep composition locks on for build-only gains, or deliberately unlock broader changes."
    )
    note.setWordWrap(True)
    actions.addWidget(note)
    send_button = QPushButton("Send Team to Roster")
    send_button.setProperty("primary", True)
    send_button.clicked.connect(lambda *_: _send_optimization_team(page))
    actions.addWidget(send_button)
    row.addWidget(actions, 2)

    return wrapper


def _optimization_init_with_progress(self, parent=None) -> None:
    assert _ORIGINAL_OPT_INIT is not None
    _ORIGINAL_OPT_INIT(self, parent)

    coverage_card, coverage_grid = make_coverage_card()
    self.progress_coverage_card = coverage_card
    self.progress_coverage_grid = coverage_grid
    self.workspace_layout.insertWidget(0, coverage_card)

    self.progress_action_row = _build_optimization_progress_row(self)
    self.workspace_layout.addWidget(self.progress_action_row)
    _refresh_optimization_progress(self)


def _optimization_update_with_progress(self, *args) -> None:
    assert _ORIGINAL_OPT_UPDATE_ANALYSIS is not None
    _ORIGINAL_OPT_UPDATE_ANALYSIS(self, *args)
    _refresh_optimization_progress(self)


def install() -> None:
    global _INSTALLED
    global _ORIGINAL_COMP_INIT, _ORIGINAL_COMP_REFRESH_COVERAGE
    global _ORIGINAL_OPT_INIT, _ORIGINAL_OPT_UPDATE_ANALYSIS
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage
    from ui.optimization_page import OptimizationPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    _ORIGINAL_COMP_REFRESH_COVERAGE = CompBuilderPage._refresh_coverage
    CompBuilderPage.__init__ = _comp_init_with_progress
    CompBuilderPage._refresh_coverage = _comp_refresh_coverage_with_progress

    _ORIGINAL_OPT_INIT = OptimizationPage.__init__
    _ORIGINAL_OPT_UPDATE_ANALYSIS = OptimizationPage._update_team_analysis
    OptimizationPage.__init__ = _optimization_init_with_progress
    OptimizationPage._update_team_analysis = _optimization_update_with_progress

    _INSTALLED = True
