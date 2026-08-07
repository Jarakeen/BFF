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
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
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


        self.observation.setPlaceholderText(
            "Record the expedition's observations..."
        )


        #
        # Metadata (Top)
        #

        left = QFormLayout()

        left.addRow(
            "Expedition",
            self.expedition,
        )

        left.addRow(
            "Title",
            self.title,
        )

        right = QFormLayout()

        right.addRow(
            "Location",
            self.location,
        )

        metadata = QHBoxLayout()

        metadata.addLayout(
            left,
            1,
        )

        metadata.addLayout(
            right,
            1,
        )

        #
        # Main Layout
        #

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(10)

        layout.addLayout(
            metadata
        )

        observation_label = QLabel(
            "Observation"
        )

        layout.addWidget(
            observation_label
        )

        layout.addWidget(
            self.observation,
            1,
        )

    # --------------------------------------------------
    # Model
    # --------------------------------------------------

    @property
    def model(self) -> FieldNoteModel:

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

        self.expedition.clear()

        self.location.clear()

        self.title.clear()

        self.observation.clear()

        self.expedition.setFocus()