from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
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

from engine.config import get_data_dir, get_user_database_path
from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.finch_roster_sync_service import sync_finch_gear_needs
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from services.roster_service import RosterService
from services.roster_player_identity_service import RosterPlayerIdentityService
from services.user_safety_snapshot_service import UserSafetySnapshotService
from ui.ui_safety import confirm_destructive_action
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from widgets.roster_actions import RosterActions
from widgets.roster_record import RosterRecord
from widgets.roster_table import RosterTable


_GENERIC_ASSIGNMENT_CHOICES: tuple[tuple[str, str], ...] = (
    ("Boss Positioning / Add Control", "mechanic:boss_positioning_add_control"),
    ("Portal / Backup Control", "mechanic:portal_backup_control"),
    ("Raid Healing / Support", "role:raid_healing_support"),
    ("Orbs / Utility", "role:orbs_utility"),
    ("Boss Damage / Mechanic", "role:boss_damage_mechanic"),
    ("Execute / Interrupts", "mechanic:execute_interrupts"),
    ("Interrupts", "mechanic:interrupts"),
    ("Portal", "mechanic:portal"),
    ("Kite", "mechanic:kite"),
    ("Add Control", "mechanic:add_control"),
    ("Boss Positioning", "mechanic:boss_positioning"),
    ("Mechanic", "mechanic:general"),
    ("Utility", "role:utility"),
    ("Backup", "role:backup"),
    ("Needs assignment", "state:needs_assignment"),
    ("—", "state:none"),
)


def _assignment_choice_rows() -> tuple[tuple[str, str], ...]:
    """Return display labels paired with stable assignment identities.

    Raid-support choices reuse the existing canonical coverage requirement IDs.
    The small generic set covers raid-lead responsibilities that are not provider
    requirements yet, without pretending those labels are encounter mechanics.
    """
    rows: list[tuple[str, str]] = list(_GENERIC_ASSIGNMENT_CHOICES)
    seen = {label.casefold() for label, _ in rows}
    for requirement in DEFAULT_RAID_COVERAGE_PROFILE.requirements:
        label = requirement.display_name.strip()
        if not label or label.casefold() in seen:
            continue
        rows.append((label, f"requirement:{requirement.requirement_id}"))
        seen.add(label.casefold())
    return tuple(rows)


_ASSIGNMENT_CHOICES = _assignment_choice_rows()
_FINCH_SYNC_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="finch-sync")


