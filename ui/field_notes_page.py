# ==================================================
# Black Feather Foundry
#
# File:
# ui/field_notes_page.py
#
# Purpose:
# Field Notes page.
#
# ==================================================

from __future__ import annotations

import json

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QSizePolicy,
    QScrollArea,
    QFrame,
)

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.components.foundry_card import FoundryCard
from ui.foundry_page import FoundryPage

from widgets.field_notes_editor import FieldNotesEditor
from widgets.field_notes_actions import FieldNotesActions

from services.archive_service import ArchiveService
from services.settings_service import SettingsService


class FieldNotesPage(FoundryPage):
    """
    Field Notes page.
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

        #
        # Header
        #

        self.header = FoundryHeader(
            title="Field Notes",
            subtitle=(
                "Record today's observations "
                "for the Archive."
            ),
            department="Archives",
        )

        self.set_header(
            self.header
        )

        #
        # Main Editor
        #

        self.editor = FieldNotesEditor()

        editor_card = FoundryCard(
            "Field Notes"
        )

        editor_card.addWidget(
            self.editor
        )

        #
        # Actions
        #

        self.actions = FieldNotesActions()

        #
        # Status
        #

        self.status = FoundryStatusBar()

        #
        # IMPORTANT:
        # FoundryPage already owns the workspace,
        # scroll area, action bar, and status bar.
        # Do not create another workspace here.
        #

        self.add_workspace(
            editor_card
        )

        self.set_actions(
            self.actions
        )

        self.set_status(
            self.status
        )

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
        Save the current Field Note to CurrentBroadcast.json.
        """

        try:

            import json

            model = self.editor.model

            broadcast_path = Path(
                self.settings["CurrentBroadcastPath"]
            )

            print(
                f"[FIELD NOTES] Broadcast path: {broadcast_path}"
            )

            print(
                f"[FIELD NOTES] Absolute path: "
                f"{broadcast_path.resolve()}"
            )

            #
            # Make sure the folder exists
            #

            broadcast_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            print(
                "[FIELD NOTES] Parent folder ready."
            )

            #
            # Load existing JSON if it exists
            #

            if broadcast_path.exists():

                print(
                    "[FIELD NOTES] Existing CurrentBroadcast.json found."
                )

                data = json.loads(
                    broadcast_path.read_text(
                        encoding="utf-8"
                    )
                )

            else:

                print(
                    "[FIELD NOTES] CurrentBroadcast.json does not exist. "
                    "Creating it."
                )

                data = {}

            #
            # Field Note data
            #

            data["Status"] = {
                "Observe": model.observe,
                "Document": model.document,
                "Learn": model.learn,
                "ShareTheLesson": model.share_the_lesson,
            }

            data["Assignment"] = model.assignment

            data["Observation"] = model.observation

            data["Context"] = model.context

            data["NextSteps"] = model.next_steps

            data["RandomNotes"] = model.random_notes

            print(
                "[FIELD NOTES] Data prepared."
            )

            #
            # Write JSON
            #

            broadcast_path.write_text(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=4,
                ),
                encoding="utf-8",
            )

            print(
                "[FIELD NOTES] CurrentBroadcast.json written."
            )

            self.status.success(
                "Field Note saved to OBS."
            )

        except Exception as exc:

            print(
                f"[FIELD NOTES] SAVE ERROR: {exc}"
            )

            self.status.error(
                f"Field Note save failed: {exc}"
            )

    def clear(self):

        self.editor.clear()

        self.status.info(
            "Field note cleared."
        )

    def archive(self):

        try:

            model = self.editor.model

            report_id, path = (
                self.archive_service.file_form(
                    "FN",
                    lambda report_id, number: [

                        f"# Field Note {report_id}",

                        "",

                        f"Expedition: "
                        f"{model.expedition}",

                        f"Location: "
                        f"{model.location}",

                        "",

                        f"## {model.title}",

                        "",

                        "Status:",

                        (
                            "Observe"
                            if model.observe
                            else ""
                        ),

                        (
                            "Document"
                            if model.document
                            else ""
                        ),

                        (
                            "Learn"
                            if model.learn
                            else ""
                        ),

                        (
                            "Share the Lesson"
                            if model.share_the_lesson
                            else ""
                        ),

                        "",

                        "Clipboard Assignment:",

                        model.assignment,

                        "",

                        "Observation:",

                        model.observation,

                        "",

                        "Context:",

                        model.context,

                        "",

                        "Notes for Future Explorers:",

                        model.next_steps,

                        "",

                        "Random Notes:",

                        model.random_notes,

                    ],
                )
            )

            self.status.success(
                f"Archived as {report_id}."
            )

        except Exception as exc:

            self.status.error(
                f"Archive failed: {exc}"
            )