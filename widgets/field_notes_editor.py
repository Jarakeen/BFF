# ==================================================
# Black Feather Foundry
#
# File:
# widgets/field_notes_editor.py
#
# Purpose:
# Editor for creating Field Notes.
#
# ==================================================

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QTextEdit,
)


# --------------------------------------------------
# Model
# --------------------------------------------------

@dataclass
class FieldNoteModel:
    expedition: str
    location: str
    title: str
    observation: str


# --------------------------------------------------
# Widget
# --------------------------------------------------

class FieldNotesEditor(QWidget):
    """
    Editor for Field Notes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Controls
        #

        self.expedition = QLineEdit()

        self.location = QLineEdit()

        self.title = QLineEdit()

        self.observation = QTextEdit()

        #
        # Layout
        #

        layout = QFormLayout(self)

        layout.addRow(
            "Expedition",
            self.expedition,
        )

        layout.addRow(
            "Location",
            self.location,
        )

        layout.addRow(
            "Title",
            self.title,
        )

        layout.addRow(
            "Observation",
            self.observation,
        )

    # --------------------------------------------------
    # Model
    # --------------------------------------------------

    @property
    def model(self) -> FieldNoteModel:
        """
        Return the current field note.
        """

        return FieldNoteModel(
            expedition=self.expedition.text().strip(),
            location=self.location.text().strip(),
            title=self.title.text().strip(),
            observation=self.observation.toPlainText().strip(),
        )

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def clear(self):
        """
        Reset the editor.
        """

        self.expedition.clear()
        self.location.clear()
        self.title.clear()
        self.observation.clear()

        self.expedition.setFocus()