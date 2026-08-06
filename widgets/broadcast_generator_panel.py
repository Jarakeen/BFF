# ==================================================
# Black Feather Foundry
#
# File:
# widgets/broadcast_generator_panel.py
#
# Purpose:
# Displays generated broadcast titles and
# live notifications.
#
# ==================================================

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QLabel,
    QHBoxLayout,
    QListWidget,
    QVBoxLayout,
    QWidget,
)


class BroadcastGeneratorPanel(QWidget):
    """
    Displays generated broadcast copy.

    Clicking a title or notification copies it
    to the clipboard.
    """

    statusMessage = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        #
        # Output
        #

        output_row = QHBoxLayout()

        #
        # Stream Titles
        #

        title_layout = QVBoxLayout()

        self.title_label = QLabel("Stream Titles")
        self.title_list = QListWidget()

        self.title_list.setToolTip(
            "Click to copy."
        )

        self.title_list.itemClicked.connect(
            self._copy_title
        )

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.title_list)

        output_row.addLayout(title_layout)

        #
        # Live Notifications
        #

        notification_layout = QVBoxLayout()

        self.notification_label = QLabel("Live Notifications")
        self.notification_list = QListWidget()

        self.notification_list.setWordWrap(True)

        self.notification_list.setToolTip(
            "Click to copy."
        )

        self.notification_list.itemClicked.connect(
            self._copy_notification
        )

        notification_layout.addWidget(self.notification_label)
        notification_layout.addWidget(self.notification_list)

        output_row.addLayout(notification_layout)

        layout.addLayout(output_row)

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

        self.title_list.addItems(titles)

    def set_notifications(
        self,
        notifications: list[str],
    ):

        self.notification_list.clear()

        self.notification_list.addItems(
            notifications
        )

    def set_result(self, result):

        self.set_titles(result.titles)

        self.set_notifications(
            result.notifications
        )

    # --------------------------------------------------
    # Selection
    # --------------------------------------------------

    def selected_title(self):

        item = self.title_list.currentItem()

        if item:

            return item.text()

        return ""

    def selected_notification(self):

        item = self.notification_list.currentItem()

        if item:

            return item.text()

        return ""

    # --------------------------------------------------
    # Clipboard
    # --------------------------------------------------

    def _copy_title(self, item):

        QApplication.clipboard().setText(
            item.text()
        )

        self.statusMessage.emit(
            "Stream title copied."
        )

    def _copy_notification(self, item):

        QApplication.clipboard().setText(
            item.text()
        )

        self.statusMessage.emit(
            "Live notification copied."
        )