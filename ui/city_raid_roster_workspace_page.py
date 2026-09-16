from __future__ import annotations

"""Urban Wilderness Roster entry point and final composition polish.

The underlying themed roster page owns canonical data and actions.  This wrapper only
adjusts presentation for the approved one-screen Roster mockup: six equal summary cards,
real semantic badges, restrained artwork, and a readable table-first layout.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QLabel, QHeaderView, QSizePolicy

from ui.themed_raid_roster_workspace_page import ThemedRaidRosterWorkspacePage
from ui.ux_icons import icon


_BADGES = {
    "players": "users",
    "characters": "character",
    "teams": "users",
    "availability": "stopwatch",
    "recruitment": "person",
    "archive": "archive",
}


class CityRaidRosterWorkspacePage(ThemedRaidRosterWorkspacePage):
    """Compatibility route name for the single Urban Wilderness Roster dashboard."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._polish_urban_wilderness_roster()

    def _polish_urban_wilderness_roster(self) -> None:
        """Keep the mockup readable at normal desktop widths without horizontal sprawl."""
        self.header.subtitle.setText("Same people. Different rooftops. Better runs.")

        for key, card in self.metric_cards.items():
            card.setMinimumWidth(0)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            card.setMinimumHeight(132)
            card.setMaximumHeight(148)

            badge = next(
                (
                    label
                    for label in card.findChildren(QLabel)
                    if bool(label.property("rosterMetricIcon"))
                ),
                None,
            )
            if badge is not None:
                badge.clear()
                badge.setFixedSize(QSize(54, 54))
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setPixmap(icon(_BADGES.get(key, "compass")).pixmap(46, 46))
                badge.setProperty("rosterMetricBadge", True)

        # The artwork is flavor, not the page's landlord.  Keep it cropped and restrained.
        if hasattr(self, "quote_art"):
            self.quote_art.setMinimumWidth(0)
            self.quote_art.setMaximumWidth(390)
            self.quote_art.setMinimumHeight(165)
            self.quote_art.setMaximumHeight(220)
            self.quote_art.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if hasattr(self, "team_art"):
            self.team_art.setMinimumWidth(0)
            self.team_art.setMaximumWidth(460)
            self.team_art.setMinimumHeight(120)
            self.team_art.setMaximumHeight(160)
            self.team_art.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # The roster itself is the primary information surface.  Let useful columns share
        # the width instead of allowing pixmap size hints to squeeze the table into a sliver.
        if hasattr(self, "table"):
            header = self.table.horizontalHeader()
            header.setStretchLastSection(True)
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for column, width in enumerate((190, 165, 110, 120, 120, 130, 105)):
                self.table.setColumnWidth(column, width)
            self.table.setMinimumWidth(720)

        # Use one of the uploaded field-note lines as the quiet page refrain.
        if hasattr(self, "team_snapshot_label"):
            self.team_snapshot_label.setToolTip(
                "Good people make hard things possible. Different rooftops. Same horizon."
            )


__all__ = ["CityRaidRosterWorkspacePage"]
