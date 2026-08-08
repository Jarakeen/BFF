# ==================================================
# Black Feather Foundry
#
# File:
# ui/settings_page.py
#
# Purpose:
# Foundry Settings.
#
# Configure the Black Feather Foundry,
# OBS integration, archives, and
# collections.
#
# ==================================================

from __future__ import annotations

from pathlib import Path
from ui.theme.roles import ButtonRole
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
)

from ui.components.foundry_header import FoundryHeader
from ui.theme.roles import ButtonRole
from ui.components.foundry_button import FoundryButton
from ui.components.foundry_status_bar import FoundryStatusBar
from widgets.settings_editor import SettingsEditor

from ui.components.foundry_card import FoundryCard

from services.settings_service import SettingsService
from services.obs_websocket_service import ObsWebSocketService


class SettingsPage(QWidget):
    """
    Configure the Foundry.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_services()
        self.build_ui()
        self.connect_signals()

        self.load_settings()

    # --------------------------------------------------
    # Services
    # --------------------------------------------------

    def build_services(self):

        self.settings_service = SettingsService(
            Path("settings.json")
        )

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        self.header = FoundryHeader(
            title="Settings",
            subtitle="Configure the Foundry workspace and services.",
            department="Administration",
        )

        self.editor = SettingsEditor()

        self.status = FoundryStatusBar()

        self.save_button = FoundryButton(
            "Save Settings",
            role=ButtonRole.SUCCESS,
        )

        self.reload_button = FoundryButton(
            "Reload",
            role=ButtonRole.SUCCESS,
        )

        self.test_button = FoundryButton(
            "Test OBS",
            role=ButtonRole.SUCCESS,
        )

        #
        # Layout
        #

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        layout.setSpacing(8)

        layout.addWidget(
            self.header
        )

        editor = FoundryCard(
            "Foundry Settings"
        )

        editor.addWidget(
            self.editor
        )

        layout.addWidget(
            editor
        )

        buttons = QHBoxLayout()

        buttons.addWidget(
            self.save_button
        )

        buttons.addWidget(
            self.reload_button
        )

        buttons.addWidget(
            self.test_button
        )

        buttons.addStretch()

        layout.addLayout(
            buttons
        )

        layout.addWidget(
            self.status
        )

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.save_button.clicked.connect(
            self.save_settings
        )

        self.reload_button.clicked.connect(
            self.load_settings
        )

        self.test_button.clicked.connect(
            self.test_obs
        )

        #
        # Browse Buttons
        #

        self.editor.workspace_browse.clicked.connect(
            self.browse_workspace
        )

        self.editor.archive_browse.clicked.connect(
            self.browse_archive
        )

        self.editor.counters_browse.clicked.connect(
            self.browse_counters
        )

        self.editor.achievement_data_browse.clicked.connect(
            self.browse_achievement_data
        )

        self.editor.progress_browse.clicked.connect(
            self.browse_progress
        )

    # --------------------------------------------------
    # Loading
    # --------------------------------------------------

    def load_settings(self):

        settings = self.settings_service.load()

        self.editor.load_settings(
            settings
        )

        self.status.info(
            "Settings loaded."
        )

    def save_settings(self):

        self.settings_service.save(
            self.editor.settings
        )

        self.status.success(
            "Settings saved."
        )

    # --------------------------------------------------
    # OBS
    # --------------------------------------------------

    def test_obs(self):

        settings = self.editor.settings

        try:

            ObsWebSocketService(
                host=settings["ObsWebSocketHost"],
                port=settings["ObsWebSocketPort"],
                password=settings["ObsWebSocketPassword"],
            )

            self.status.success(
                "OBS settings look valid."
            )

        except Exception as ex:

            self.status.error(
                str(ex)
            )

    # --------------------------------------------------
    # Browse Helpers
    # --------------------------------------------------

    def browse_workspace(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Foundry Workspace",
        )

        if folder:

            self.editor.workspace.setText(
                folder
            )

    def browse_archive(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Archive Folder",
        )

        if folder:

            self.editor.archive_folder.setText(
                folder
            )

    def browse_counters(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Counters Folder",
        )

        if folder:

            self.editor.counters_folder.setText(
                folder
            )

    def browse_achievement_data(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Achievement Data",
            "",
            "JSON (*.json)",
        )

        if filename:

            self.editor.achievement_data.setText(
                filename
            )

    def browse_progress(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Achievement Progress",
            "",
            "JSON (*.json)",
        )

        if filename:

            self.editor.achievement_progress.setText(
                filename
            )