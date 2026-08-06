# ==================================================
# Black Feather Foundry
#
# File:
# widgets/timeline_panel.py
#
# Purpose:
# Displays the chronological timeline of the
# current Expedition.
#
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
)

from models.event_model import Event


class TimelinePanel(QWidget):
    """
    Displays the Expedition timeline.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Controls
        #

        self.timeline = QListWidget()

        #
        # Layout
        #

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.timeline)

    # --------------------------------------------------
    # Events
    # --------------------------------------------------

    def add_event(self, event: Event):
        """
        Add a single event to the timeline.
        """

        timestamp = event.timestamp.strftime("%H:%M:%S")

        item = QListWidgetItem(
            f"{timestamp}   {event.event}"
        )

        self.timeline.addItem(item)

        self.timeline.scrollToBottom()

    def set_events(
        self,
        events: list[Event],
    ):
        """
        Replace the timeline with a collection
        of events.
        """

        self.timeline.clear()

        for event in events:
            self.add_event(event)

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def clear(self):
        """
        Clear the timeline.
        """

        self.timeline.clear()