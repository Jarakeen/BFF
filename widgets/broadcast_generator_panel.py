# ==================================================
# Black Feather Foundry
#
# File:
# widgets/broadcast_generator_panel.py
#
# Purpose:
# Displays generated broadcast titles and
# notifications.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QListWidget,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)


class BroadcastGeneratorPanel(QWidget):
    """
    Preview generated broadcast content.
    """

    statusMessage = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.title_list = QListWidget()

        self.notification_list = QListWidget()

        self.title_list.setToolTip(
            "Click to copy."
        )

        self.notification_list.setToolTip(
            "Click to copy."
        )

        self.notification_list.setWordWrap(True)

        self.title_list.itemClicked.connect(
            self._copy_title
        )

        self.notification_list.itemClicked.connect(
            self._copy_notification
        )

        #
        # Layout
        #

        title_layout = QVBoxLayout()

        title_layout.addWidget(
            QLabel("Stream Titles")
        )

        title_layout.addWidget(
            self.title_list
        )

        notification_layout = QVBoxLayout()

        notification_layout.addWidget(
            QLabel("Notifications")
        )

        notification_layout.addWidget(
            self.notification_list
        )

        content = QHBoxLayout()

        content.addLayout(
            title_layout
        )

        content.addLayout(
            notification_layout
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.addLayout(
            content
        )

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def clear(self):

        self.title_list.clear()

        self.notification_list.clear()

    def set_titles(
        self,
        titles: list[str],
    ):

        self.title_list.clear()

        self.title_list.addItems(
            titles
        )

    def set_notifications(
        self,
        notifications: list[str],
    ):

        self.notification_list.clear()

        self.notification_list.addItems(
            notifications
        )

    def set_result(self, result):

        self.set_titles(
            result.titles
        )

        self.set_notifications(
            result.notifications
        )

        print("Setting titles:", result.titles)
        print("Setting notifications:", result.notifications)

        self.set_titles(result.titles)
        self.set_notifications(result.notifications)

        print("Title widget count:", self.title_list.count())
        print("Notification widget count:", self.notification_list.count())
    # --------------------------------------------------
    # Selected Items
    # --------------------------------------------------

    @property
    def selected_title(self) -> str:

        item = self.title_list.currentItem()

        return item.text() if item else ""

    @property
    def selected_notification(self) -> str:

        item = self.notification_list.currentItem()

        return item.text() if item else ""

    # --------------------------------------------------
    # Clipboard
    # --------------------------------------------------

    def _copy_title(self, item):

        QApplication.clipboard().setText(
            item.text()
        )

        self.statusMessage.emit(
            "Title copied to clipboard."
        )

    def _copy_notification(self, item):

        QApplication.clipboard().setText(
            item.text()
        )

        self.statusMessage.emit(
            "Notification copied to clipboard."
        )