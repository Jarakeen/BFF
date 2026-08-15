# ==================================================
# Black Feather Foundry
#
# File:
# widgets/timeline_panel.py
#
# Purpose:
# Editable chronological timeline for the current
# Expedition.
#
# ==================================================

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QDateTimeEdit,
    QSpinBox,
    QTextEdit,
    QMenu,  
)

from models.event_model import Event


class EventEditDialog(QDialog):
    """Edit the details of a single Expedition event."""

    def __init__(self, event: Event, parent=None):
        super().__init__(parent)

        # Do not use ``self.event`` here: QDialog already has an event()
        # method, and shadowing it prevents Qt from opening the dialog.
        self.timeline_event = event

        self.setWindowTitle("Edit Event")
        self.resize(460, 300)

        layout = QFormLayout(self)

        # --------------------------------------------------
        # Timestamp
        # --------------------------------------------------

        self.timestamp = QDateTimeEdit()
        self.timestamp.setCalendarPopup(True)
        self.timestamp.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.timestamp.setDateTime(event.timestamp)

        layout.addRow("Timestamp", self.timestamp)

        # --------------------------------------------------
        # Event
        # --------------------------------------------------

        self.event_label = QTextEdit()
        self.event_label.setPlainText(event.event)
        self.event_label.setMaximumHeight(60)

        layout.addRow("Event", self.event_label)

        # --------------------------------------------------
        # Wipe percentage
        # --------------------------------------------------

        self.percent = None

        if event.event == "Wipe":
            self.percent = QSpinBox()
            self.percent.setRange(0, 100)
            self.percent.setSuffix("%")
            self.percent.setValue(
                int(event.payload.get("percent", 0))
            )

            layout.addRow("Reached", self.percent)

        # --------------------------------------------------
        # Notes
        # --------------------------------------------------

        self.notes = QTextEdit()
        self.notes.setPlainText(event.notes)

        layout.addRow("Notes", self.notes)

        # --------------------------------------------------
        # Buttons
        # --------------------------------------------------

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addRow(buttons)

    def apply(self):
        """Write edited values back to the Event."""

        self.timeline_event.timestamp = (
            self.timestamp.dateTime().toPython()
        )

        self.timeline_event.event = (
            self.event_label.toPlainText().strip()
        )

        self.timeline_event.notes = (
            self.notes.toPlainText().strip()
        )

        if self.percent is not None:
            self.timeline_event.payload["percent"] = (
                self.percent.value()
            )


class TimelinePanel(QWidget):
    """
    Displays and edits the Expedition timeline.
    """

    eventChanged = Signal(object)
    eventDeleted = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        # The actual Event objects currently displayed.
        self.events: list[Event] = []

        self.timeline = QListWidget()

        # Double-click = edit.
        self.timeline.itemDoubleClicked.connect(
            self._edit_item
        )

        self.timeline.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.timeline.customContextMenuRequested.connect(
            self._context_menu
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.timeline)

    # --------------------------------------------------
    # Events
    # --------------------------------------------------

    def add_event(self, event: Event):
        """Add a single Event to the timeline."""

        self.events.append(event)
        self._add_item(event)

    def set_events(self, events: list[Event]):
        """Replace the timeline with the supplied events."""

        self.events = list(events)

        self.timeline.clear()

        for event in self.events:
            self._add_item(event)

    def _add_item(self, event: Event):

        timestamp = event.timestamp.strftime(
            "%H:%M:%S"
        )

        text = f"{timestamp}   {event.event}"

        # Make useful raid details visible.
        if event.event == "Wipe":
            percent = event.payload.get(
                "percent"
            )

            if percent is not None:
                text += f"   • {percent}%"

        if event.event == "Pull Started":
            pull = event.payload.get("pull")

            if pull is not None:
                text += f"   • Pull {pull}"

        item = QListWidgetItem(text)

        # THIS is the important part.
        #
        # The list item now points directly at the
        # Event object rather than just displaying text.
        item.setData(
            Qt.ItemDataRole.UserRole,
            event,
        )

        self.timeline.addItem(item)

    # --------------------------------------------------
    # Editing
    # --------------------------------------------------

    def edit_selected_event(self) -> bool:
        """Edit the currently selected event, if there is one."""
        item = self.timeline.currentItem()
        if item is None:
            return False
        self._edit_item(item)
        return True

    def _edit_item(self, item: QListWidgetItem):

        event = item.data(
            Qt.ItemDataRole.UserRole
        )

        if event is None:
            return

        dialog = EventEditDialog(
            event,
            self,
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:

            dialog.apply()

            self._refresh_item(
                item,
                event,
            )

            self.eventChanged.emit(event)

    def _refresh_item(
        self,
        item: QListWidgetItem,
        event: Event,
    ):

        timestamp = event.timestamp.strftime(
            "%H:%M:%S"
        )

        text = f"{timestamp}   {event.event}"

        if event.event == "Wipe":

            percent = event.payload.get(
                "percent"
            )

            if percent is not None:
                text += f"   • {percent}%"

        if event.event == "Pull Started":

            pull = event.payload.get("pull")

            if pull is not None:
                text += f"   • Pull {pull}"

        item.setText(text)

    # --------------------------------------------------
    # Context menu
    # --------------------------------------------------

    def _context_menu(self, position):

        item = self.timeline.itemAt(position)

        if item is None:
            return

        event = item.data(32)

        if event is None:
            return

        menu = QMenu(self)

        edit_action = menu.addAction(
            "✎ Edit Event"
        )

        menu.addSeparator()

        delete_action = menu.addAction(
            "↶ Remove Event"
        )

        action = menu.exec(
            self.timeline.mapToGlobal(position)
        )

        if action == edit_action:
            self._edit_item(item)

        elif action == delete_action:
            self._delete_item(
                item,
                event,
            )

    # --------------------------------------------------
    # Delete
    # --------------------------------------------------

    def _delete_item(
        self,
        item: QListWidgetItem,
        event: Event,
    ):

        row = self.timeline.row(item)

        if row >= 0:
            self.timeline.takeItem(row)

        if event in self.events:
            self.events.remove(event)

        self.eventDeleted.emit(event)

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def clear(self):
        self.events.clear()
        self.timeline.clear()
