# ==================================================
# Black Feather Foundry
#
# File:
# ui/roster_page.py
#
# Purpose:
# Roster Desk page.
#
# Maintain expedition personnel: players, characters,
# ESO classes, roles, team, and availability.
#
# This is the roster management interface, not the
# raid optimizer - the optimizer is a later engine
# that will read this data, not something this page
# implements.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QWidget,
)

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar

from ui.components.foundry_card import FoundryCard

from widgets.roster_table import RosterTable
from widgets.roster_record import RosterRecord
from widgets.roster_actions import RosterActions

from ui.foundry_page import FoundryPage

from services.eso_database import EsoDatabase
from services.roster_service import RosterService

from models.roster_model import RosterMember


class RosterPage(FoundryPage):
    """
    Roster Desk.

    Maintain expedition personnel and their
    capabilities.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_services()
        self.build_ui()
        self.connect_signals()

        self.refresh()

    # --------------------------------------------------
    # Services
    # --------------------------------------------------

    def build_services(self):

        #
        # Same eso.db used everywhere else in the
        # Foundry (see CollectionsPage / MainWindow) -
        # the roster is not a separate database.
        #

        data_dir = (
            Path(__file__).resolve().parents[1] / "data"
        )

        self.database = EsoDatabase(
            data_dir / "eso.db"
        )

        self.roster_service = RosterService(
            self.database
        )

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        #
        # Header
        #

        self.header = FoundryHeader(
            title="Roster",
            subtitle="Maintain expedition personnel and their capabilities.",
            department="Operations",
        )

        #
        # Widgets
        #

        self.table = RosterTable()

        self.record = RosterRecord()

        self.actions = RosterActions()

        self.status = FoundryStatusBar()

        #
        # Page
        #

        self.set_header(self.header)

        #
        # Workspace
        #

        workspace_widget = QWidget()

        workspace = QHBoxLayout(workspace_widget)

        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(12)

        #
        # Left Card - Roster
        #

        roster_card = FoundryCard("Roster")

        roster_card.addWidget(self.table)

        #
        # Right Card - Personnel Record
        #

        record_card = FoundryCard("Personnel Record")

        record_card.addWidget(self.record)
        record_card.addStretch()

        #
        # Assemble Workspace
        #

        workspace.addWidget(
            roster_card,
            3,
        )

        workspace.addWidget(
            record_card,
            2,
        )

        self.add_workspace(workspace_widget)

        #
        # Bottom
        #

        self.set_actions(self.actions)

        self.set_status(self.status)

        self.status.info(
            "Roster Desk ready."
        )

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.table.memberSelected.connect(
            self.load_member
        )

        self.actions.newRequested.connect(
            self.new_member
        )

        self.actions.saveRequested.connect(
            self.save_member
        )

        self.actions.deleteRequested.connect(
            self.delete_member
        )

        self.actions.refreshRequested.connect(
            self.refresh
        )

    # --------------------------------------------------
    # Actions
    # --------------------------------------------------

    def refresh(self):

        try:

            selected_id = self.table.selected_member_id()

            members = self.roster_service.list_members()

            self.table.load_members(members)

            self.record.set_team_choices(
                self.roster_service.list_team_names()
            )

            if selected_id is not None:
                self.table.select_member_id(selected_id)

            self.status.info(
                f"{len(members)} roster member(s) loaded."
            )

        except Exception as exc:

            self.status.error(
                f"Failed to load roster: {exc}"
            )

    def load_member(
        self,
        member_id: int,
    ):

        member = self.roster_service.get_member(
            member_id
        )

        if member is not None:
            self.record.load(member)

    def new_member(self):

        self.table.clearSelection()

        self.record.clear()

        self.status.info(
            "New personnel record. Fill it in and Save."
        )

    def save_member(self):

        try:

            model = self.record.model

            if not model.PlayerName:

                self.status.warning(
                    "Player Name is required."
                )

                return

            if model.Id is None:

                new_id = self.roster_service.create_member(
                    model
                )

                self.status.success(
                    f"Added {model.PlayerName} to the roster."
                )

            else:

                self.roster_service.update_member(
                    model
                )

                new_id = model.Id

                self.status.success(
                    f"Updated {model.PlayerName}."
                )

            self.refresh()

            self.table.select_member_id(new_id)

        except Exception as exc:

            self.status.error(
                f"Save failed: {exc}"
            )

    def delete_member(self):

        model = self.record.model

        if model.Id is None:

            self.status.warning(
                "Select a roster member to delete."
            )

            return

        confirm = QMessageBox.question(
            self,
            "Remove Personnel Record",
            f"Remove {model.PlayerName or 'this member'} from the roster?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:

            self.roster_service.delete_member(
                model.Id
            )

            self.record.clear()

            self.refresh()

            self.status.success(
                "Removed from roster."
            )

        except Exception as exc:

            self.status.error(
                f"Delete failed: {exc}"
            )
