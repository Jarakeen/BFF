from __future__ import annotations

"""Keep the Team Schedule merge action in the same row as Create/Delete.

The merge workflow originally patched the completed Team Schedule page after the
FoundryCard had already nested its action row inside ``body_layout``. Searching
only from the outer page layout could therefore find the button widget but not
its actual row layout, and a fallback parent-layout insertion rendered the merge
action as a full-width strip. This final composition pass relocates the existing
button into the concrete row that owns Delete Selected Team.
"""

from PySide6.QtWidgets import QPushButton


_INSTALLED = False


def _find_layout_containing(layout, target):
    if layout is None:
        return None
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is target:
            return layout
        nested = item.layout()
        if nested is not None:
            found = _find_layout_containing(nested, target)
            if found is not None:
                return found
    return None


def _ancestor_foundry_card(widget):
    current = widget.parentWidget() if widget is not None else None
    while current is not None:
        if bool(current.property("foundryCard")) and hasattr(current, "body_layout"):
            return current
        current = current.parentWidget()
    return None


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original_build_team_schedule_tab = RosterPage._build_team_schedule_tab

    def build_team_schedule_tab_with_merge_row_fix(self):
        page = original_build_team_schedule_tab(self)
        buttons = page.findChildren(QPushButton)
        merge_button = next(
            (
                button
                for button in buttons
                if button.text().strip().casefold().startswith("merge teams")
            ),
            None,
        )
        delete_button = next(
            (
                button
                for button in buttons
                if button.text().strip().casefold() == "delete selected team"
            ),
            None,
        )
        if merge_button is None or delete_button is None:
            return page

        card = _ancestor_foundry_card(delete_button)
        if card is None:
            return page

        destination_row = _find_layout_containing(card.body_layout, delete_button)
        if destination_row is None:
            return page

        current_layout = _find_layout_containing(card.body_layout, merge_button)
        if current_layout is not None:
            current_layout.removeWidget(merge_button)

        destination_row.insertWidget(
            max(0, destination_row.indexOf(delete_button)),
            merge_button,
        )
        self.merge_teams_button = merge_button
        return page

    RosterPage._build_team_schedule_tab = build_team_schedule_tab_with_merge_row_fix
    _INSTALLED = True
