# ==================================================
# Black Feather Foundry
#
# File:
# widgets/archive_preview.py
#
# Purpose:
# Displays the selected archive record.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
)


class ArchivePreview(QWidget):
    """
    Read-only preview of an archived record.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Controls
        #

        self.preview = QTextEdit()

        self.preview.setReadOnly(True)

        #
        # Layout
        #

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.preview)

    # --------------------------------------------------
    # Loading
    # --------------------------------------------------

    def load_file(
        self,
        path: Path,
    ):
        """
        Display an archive file.
        """

        if not path.exists():

            self.preview.setPlainText(
                "Archive not found."
            )

            return

        self.preview.setPlainText(
            path.read_text(
                encoding="utf-8"
            )
        )

    def load_text(
        self,
        text: str,
    ):
        """
        Display archive text.
        """

        self.preview.setPlainText(text)

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def clear(self):
        """
        Clear the preview.
        """

        self.preview.clear()