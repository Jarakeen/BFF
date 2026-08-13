# ==================================================
# Black Feather Foundry
#
# File:
# ui/builds_page.py
#
# Purpose:
# Builds Desk.
#
# Player character build sheets for up to 12 raid team
# members -- identity, gear, CP, skills, consumables, and
# per-boss alternate loadouts for a trial. Exports to CSV
# or PDF for sharing outside the Foundry.
#
# Wired to the sidebar's existing "Builds" nav entry
# (Raid Operations > Builds, page key "console:2").
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QMessageBox,
    QFileDialog,
)

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_tabs import FoundryTabs
from widgets.build_dashboard import BuildDashboard
from ui.foundry_page import FoundryPage

from widgets.build_editor import BuildEditor

from models.build_model import BuildRoster, PlayerBuild

from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.reference_data_service import ReferenceDataService
from services.settings_service import SettingsService


class BuildsPage(FoundryPage):
    """
    Builds Desk -- one tab per raid team member's character
    build, with per-boss alternate loadouts and CSV/PDF
    export.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_services()

        self._suppress_tab_rebuild = False

        self.build_ui()
        self.connect_signals()

        self.refresh()

    # --------------------------------------------------
    # Services
    # --------------------------------------------------

    def build_services(self):

        data_dir = Path(__file__).resolve().parents[1] / "data"

        self.database = EsoDatabase(data_dir / "eso.db")

        self.reference = ReferenceDataService(self.database)

        self.build_service = BuildService(data_dir / "builds.json")

        self.settings_service = SettingsService(Path("settings.json"))

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        self.header = FoundryHeader(
            title="Builds",
            subtitle="Character build sheets for the raid team, with per-boss alternates.",
            department="Planning",
        )

        self.set_header(self.header)

        #
        # Tab strip
        #
        # Rebuilt each time a member is added/removed or a
        # name changes, since FoundryTabs takes a fixed
        # label list at construction time.
        #

        self.tab_row = QHBoxLayout()

        self.tab_row.setSpacing(8)

        self.tabs_container = QHBoxLayout()

        self.tabs_widget = None

        self.add_member_button = FoundryButton(
            "+ Add Member",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        self.remove_member_button = FoundryButton(
            "Remove Member",
            role=ButtonRole.DANGER,
            compact=True,
        )

        self.tab_row.addLayout(self.tabs_container, 1)
        self.tab_row.addWidget(self.add_member_button)
        self.tab_row.addWidget(self.remove_member_button)

        self.add_workspace_layout(self.tab_row)

        #
        # Per-member editors
        #

        self.stack = QStackedWidget()

        self.editors: list[BuildEditor] = []

        self.add_workspace(self.stack)

        #
        # Actions
        #

        self.actions = QWidget()

        actions_layout = QHBoxLayout(self.actions)

        actions_layout.setContentsMargins(0, 0, 0, 0)

        self.save_button = FoundryButton(
            "Save Builds",
            role=ButtonRole.SUCCESS,
        )

        self.export_csv_button = FoundryButton(
            "Export CSV...",
            role=ButtonRole.SECONDARY,
        )

        self.export_pdf_button = FoundryButton(
            "Export PDF...",
            role=ButtonRole.SECONDARY,
        )

        actions_layout.addWidget(self.save_button)
        actions_layout.addWidget(self.export_csv_button)
        actions_layout.addWidget(self.export_pdf_button)
        actions_layout.addStretch()

        self.set_actions(self.actions)

        #
        # Status
        #

        self.status = FoundryStatusBar()

        self.set_status(self.status)

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.add_member_button.clicked.connect(self.add_member)

        self.remove_member_button.clicked.connect(self.remove_current_member)

        self.save_button.clicked.connect(self.save_builds)

        self.export_csv_button.clicked.connect(self.export_csv)

        self.export_pdf_button.clicked.connect(self.export_pdf)

    # --------------------------------------------------
    # Loading
    # --------------------------------------------------

    def refresh(self):

        try:

            roster = self.build_service.load()

        except Exception as exc:

            self.status.error(f"Failed to load builds: {exc}")

            roster = BuildRoster()

        self._load_roster(roster)

        self.status.info(f"{len(roster.Members)} build(s) loaded.")

    def _load_roster(self, roster: BuildRoster):

        while self.stack.count():

            widget = self.stack.widget(0)

            self.stack.removeWidget(widget)

            widget.deleteLater()

        self.editors = []

        for member in roster.Members:

            editor = self._new_editor()

            editor.load(member)

            self.editors.append(editor)

            dashboard = BuildDashboard(editor)
            self.stack.addWidget(dashboard)

        self._rebuild_tabs()

    def _new_editor(self) -> BuildEditor:

        editor = BuildEditor(
            race_choices=self.reference.list_race_names(),
            set_choices=self.reference.list_gear_set_names(),
            skill_choices=self.reference.list_skill_names(),
            cp_choices=self.reference.list_champion_point_names(),
        )

        editor.nameChanged.connect(self._rebuild_tabs)

        return editor

    # --------------------------------------------------
    # Tabs
    # --------------------------------------------------

    def _rebuild_tabs(self, *_args):

        if self._suppress_tab_rebuild:
            return

        current = self.stack.currentIndex()

        if current < 0:
            current = 0

        while self.tabs_container.count():

            item = self.tabs_container.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        labels = [
            editor.model.display_label(f"Member {i + 1}")
            for i, editor in enumerate(self.editors)
        ]

        if not labels:
            return

        self.tabs_widget = FoundryTabs(
            labels,
            selected=labels[current] if current < len(labels) else labels[0],
        )

        self.tabs_widget.tabChanged.connect(self._select_tab_by_label)

        self.tabs_container.addWidget(self.tabs_widget)

        self.remove_member_button.setEnabled(len(self.editors) > 1)

        self.add_member_button.setEnabled(
            len(self.editors) < BuildRoster.MAX_MEMBERS
        )

    def _select_tab_by_label(self, label: str):

        for i, editor in enumerate(self.editors):

            if editor.model.display_label(f"Member {i + 1}") == label:

                self.stack.setCurrentIndex(i)

                return

    # --------------------------------------------------
    # Member management
    # --------------------------------------------------

    def add_member(self):

        if len(self.editors) >= BuildRoster.MAX_MEMBERS:

            self.status.warning(
                f"Builds is limited to {BuildRoster.MAX_MEMBERS} members."
            )

            return

        editor = self._new_editor()

        self.editors.append(editor)

        dashboard = BuildDashboard(editor)
        self.stack.addWidget(dashboard)
        self.stack.setCurrentWidget(editor)

        self._rebuild_tabs()

        self.status.info("New member added. Fill in their build and Save.")

    def remove_current_member(self):

        if len(self.editors) <= 1:

            self.status.warning("At least one member is required.")

            return

        index = self.stack.currentIndex()

        if index < 0:
            return

        editor = self.editors[index]

        label = editor.model.display_label(f"Member {index + 1}")

        confirm = QMessageBox.question(
            self,
            "Remove Member",
            f"Remove the build for {label}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.editors.pop(index)

        self.stack.removeWidget(editor)

        editor.deleteLater()

        self._rebuild_tabs()

        self.status.success(f"Removed {label}.")

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    def _current_roster(self) -> BuildRoster:

        return BuildRoster(
            Members=[editor.model for editor in self.editors]
        )

    def save_builds(self):

        try:

            self.build_service.save(self._current_roster())

            self.status.success("Builds saved.")

        except Exception as exc:

            self.status.error(f"Save failed: {exc}")

    # --------------------------------------------------
    # Export
    # --------------------------------------------------

    def _default_export_folder(self) -> str:

        try:

            settings = self.settings_service.load()

            return settings.get("BuildsExportFolder", "") or ""

        except Exception:
            return ""

    def export_csv(self):

        folder = self._default_export_folder()

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Builds as CSV",
            str(Path(folder) / "raid_builds.csv") if folder else "raid_builds.csv",
            "CSV Files (*.csv)",
        )

        if not filename:
            return

        try:

            self.build_service.export_csv(self._current_roster(), Path(filename))

            self.status.success(f"Exported CSV to {filename}")

        except Exception as exc:

            self.status.error(f"CSV export failed: {exc}")

    def export_pdf(self):

        folder = self._default_export_folder()

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Builds as PDF",
            str(Path(folder) / "raid_builds.pdf") if folder else "raid_builds.pdf",
            "PDF Files (*.pdf)",
        )

        if not filename:
            return

        try:

            self.build_service.export_pdf(self._current_roster(), Path(filename))

            self.status.success(f"Exported PDF to {filename}")

        except Exception as exc:

            self.status.error(f"PDF export failed: {exc}")
