from __future__ import annotations

"""Ensure the Team Schedule merge control lives in the visible Teams action row.

FoundryCard owns nested widget/layout hierarchies.  The Teams action row is a
QHBoxLayout inside the card body's QVBoxLayout, so looking only at ancestor
widget layouts can mistake the card body for the target and leave Merge Teams
as a full-width strip.  This layer finds the exact nested layout item that owns
Delete Selected Team, then relocates or creates the merge button beside it.
"""

from PySide6.QtWidgets import QLayout, QPushButton, QSizePolicy, QWidget

from ui.roster_team_merge_support import _open_merge_dialog


_INSTALLED = False


def _layout_location(layout: QLayout | None, target: QWidget) -> tuple[QLayout, int] | None:
    if layout is None:
        return None
    for index in range(layout.count()):
        item = layout.itemAt(index)
        widget = item.widget()
        nested = item.layout()
        if widget is target:
            return layout, index
        if nested is not None:
            found = _layout_location(nested, target)
            if found is not None:
                return found
        if widget is not None and widget is not target:
            found = _layout_location(widget.layout(), target)
            if found is not None:
                return found
    return None


def _button_location(page_widget: QWidget, button: QPushButton) -> tuple[QLayout, int] | None:
    return _layout_location(page_widget.layout(), button)


def _ensure_merge_button(page_widget: QWidget, roster_page) -> None:
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

    target = _button_location(page_widget, delete_button)
    if target is None:
        return
    target_layout, delete_index = target

    merge_buttons = [
        button
        for button in page_widget.findChildren(QPushButton)
        if button.text().strip().casefold().startswith("merge teams")
    ]
    merge_button = merge_buttons[0] if merge_buttons else None

    # Remove any accidental duplicate controls left by an earlier composition
    # layer.  Keep the first button so its signal wiring remains intact.
    for duplicate in merge_buttons[1:]:
        location = _button_location(page_widget, duplicate)
        if location is not None:
            location[0].removeWidget(duplicate)
        duplicate.deleteLater()

    if merge_button is None:
        merge_button = QPushButton("Merge Teams…")
        merge_button.clicked.connect(lambda _checked=False: _open_merge_dialog(roster_page))

    merge_button.setToolTip(
        "Merge one named team into another while preserving people, characters, builds, and canonical build ownership."
    )
    merge_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    merge_button.setMinimumWidth(120)
    merge_button.setMaximumWidth(160)

    current = _button_location(page_widget, merge_button)
    if current is not None and current[0] is not target_layout:
        current[0].removeWidget(merge_button)
        current = None

    if current is None or current[0] is not target_layout:
        # Re-read the delete index because removing a misplaced button may have
        # changed indices in the target layout.
        target = _button_location(page_widget, delete_button)
        if target is None:
            return
        target_layout, delete_index = target
        target_layout.insertWidget(delete_index, merge_button)
    else:
        merge_index = current[1]
        target = _button_location(page_widget, delete_button)
        if target is not None and merge_index != max(0, target[1] - 1):
            target_layout.removeWidget(merge_button)
            target_layout.insertWidget(target[1], merge_button)

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
