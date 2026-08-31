from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.roster_service import RosterService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from widgets.roster_actions import RosterActions
from widgets.roster_record import RosterRecord
from widgets.roster_table import RosterTable


class RosterPage(FoundryPage):
    """Assignments desk: roster, responsibilities, readiness, and player needs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.database = EsoDatabase(get_data_dir() / "eso.db")
        self.roster_service = RosterService(self.database)
        self.members: list[RosterMember] = []
        self._build_ui()
        self._connect_editor_signals()
        self.refresh()

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Assignments",
            subtitle="Roles, responsibilities, and what your team needs.",
            department="Raid Engine • Assignments",
        )
        self.set_header(self.header)

        self.view_combo = QComboBox()
        self.view_combo.addItems(["Encounter", "Whole Trial", "Roster"])
        self.role_combo = QComboBox()
        self.role_combo.addItems(["All Roles", "Tanks", "Healers", "Damage Dealers"])
        self.show_combo = QComboBox()
        self.show_combo.addItems(["All Players", "Active", "Bench", "Needs Attention"])
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search player or assignment...")
        self.search.textChanged.connect(self._populate_assignment_table)
        self.header.add_context_widget(self._context_field("VIEW BY", self.view_combo))
        self.header.add_context_widget(self._context_field("FILTER BY ROLE", self.role_combo))
        self.header.add_context_widget(self._context_field("SHOW", self.show_combo))
        self.header.add_context_widget(self.search)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_assignments_tab(), "ASSIGNMENTS")
        self.tabs.addTab(self._build_roster_records_tab(), "ROSTER RECORDS")
        self.tabs.addTab(self._placeholder_tab("Encounter Overrides", "Per-boss assignment overrides will live here."), "ENCOUNTER OVERRIDES")
        self.add_workspace(self.tabs)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    @staticmethod
    def _context_field(title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def _build_assignments_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        roster_card = FoundryCard("Player Assignments")
        import_button = QPushButton("Import Roster")
        roster_card.set_header_action(import_button)
        self.assignment_table = QTableWidget(0, 9)
        self.assignment_table.setHorizontalHeaderLabels([
            "Player", "Role", "Class", "Build", "Primary Assignment",
            "Secondary Assignment", "Gear Needed", "Notes", "Ready",
        ])
        self.assignment_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.assignment_table.verticalHeader().setVisible(False)
        self.assignment_table.horizontalHeader().setStretchLastSection(True)
        self.assignment_table.setMinimumHeight(430)
        roster_card.addWidget(self.assignment_table)
        root.addWidget(roster_card, 4)

        lower = QHBoxLayout()
        lower.setSpacing(10)
        self.attention_card = FoundryCard("Needs Attention")
        self.team_card = FoundryCard("Team Summary")
        self.notes_card = FoundryCard("Assignment Notes")
        self.notes_card.setProperty("parchment", True)
        self.notes_card.addWidget(QLabel(
            "• Everyone knows portal.\n"
            "• Focus on survival at 25%.\n"
            "• Execute clean.\n"
            "• Put quick player notes here during prog."
        ))
        self.notes_card.addWidget(QPushButton("Add Note"))
        lower.addWidget(self.attention_card, 2)
        lower.addWidget(self.team_card, 2)
        lower.addWidget(self.notes_card, 2)
        root.addLayout(lower, 1)
        return page

    def _build_roster_records_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        workspace = QHBoxLayout()
        self.table = RosterTable()
        self.record = RosterRecord()
        left = FoundryCard("Roster")
        left.addWidget(self.table)
        right = FoundryCard("Personnel Record")
        right.addWidget(self.record)
        right.addStretch()
        workspace.addWidget(left, 3)
        workspace.addWidget(right, 2)
        root.addLayout(workspace, 1)

        self.actions = RosterActions()
        root.addWidget(self.actions)
        return page

    def _placeholder_tab(self, title: str, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = FoundryCard(title)
        card.addWidget(QLabel(text))
        card.addStretch(1)
        layout.addWidget(card)
        return page

    def _connect_editor_signals(self):
        self.table.memberSelected.connect(self.load_member)
        self.actions.newRequested.connect(self.new_member)
        self.actions.saveRequested.connect(self.save_member)
        self.actions.deleteRequested.connect(self.delete_member)
        self.actions.refreshRequested.connect(self.refresh)

    def refresh(self):
        try:
            selected_id = self.table.selected_member_id()
            self.members = self.roster_service.list_members()
            self.table.load_members(self.members)
            self.record.set_team_choices(self.roster_service.list_team_names())
            if selected_id is not None:
                self.table.select_member_id(selected_id)
            self._populate_assignment_table()
            self._refresh_summary_cards()
            self.status.info(f"{len(self.members)} roster member(s) loaded into Assignments.")
        except Exception as exc:
            self.status.error(f"Failed to load roster: {exc}")

    def _populate_assignment_table(self, *_args):
        if not hasattr(self, "assignment_table"):
            return
        query = self.search.text().strip().lower() if hasattr(self, "search") else ""
        self.assignment_table.setRowCount(0)
        for member in self.members:
            haystack = f"{member.PlayerName} {member.CharacterName} {member.EsoClass} {member.PrimaryRole} {member.SecondaryRole} {member.Team}".lower()
            if query and query not in haystack:
                continue
            row = self.assignment_table.rowCount()
            self.assignment_table.insertRow(row)
            role = member.PrimaryRole or "Unassigned"
            values = [
                member.PlayerName or member.CharacterName or "Unnamed",
                role,
                member.EsoClass or "—",
                member.CharacterName or "—",
                self._default_assignment(role),
                self._secondary_assignment(role),
                "—",
                member.Team or "",
                "✓" if member.Status == "Active" else "•",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col in {0, 1, 2, 3, 8}:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.assignment_table.setItem(row, col, item)

    @staticmethod
    def _default_assignment(role: str) -> str:
        lower = role.lower()
        if "tank" in lower:
            return "Boss Positioning / Add Control"
        if "heal" in lower:
            return "Raid Healing / Support"
        if "damage" in lower or "dps" in lower:
            return "Boss Damage / Mechanic"
        return "Needs assignment"

    @staticmethod
    def _secondary_assignment(role: str) -> str:
        lower = role.lower()
        if "tank" in lower:
            return "Portal / Backup Control"
        if "heal" in lower:
            return "Orbs / Utility"
        if "damage" in lower or "dps" in lower:
            return "Execute / Interrupts"
        return "—"

    def _refresh_summary_cards(self):
        self.attention_card.clear()
        self.team_card.clear()
        inactive = [m for m in self.members if m.Status != "Active"]
        unassigned = [m for m in self.members if not m.PrimaryRole]
        if not inactive and not unassigned:
            self.attention_card.addWidget(QLabel("✓  No roster-level readiness issues detected."))
        else:
            for member in unassigned[:3]:
                self.attention_card.addWidget(QLabel(f"⚠  {member.PlayerName}: role / assignment needed"))
            for member in inactive[:3]:
                self.attention_card.addWidget(QLabel(f"⚠  {member.PlayerName}: {member.Status}"))

        tanks = sum(1 for m in self.members if "tank" in m.PrimaryRole.lower())
        healers = sum(1 for m in self.members if "heal" in m.PrimaryRole.lower())
        dds = max(0, len(self.members) - tanks - healers)
        active = sum(1 for m in self.members if m.Status == "Active")
        self.team_card.addWidget(QLabel(
            f"Tanks      {tanks}\n"
            f"Healers    {healers}\n"
            f"Damage     {dds}\n"
            f"Active     {active}/{len(self.members)}\n\n"
            "Gear needs and build readiness will appear here as those systems are connected."
        ))

    def load_member(self, member_id: int):
        member = self.roster_service.get_member(member_id)
        if member is not None:
            self.record.load(member)

    def new_member(self):
        self.table.clearSelection()
        self.record.clear()
        self.status.info("New personnel record. Fill it in and Save.")

    def save_member(self):
        try:
            model = self.record.model
            if not model.PlayerName:
                self.status.warning("Player Name is required.")
                return
            if model.Id is None:
                new_id = self.roster_service.create_member(model)
                self.status.success(f"Added {model.PlayerName} to the roster.")
            else:
                self.roster_service.update_member(model)
                new_id = model.Id
                self.status.success(f"Updated {model.PlayerName}.")
            self.refresh()
            self.table.select_member_id(new_id)
        except Exception as exc:
            self.status.error(f"Save failed: {exc}")

    def delete_member(self):
        model = self.record.model
        if model.Id is None:
            self.status.warning("Select a roster member to delete.")
            return
        confirm = QMessageBox.question(
            self,
            "Remove Personnel Record",
            f"Remove {model.PlayerName or 'this member'} from the roster?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.roster_service.delete_member(model.Id)
            self.record.clear()
            self.refresh()
            self.status.success("Removed from roster.")
        except Exception as exc:
            self.status.error(f"Delete failed: {exc}")
