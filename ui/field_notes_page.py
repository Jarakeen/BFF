# ==================================================
# Black Feather Foundry
#
# File:
# ui/field_notes_page.py
#
# Purpose:
# Field Notes page.
#
# Records expedition observations and preserves
# notable discoveries as permanent archive entries.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
)

from widgets.page_header import PageHeader
from widgets.status_panel import StatusPanel
from ui.components.section_card import SectionCard

from widgets.field_notes_editor import FieldNotesEditor
from widgets.field_notes_actions import FieldNotesActions

from services.archive_service import ArchiveService
from services.settings_service import SettingsService


class FieldNotesPage(QWidget):
    """
    Field Notes.

    Record expedition observations for the Archive.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Settings
        #

        self.settings = SettingsService(
            Path("settings.json")
        ).load()

        #
        # Services
        #

        self.archive_service = ArchiveService(
            counters_folder=Path(
                self.settings["CountersFolder"]
            ),
            archive_folder=Path(
                self.settings["ArchiveFolder"]
            ),
        )

        #
        # UI
        #

        self.build_ui()

        #
        # Signals
        #

        self.connect_signals()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.header = PageHeader(
            title="Field Notes",
            subtitle="Record today's observations for the Archive.",
            department="Archives",
        )

        self.editor = FieldNotesEditor()

        self.actions = FieldNotesActions()

        self.status = StatusPanel()

        layout.addWidget(self.header)

        editor = SectionCard("Observation")
        editor.addWidget(self.editor)
        layout.addWidget(editor)

        actions = SectionCard("Actions")
        actions.addWidget(self.actions)
        layout.addWidget(actions)

        layout.addStretch()

        layout.addWidget(self.status)

        self.status.info(
            "Ready to record today's observations."
        )

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.actions.saveRequested.connect(
            self.save
        )

        self.actions.clearRequested.connect(
            self.clear
        )

        self.actions.archiveRequested.connect(
            self.archive
        )

    # --------------------------------------------------
    # Actions
    # --------------------------------------------------

    def save(self):
        """
        Save the current field note.
        """

        model = self.editor.model

        #
        # Save draft here later.
        #

        self.status.success(
            "Field note saved."
        )

    def clear(self):
        """
        Reset the editor.
        """

        self.editor.clear()

        self.status.info(
            "Field note cleared."
        )

    def archive(self):
        """
        Archive the current field note.
        """

        try:

            model = self.editor.model

            report_id, path = self.archive_service.file_form(
                "FN",
                lambda report_id, number: [

                    f"# Field Note {report_id}",

                    "",

                    f"Expedition: {model.expedition}",

                    f"Location: {model.location}",

                    "",

                    f"## {model.title}",

                    "",

                    model.observation,

                ],
            )

            self.status.success(
                f"Archived as {report_id}."
            )

        except Exception as exc:

            self.status.error(
                f"Archive failed: {exc}"
            )