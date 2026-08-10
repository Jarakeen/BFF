# ==================================================
# Black Feather Foundry
#
# File:
# widgets/roster_table.py
#
# Purpose:
# Compact list of roster members. Selecting a row
# loads that member into the Personnel Record.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from models.roster_model import RosterMember


class RosterTable(QTableWidget):
    """
    Compact roster table.

    A full 12-person trial roster should fit without
    scrolling - rows stay tight and columns resize to
    content rather than stretching.
    """

    HEADERS = [
        "Player",
        "Character",
        "Class",
        "Primary",
        "Secondary",
        "Team",
        "Status",
    ]

    memberSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(0, len(self.HEADERS), parent)

        self.setHorizontalHeaderLabels(self.HEADERS)

        self.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )

        self.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.setAlternatingRowColors(True)

        self.setSortingEnabled(True)

        self.verticalHeader().setVisible(False)

        self.verticalHeader().setDefaultSectionSize(22)

        self.horizontalHeader().setStretchLastSection(False)

        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        self.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )

        self.itemSelectionChanged.connect(
            self._selection_changed
        )

    # --------------------------------------------------
    # Data
    # --------------------------------------------------

    def load_members(
        self,
        members: list[RosterMember],
    ):

        self.setSortingEnabled(False)

        self.setRowCount(0)

        for member in members:
            self._add_row(member)

        self.setSortingEnabled(True)

    def _add_row(
        self,
        member: RosterMember,
    ):

        row = self.rowCount()

        self.insertRow(row)

        values = [
            member.PlayerName,
            member.CharacterName,
            member.EsoClass,
            member.PrimaryRole,
            member.SecondaryRole,
            member.Team,
            member.Status,
        ]

        for column, value in enumerate(values):

            item = QTableWidgetItem(str(value))

            item.setFlags(
                item.flags() & ~Qt.ItemFlag.ItemIsEditable
            )

            if column == 0:
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    member.Id,
                )

            self.setItem(
                row,
                column,
                item,
            )

    # --------------------------------------------------
    # Selection
    # --------------------------------------------------

    def _selection_changed(self):

        member_id = self.selected_member_id()

        if member_id is not None:
            self.memberSelected.emit(member_id)

    def selected_member_id(self) -> int | None:

        rows = self.selectionModel().selectedRows()

        if not rows:
            return None

        item = self.item(rows[0].row(), 0)

        if item is None:
            return None

        return item.data(Qt.ItemDataRole.UserRole)

    def select_member_id(
        self,
        member_id: int,
    ):

        for row in range(self.rowCount()):

            item = self.item(row, 0)

            if item and item.data(
                Qt.ItemDataRole.UserRole
            ) == member_id:

                self.selectRow(row)

                return
