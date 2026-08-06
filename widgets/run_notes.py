# ==================================================
# Black Feather Foundry
#
# File:
# widgets/run_notes.py
#
# Purpose:
# Notes editor for Achievement Runs.
#
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QTextEdit,
    QLabel,
    QVBoxLayout,
)


class RunNotes(QWidget):
    """
    Notes editor for an Achievement Run.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Editors
        #

        self.notes = QTextEdit()

        self.notes.setPlaceholderText(
            "Clean pulls, boss notes, and key moments."
        )

        self.lessons = QTextEdit()

        self.lessons.setPlaceholderText(
            "Lessons learned and improvements for next time."
        )

        self.next_steps = QTextEdit()

        self.next_steps.setPlaceholderText(
            "What should the crew try next?"
        )

        #
        # Layout
        #

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(
            QLabel("Run Notes")
        )

        layout.addWidget(
            self.notes
        )

        layout.addWidget(
            QLabel("Lessons Learned")
        )

        layout.addWidget(
            self.lessons
        )

        layout.addWidget(
            QLabel("What's Next?")
        )

        layout.addWidget(
            self.next_steps
        )

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def clear(self):
        """
        Clear all notes.
        """

        self.notes.clear()

        self.lessons.clear()

        self.next_steps.clear()

    @property
    def run_notes(self) -> dict:
        """
        Return the current notes.
        """

        return {
            "notes": self.notes.toPlainText().strip(),
            "lessons": self.lessons.toPlainText().strip(),
            "next_steps": self.next_steps.toPlainText().strip(),
        }

    def set_notes(self, data: dict):
        """
        Populate the editor.
        """

        self.notes.setPlainText(
            data.get("notes", "")
        )

        self.lessons.setPlainText(
            data.get("lessons", "")
        )

        self.next_steps.setPlainText(
            data.get("next_steps", "")
        )