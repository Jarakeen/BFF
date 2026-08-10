# ==================================================
# Black Feather Foundry
#
# File:
# widgets/field_notes_editor.py
#
# Purpose:
# Complete Field Notes editor.
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
    QCheckBox,
    QSizePolicy,
)


# --------------------------------------------------
# Model
# --------------------------------------------------

@dataclass
class FieldNoteModel:

    expedition: str
    location: str
    title: str

    assignment: str
    observation: str
    context: str
    next_steps: str
    random_notes: str

    observe: bool
    document: bool
    learn: bool
    share_the_lesson: bool


# --------------------------------------------------
# Widget
# --------------------------------------------------

class FieldNotesEditor(QWidget):
    """
    Complete Field Notes editor.

    Left side:
        Expedition
        Location
        Title
        Observation

    Right side:
        Clipboard Assignment
        Status
        Observations
        Context
        Notes for Future Explorers
        Random Notes
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
)
        # ==================================================
        # LEFT SIDE
        # ==================================================

        #
        # Metadata
        #

        self.expedition = QLineEdit()

        self.location = QLineEdit()

        self.title = QLineEdit()

        #
        # Main Observation
        #

        self.observation = QTextEdit()

        self.observation.setPlaceholderText(
            "Record the expedition's observations..."
        )
        self.observation.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
         )

        #
        # Left metadata
        #

        metadata = QFormLayout()

        metadata.setSpacing(8)

        metadata.addRow(
            "Expedition",
            self.expedition,
        )

        metadata.addRow(
            "Location",
            self.location,
        )

        metadata.addRow(
            "Title",
            self.title,
        )

        #
        # Left layout
        #

        left_layout = QVBoxLayout()

        left_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        left_layout.setSpacing(8)

        left_layout.addLayout(
            metadata
        )

        left_layout.addWidget(
            QLabel("Observation")
        )

        left_layout.addWidget(
            self.observation,
            1,
        )

        left_layout.addStretch()

        # ==================================================
        # RIGHT SIDE
        # ==================================================

        #
        # Clipboard Assignment
        #

        self.assignment = QLineEdit()

        self.assignment.setPlaceholderText(
            "What needs to be accomplished..."
        )

        #
        # Status
        #

        self.observe = QCheckBox(
            "Observe"
        )

        self.document = QCheckBox(
            "Document"
        )

        self.learn = QCheckBox(
            "Learn"
        )

        self.share_the_lesson = QCheckBox(
            "Share the Lesson"
        )

        status_layout = QHBoxLayout()

        status_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        status_layout.setSpacing(8)

        status_layout.addWidget(
            self.observe
        )

        status_layout.addWidget(
            self.document
        )

        status_layout.addWidget(
            self.learn
        )

        status_layout.addWidget(
            self.share_the_lesson
        )

        #
        # Context
        #

        self.context = QTextEdit()

        self.context.setPlaceholderText(
            "Context for future explorers..."
        )

        #
        # Notes for Future Explorers
        #

        self.next_steps = QTextEdit()

        self.next_steps.setPlaceholderText(
            "Notes and recommendations for future explorers..."
        )

        #
        # Random Notes
        #

        self.random_notes = QTextEdit()

        self.random_notes.setPlaceholderText(
            "Random notes, observations, reminders, "
            "or anything else worth writing down..."
        )

        #
        # Right layout
        #

        right_layout = QVBoxLayout()

        right_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        right_layout.setSpacing(6)

        #
        # Clipboard
        #

        right_layout.addWidget(
            QLabel("Clipboard Assignment")
        )

        right_layout.addWidget(
            self.assignment
        )

        #
        # Status
        #

        right_layout.addWidget(
            QLabel("Status")
        )

        right_layout.addLayout(
            status_layout
        )


        #
        # Context
        #

        right_layout.addWidget(
            QLabel("Context")
        )

        right_layout.addWidget(
            self.context,
            1,
        )

        #
        # Future Explorers
        #

        right_layout.addWidget(
            QLabel("Notes for Future Explorers")
        )

        right_layout.addWidget(
            self.next_steps,
            1,
        )

        #
        # Random Notes
        #

        right_layout.addWidget(
            QLabel("Random Notes")
        )

        right_layout.addWidget(
            self.random_notes,
            1,
        )

        right_layout.addStretch()

        # ==================================================
        # MAIN EDITOR LAYOUT
        # ==================================================

        main_layout = QHBoxLayout(self)

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        main_layout.setSpacing(12)

        #
        # Left = larger
        #

        main_layout.addLayout(
            left_layout,
            3,
        )

        #
        # Right
        #

        main_layout.addLayout(
            right_layout,
            2,
        )

    # --------------------------------------------------
    # Model
    # --------------------------------------------------

    @property
    def model(self) -> FieldNoteModel:

        return FieldNoteModel(

            expedition=(
                self.expedition
                .text()
                .strip()
            ),

            location=(
                self.location
                .text()
                .strip()
            ),

            title=(
                self.title
                .text()
                .strip()
            ),

            assignment=(
                self.assignment
                .text()
                .strip()
            ),

            observation=(
                self.observation
                .toPlainText()
                .strip()
            ),

            context=(
                self.context
                .toPlainText()
                .strip()
            ),

            next_steps=(
                self.next_steps
                .toPlainText()
                .strip()
            ),

            random_notes=(
                self.random_notes
                .toPlainText()
                .strip()
            ),

            observe=self.observe.isChecked(),

            document=self.document.isChecked(),

            learn=self.learn.isChecked(),

            share_the_lesson=(
                self.share_the_lesson
                .isChecked()
            ),
        )

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def clear(self):

        self.expedition.clear()

        self.location.clear()

        self.title.clear()

        self.assignment.clear()

        self.observation.clear()

        self.context.clear()

        self.next_steps.clear()

        self.random_notes.clear()

        self.observe.setChecked(
            False
        )

        self.document.setChecked(
            False
        )

        self.learn.setChecked(
            False
        )

        self.share_the_lesson.setChecked(
            False
        )

        self.expedition.setFocus()