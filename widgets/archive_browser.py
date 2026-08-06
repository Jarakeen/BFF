# ==================================================
# Black Feather Foundry
#
# File:
# widgets/archive_browser.py
#
# Purpose:
# Searchable browser for archived Expeditions.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt, Signal

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
)


class ArchiveBrowser(QWidget):
    """
    Searchable list of archived Expedition records.
    """

    archiveSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Controls
        #

        self.search = QLineEdit()

        self.search.setPlaceholderText(
            "Search Expeditions..."
        )

        self.archive_list = QListWidget()

        #
        # Layout
        #

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(self.search)
        layout.addWidget(self.archive_list)

        #
        # Signals
        #

        self.search.textChanged.connect(
            self.filter
        )

        self.archive_list.itemSelectionChanged.connect(
            self._selection_changed
        )

    # --------------------------------------------------
    # Loading
    # --------------------------------------------------

    def load_records(self, records):
        """
        Populate the browser with archive records.
        """

        self.archive_list.clear()

        for record in records:

            item = QListWidgetItem(
                record.name
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                record.archive_no,
            )

            self.archive_list.addItem(item)

    def refresh(self, records):
        """
        Reload the archive browser.
        """

        self.load_records(records)

    # --------------------------------------------------
    # Search
    # --------------------------------------------------

    def filter(self, text: str):
        """
        Filter archive entries.
        """

        text = text.lower().strip()

        for row in range(
            self.archive_list.count()
        ):

            item = self.archive_list.item(row)

            visible = (
                text in item.text().lower()
            )

            item.setHidden(
                not visible
            )

    # --------------------------------------------------
    # Selection
    # --------------------------------------------------

    def _selection_changed(self):
        """
        Emit the selected archive ID.
        """

        item = self.archive_list.currentItem()

        if item is None:
            return

        self.archiveSelected.emit(
            item.data(
                Qt.ItemDataRole.UserRole
            )
        )

    @property
    def current_archive(self):
        """
        Return the selected archive ID.
        """

        item = self.archive_list.currentItem()

        if item is None:
            return None

        return item.data(
            Qt.ItemDataRole.UserRole
        )

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def clear(self):
        """
        Reset the browser.
        """

        self.search.clear()
        self.archive_list.clear()