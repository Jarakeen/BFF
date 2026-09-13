from __future__ import annotations

"""Ensure the Team Schedule merge control is inserted into the visible Teams card.

FoundryCard owns its own internal widget/layout hierarchy, so searching only the
outer Team Schedule page layout cannot locate the row that contains the Delete
Selected Team button.  This layer composes after the merge workflow and inserts
the existing merge action beside Delete using the button's real ancestor layout.
"""

from PySide6.QtWidgets import QLayout, QPushButton, QWidget

from ui.roster_team_merge_support import _open_merge_dialog


_INSTALLED = False


def _ancestor_layout_containing(widget: QWidget) -> tuple[QLayout, int] | None:
    current: QWidget | None = widget.parentWidget()
    while current is not None:
        layout = current.layout()
        if layout is not None:
            index = layout.indexOf(widget)
            if index >= 0:
                return layout, index
        widget = current
        current = current.parentWidget()
    return None


def _ensure_merge_button(page_widget: QWidget, roster_page) -> None:
    existing = next(
        (
            button
            for button in page_widget.findChildren(QPushButton)
            if button.text().strip().casefold().startswith("merge teams")
        ),
        None,
    )
    if existing is not None:
        roster_page.merge_teams_button = existing
        return

    delete_button = next(
        (
            button
            for button in page_widget.findChildren(QPushButton)
            if button.text().strip().casefold() == "delete selected team"
        ),
        None,
    )
    if delete_button is None:
        return

    location = _ancestor_layout_containing(delete_button)
    if location is None:
        return
    layout, delete_index = location

    merge_button = QPushButton("Merge Teams…")
    merge_button.setToolTip(
        "Merge one named team into another while preserving people, characters, builds, and canonical build ownership."
    )
    merge_button.clicked.connect(lambda _checked=False: _open_merge_dialog(roster_page))
    layout.insertWidget(delete_index, merge_button)
    roster_page.merge_teams_button = merge_button


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original = RosterPage._build_team_schedule_tab

    def build_team_schedule_tab_with_visible_merge(self):
        page = original(self)
        _ensure_merge_button(page, self)
        return page

    RosterPage._build_team_schedule_tab = build_team_schedule_tab_with_visible_merge
    _INSTALLED = True