class RosterPage(FoundryPage):
    """Assignments desk: roster, responsibilities, readiness, and player needs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.database = EsoDatabase(get_user_database_path())
        self.roster_service = RosterService(self.database)
        self.identity_service = RosterPlayerIdentityService(self.database)
        self.members: list[RosterMember] = []
        self._all_members: list[RosterMember] = []
        self._finch_sync_future: Future | None = None
        self._finch_sync_timer = QTimer(self)
        self._finch_sync_timer.setInterval(100)
        self._finch_sync_timer.timeout.connect(self._poll_finch_sync)
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
        self.show_combo.addItems(
            ["All Players", "Active", "Bench", "Needs Attention", "Archived"]
        )
        self.show_combo.currentTextChanged.connect(self._apply_player_filter)
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
        self.tabs.addTab(
            self._placeholder_tab(
                "Encounter Overrides",
                "Per-boss assignment overrides will live here.",
            ),
            "ENCOUNTER OVERRIDES",
        )
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
        root.setSpacing(8)

        roster_card = FoundryCard("Player Assignments", "⚑")
        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)
        import_button = QPushButton("Import Roster")
        self.sync_finch_button = QPushButton("Sync Finch")
        self.sync_finch_button.setToolTip(
            "Apply pending Finch team requests to existing FoundryDock Personnel and assignments."
        )
        self.sync_finch_button.clicked.connect(self.sync_finch)
        self.remove_assignment_button = QPushButton("Remove Selected")
        self.remove_assignment_button.clicked.connect(self.remove_selected_assignment)
        actions_layout.addWidget(import_button)
        actions_layout.addWidget(self.sync_finch_button)
        actions_layout.addWidget(self.remove_assignment_button)
        roster_card.set_header_action(actions)

        self.assignment_table = QTableWidget(0, 9)
        self.assignment_table.setHorizontalHeaderLabels([
            "Player",
            "Role",
            "Class",
            "Build",
            "Primary Assignment",
            "Secondary Assignment",
            "Gear Needed",
            "Notes",
            "Ready",
        ])
        self.assignment_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.assignment_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.assignment_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.assignment_table.verticalHeader().setVisible(False)
        self.assignment_table.horizontalHeader().setStretchLastSection(True)
        self.assignment_table.setMinimumHeight(430)
        roster_card.addWidget(self.assignment_table)
        root.addWidget(roster_card, 4)

        lower = QHBoxLayout()
        lower.setSpacing(8)
        self.attention_card = FoundryCard("Needs Attention", "⚠").set_watermark(
            "compass", 0.04
        )
        self.team_card = FoundryCard("Team Summary", "◈").set_watermark(
            "compass", 0.055
        )
        self.notes_card = (
            FoundryCard("Assignment Notes", "✎")
            .make_parchment()
            .set_watermark("feather", 0.12)
        )
        self.notes_card.addWidget(
            QLabel(
                "• Everyone knows portal.\n"
                "• Focus on survival at 25%.\n"
                "• Execute clean.\n"
                "• Put quick player notes here during prog."
            )
        )
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
        root.setSpacing(8)

        workspace = QHBoxLayout()
        self.table = RosterTable()
        self.record = RosterRecord()
        left = FoundryCard("Roster", "☷")
        left.addWidget(self.table)
        right = FoundryCard("Personnel Record", "✎").set_watermark("feather", 0.045)
        right.addWidget(self.record)
        right.addStretch()
        workspace.addWidget(left, 3)
        workspace.addWidget(right, 2)
        root.addLayout(workspace, 1)

        self.actions = RosterActions()
        self.actions.delete_button.setText("Archive Player")
        self.actions.delete_button.setToolTip(
            "Archive this player without deleting their history, builds, or aliases."
        )

        lifecycle = QHBoxLayout()
        lifecycle.setContentsMargins(0, 0, 0, 0)
        lifecycle.setSpacing(8)
        lifecycle.addWidget(self.actions, 1)

        self.restore_player_button = QPushButton("Restore Player")
        self.restore_player_button.clicked.connect(self.restore_member)
        lifecycle.addWidget(self.restore_player_button)

        self.permanent_delete_button = QPushButton("Delete Permanently")
        self.permanent_delete_button.setProperty("danger", True)
        self.permanent_delete_button.clicked.connect(self.delete_member_permanently)
        lifecycle.addWidget(self.permanent_delete_button)

        root.addLayout(lifecycle)
        return page

    def _placeholder_tab(self, title: str, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = FoundryCard(title).set_watermark("compass", 0.045)
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
            self._all_members = self.roster_service.list_members(include_archived=True)
            self.members = self._filtered_members(self._all_members)
            self.table.load_members(self.members)
            self.record.set_team_choices(self.roster_service.list_team_names())
            if selected_id is not None:
                self.table.select_member_id(selected_id)
            self._populate_assignment_table()
            self._refresh_summary_cards()
            self._update_personnel_lifecycle_actions()
            self.status.info(
                f"{len(self.members)} roster member(s) loaded into Assignments."
            )
        except Exception as exc:
            self.status.error(f"Failed to load roster: {exc}")

    def sync_finch(self) -> None:
        if self._finch_sync_future is not None and not self._finch_sync_future.done():
            self.status.info("Finch sync is already running.")
            return

        self.sync_finch_button.setEnabled(False)
        self.status.info("Syncing pending Finch requests…")
        database_path = Path(get_data_dir()) / "eso.db"
        self._finch_sync_future = _FINCH_SYNC_EXECUTOR.submit(
            sync_finch_gear_needs,
            database_path=database_path,
            settings_path=Path("settings.json"),
        )
        self._finch_sync_timer.start()

    def _poll_finch_sync(self) -> None:
        future = self._finch_sync_future
        if future is None or not future.done():
            return

        self._finch_sync_timer.stop()
        self._finch_sync_future = None
        self.sync_finch_button.setEnabled(True)
        try:
            summary = future.result()
        except Exception as exc:
            self.status.error(f"Finch sync failed: {exc}")
            return

        self.refresh()
        if summary.errors:
            first_error = next(
                (row.message for row in summary.results if row.status == "error"),
                "Unknown sync error.",
            )
            self.status.error(
                f"Finch sync: {summary.applied} applied, {summary.rejected} rejected, "
                f"{summary.errors} error(s). {first_error}"
            )
        elif summary.rejected:
            first_rejection = next(
                (row.message for row in summary.results if row.status == "rejected"),
                "A Finch request needs attention.",
            )
            self.status.warning(
                f"Finch sync: {summary.applied} applied, {summary.rejected} rejected. "
                f"{first_rejection}"
            )
        elif summary.fetched or summary.registrations_fetched:
            self.status.success(
                "Finch sync complete: "
                f"{summary.registrations_applied}/{summary.registrations_fetched} "
                "Discord identity record(s) refreshed; "
                f"{summary.applied} gear request(s) applied."
                + (
                    f" {summary.registrations_unresolved} registration(s) need identity review."
                    if summary.registrations_unresolved
                    else ""
                )
            )
        else:
            self.status.info("Finch sync complete: no pending requests or registrations.")

    def _filtered_members(self, members: list[RosterMember]) -> list[RosterMember]:
        mode = self.show_combo.currentText().strip() if hasattr(self, "show_combo") else "All Players"
        current = [
            member for member in members
            if str(member.Status or "").strip().casefold() != "archived"
        ]
        if mode == "Archived":
            return [
                member for member in members
                if str(member.Status or "").strip().casefold() == "archived"
            ]
        if mode == "Active":
            return [
                member for member in current
                if str(member.Status or "").strip().casefold() == "active"
            ]
        if mode == "Bench":
            return [
                member for member in current
                if str(member.Status or "").strip().casefold() in {"sub", "bench"}
            ]
        if mode == "Needs Attention":
            return [
                member for member in current
                if not str(member.PrimaryRole or "").strip()
                or str(member.Status or "").strip().casefold() not in {"active", "sub", "bench"}
            ]
        return current

    def _apply_player_filter(self, *_args) -> None:
        selected_id = self.table.selected_member_id() if hasattr(self, "table") else None
        self.members = self._filtered_members(self._all_members)
        if hasattr(self, "table"):
            self.table.load_members(self.members)
            if selected_id is not None:
                self.table.select_member_id(selected_id)
        self._populate_assignment_table()
        self._refresh_summary_cards()
        self._update_personnel_lifecycle_actions()

    def _update_personnel_lifecycle_actions(self) -> None:
        if not hasattr(self, "restore_player_button"):
            return
        member_id = self.record.model.Id if hasattr(self, "record") else None
        member = self.roster_service.get_member(int(member_id)) if member_id else None
        archived = bool(
            member is not None
            and str(member.Status or "").strip().casefold() == "archived"
        )
        self.restore_player_button.setEnabled(archived)
        self.permanent_delete_button.setEnabled(archived)
        self.actions.delete_button.setEnabled(member is not None and not archived)

    @staticmethod
    def _assignment_combo(value: str) -> QComboBox:
        """Build the same case-insensitive contains autocomplete used in Builds."""
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setDuplicatesEnabled(False)
        combo.setMinimumWidth(190)
        for label, assignment_id in _ASSIGNMENT_CHOICES:
            combo.addItem(label, assignment_id)

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)
        if combo.lineEdit() is not None:
            combo.lineEdit().setClearButtonEnabled(True)
            combo.lineEdit().setPlaceholderText("Type to find assignment…")

        match = combo.findText(value, Qt.MatchFlag.MatchFixedString)
        if match >= 0:
            combo.setCurrentIndex(match)
        else:
            combo.setCurrentText(value)
        combo.setToolTip(
            "Start typing any part of an assignment name to filter the list."
        )
        return combo

    def _set_assignment_cell(self, row: int, column: int, value: str) -> None:
        """Keep a backing item for existing CSV/PDF/Discord exporters."""
        item = QTableWidgetItem(value)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.assignment_table.setItem(row, column, item)

        combo = self._assignment_combo(value)
        combo.currentTextChanged.connect(item.setText)
        self.assignment_table.setCellWidget(row, column, combo)

    def _populate_assignment_table(self, *_args):
        if not hasattr(self, "assignment_table"):
            return
        query = self.search.text().strip().lower() if hasattr(self, "search") else ""
        self.assignment_table.setRowCount(0)
        for member in self.members:
            role = member.PrimaryRole or "Unassigned"
            primary_assignment = self._default_assignment(role)
            secondary_assignment = self._secondary_assignment(role)
            haystack = (
                f"{member.PlayerName} {member.CharacterName} {member.EsoClass} "
                f"{member.PrimaryRole} {member.SecondaryRole} {member.Team} "
                f"{primary_assignment} {secondary_assignment}"
            ).lower()
            if query and query not in haystack:
                continue
            row = self.assignment_table.rowCount()
            self.assignment_table.insertRow(row)
            values = [
                member.PlayerName or member.CharacterName or "Unnamed",
                role,
                member.EsoClass or "—",
                member.CharacterName or "—",
                primary_assignment,
                secondary_assignment,
                "—",
                member.Team or "",
                "✓" if member.Status == "Active" else "•",
            ]
            for col, value in enumerate(values):
                if col in {4, 5}:
                    self._set_assignment_cell(row, col, str(value))
                    continue
                item = QTableWidgetItem(str(value))
                if col == 0 and member.Id is not None:
                    item.setData(Qt.ItemDataRole.UserRole, int(member.Id))
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
            self.attention_card.addWidget(
                QLabel("✓  No roster-level readiness issues detected.")
            )
        else:
            for member in unassigned[:3]:
                self.attention_card.addWidget(
                    QLabel(f"⚠  {member.PlayerName}: role / assignment needed")
                )
            for member in inactive[:3]:
                self.attention_card.addWidget(
                    QLabel(f"⚠  {member.PlayerName}: {member.Status}")
                )

        tanks = sum(1 for m in self.members if "tank" in m.PrimaryRole.lower())
        healers = sum(1 for m in self.members if "heal" in m.PrimaryRole.lower())
        dds = max(0, len(self.members) - tanks - healers)
        active = sum(1 for m in self.members if m.Status == "Active")
        self.team_card.addWidget(
            QLabel(
                f"Tanks      {tanks}\n"
                f"Healers    {healers}\n"
                f"Damage     {dds}\n"
                f"Active     {active}/{len(self.members)}\n\n"
                "Gear needs and build readiness will appear here as those systems are connected."
            )
        )

    def remove_selected_assignment(self):
        row = self.assignment_table.currentRow()
        if row < 0:
            self.status.warning("Select an assignment to remove.")
            return

        player_item = self.assignment_table.item(row, 0)
        member_id = (
            player_item.data(Qt.ItemDataRole.UserRole)
            if player_item is not None
            else None
        )
        if member_id is None:
            self.status.warning("The selected assignment is not linked to a roster record.")
            return

        player_name = (
            player_item.text().strip() if player_item is not None else "this player"
        )
        confirm = QMessageBox.question(
            self,
            "Remove Assignment",
            (
                f"Archive {player_name or 'this player'} from current planning?\n\n"
                "Their Personnel history, aliases, notes, builds, and old raid references are kept."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.roster_service.archive_member(int(member_id))
            if self.record.model.Id == int(member_id):
                self.record.clear()
            self.refresh()
            self.status.success(
                f"Archived {player_name or 'player'} and removed them from current planning."
            )
        except Exception as exc:
            self.status.error(f"Remove failed: {exc}")

    def load_member(self, member_id: int):
        member = self.roster_service.get_member(member_id)
        if member is not None:
            self.record.load(member)
            aliases = self.identity_service.aliases_for_member(member_id)
            self.record.set_former_gamertags(tuple(alias.alias for alias in aliases))
            self._update_personnel_lifecycle_actions()

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
            for alias in self.record.former_gamertag_values():
                self.identity_service.add_alias(
                    int(new_id),
                    alias,
                    source="former_gamertag",
                )
            self.refresh()
            self.table.select_member_id(new_id)
        except Exception as exc:
            self.status.error(f"Save failed: {exc}")

    def delete_member(self):
        model = self.record.model
        if model.Id is None:
            self.status.warning("Select a roster member to archive.")
            return
        current = self.roster_service.get_member(int(model.Id))
        if current is None:
            self.status.warning("That Personnel record no longer exists.")
            return
        if str(current.Status or "").strip().casefold() == "archived":
            self.status.info("This player is already archived.")
            return
        confirm = QMessageBox.question(
            self,
            "Archive Player",
            (
                f"Archive {current.PlayerName or 'this player'}?\n\n"
                "They will disappear from normal player lists and current raid planning. "
                "Historical records, builds, aliases, and Personnel notes are kept."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.roster_service.archive_member(int(model.Id))
            self.record.clear()
            self.refresh()
            self.status.success(f"Archived {current.PlayerName or 'player'}.")
        except Exception as exc:
            self.status.error(f"Archive failed: {exc}")

    def restore_member(self):
        model = self.record.model
        if model.Id is None:
            self.status.warning("Select an archived player to restore.")
            return
        try:
            restored = self.roster_service.restore_member(int(model.Id))
            self.show_combo.setCurrentText("All Players")
            self.refresh()
            self.table.select_member_id(int(model.Id))
            self.status.success(f"Restored {restored.PlayerName or 'player'} to Active.")
        except Exception as exc:
            self.status.error(f"Restore failed: {exc}")

    def delete_member_permanently(self):
        model = self.record.model
        if model.Id is None:
            self.status.warning("Select an archived player to delete permanently.")
            return
        current = self.roster_service.get_member(int(model.Id))
        if current is None:
            self.status.warning("That Personnel record no longer exists.")
            return
        if str(current.Status or "").strip().casefold() != "archived":
            self.status.warning("Archive the player before permanent deletion.")
            return
        if not confirm_destructive_action(
            self,
            title="Delete Archived Player Permanently",
            object_label=f'Permanently delete "{current.PlayerName or "this player"}"?',
            impact=(
                "This removes the Personnel record, current team memberships, aliases, "
                "and roster assignment state. Saved builds and historical Raid Plan snapshots "
                "are kept. A recoverable database snapshot is created first."
            ),
            confirm_text="Delete Permanently",
        ):
            return
        UserSafetySnapshotService().create(
            f"delete-player-{current.Id or current.PlayerName}"
        )
        try:
            self.roster_service.delete_member(int(model.Id))
            self.record.clear()
            self.refresh()
            self.status.success(f"Permanently deleted {current.PlayerName or 'player'}.")
        except Exception as exc:
            self.status.error(f"Permanent delete failed: {exc}")
