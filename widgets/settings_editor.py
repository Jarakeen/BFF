# ==================================================
# Black Feather Foundry
#
# File:
# widgets/settings_editor.py
#
# Purpose:
# Editor for Foundry settings.
#
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QTabWidget,
)


class SettingsEditor(QWidget):
    """
    Tabbed editor for Foundry settings.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Workspace
        #

        self.workspace = QLineEdit()

        self.workspace_browse = QPushButton(
            "Browse..."
        )

        self.update_paths = QPushButton(
            "Update Paths"
        )

        #
        # OBS
        #

        self.obs_host = QLineEdit()

        self.obs_port = QLineEdit()

        self.obs_password = QLineEdit()

        self.obs_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        self.test_connection = QPushButton(
            "Test Connection"
        )

        #
        # Broadcast
        #

        self.brb_scene = QLineEdit()

        self.end_scene = QLineEdit()

        #
        # Archives
        #

        self.archive_folder = QLineEdit()

        self.archive_browse = QPushButton(
            "Browse..."
        )

        self.counters_folder = QLineEdit()

        self.counters_browse = QPushButton(
            "Browse..."
        )

        #
        # Collections
        #

        self.achievement_data = QLineEdit()

        self.achievement_data_browse = QPushButton(
            "Browse..."
        )

        self.achievement_progress = QLineEdit()

        self.progress_browse = QPushButton(
            "Browse..."
        )

        #
        # ESO Logs (Capabilities page)
        #

        self.eso_logs_client_id = QLineEdit()

        self.eso_logs_client_secret = QLineEdit()

        self.eso_logs_client_secret.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        #
        # Builds export
        #

        self.builds_export_folder = QLineEdit()

        self.builds_export_browse = QPushButton(
            "Browse..."
        )

        #
        # Tabs
        #

        tabs = QTabWidget()

        #
        # General
        #

        general = QWidget()

        general_form = QFormLayout(general)

        workspace = QHBoxLayout()

        workspace.addWidget(
            self.workspace
        )

        workspace.addWidget(
            self.workspace_browse
        )

        general_form.addRow(
            "Foundry Workspace",
            workspace,
        )

        general_form.addRow(
            "",
            self.update_paths,
        )

        tabs.addTab(
            general,
            "General",
        )

        #
        # Broadcast
        #

        broadcast = QWidget()

        form = QFormLayout(broadcast)

        form.addRow(
            "BRB Scene",
            self.brb_scene,
        )

        form.addRow(
            "End Scene",
            self.end_scene,
        )

        tabs.addTab(
            broadcast,
            "Broadcast",
        )

        #
        # OBS
        #

        obs = QWidget()

        form = QFormLayout(obs)

        form.addRow(
            "Host",
            self.obs_host,
        )

        form.addRow(
            "Port",
            self.obs_port,
        )

        form.addRow(
            "Password",
            self.obs_password,
        )

        form.addRow(
            "",
            self.test_connection,
        )

        tabs.addTab(
            obs,
            "OBS",
        )

        #
        # Archives
        #

        archives = QWidget()

        form = QFormLayout(archives)

        archive = QHBoxLayout()

        archive.addWidget(
            self.archive_folder
        )

        archive.addWidget(
            self.archive_browse
        )

        counters = QHBoxLayout()

        counters.addWidget(
            self.counters_folder
        )

        counters.addWidget(
            self.counters_browse
        )

        form.addRow(
            "Archive Folder",
            archive,
        )

        form.addRow(
            "Counters Folder",
            counters,
        )

        tabs.addTab(
            archives,
            "Archives",
        )

        #
        # Collections
        #

        collections = QWidget()

        form = QFormLayout(collections)

        data = QHBoxLayout()

        data.addWidget(
            self.achievement_data
        )

        data.addWidget(
            self.achievement_data_browse
        )

        progress = QHBoxLayout()

        progress.addWidget(
            self.achievement_progress
        )

        progress.addWidget(
            self.progress_browse
        )

        form.addRow(
            "Achievement Data",
            data,
        )

        form.addRow(
            "Progress File",
            progress,
        )

        tabs.addTab(
            collections,
            "Collections",
        )

        #
        # ESO Logs
        #

        eso_logs = QWidget()

        form = QFormLayout(eso_logs)

        form.addRow(
            "Client ID",
            self.eso_logs_client_id,
        )

        form.addRow(
            "Client Secret",
            self.eso_logs_client_secret,
        )

        note = QPushButton(
            "Get credentials at esologs.com/api/clients"
        )

        note.setFlat(True)

        note.setEnabled(False)

        form.addRow(
            "",
            note,
        )

        tabs.addTab(
            eso_logs,
            "ESO Logs",
        )

        #
        # Builds
        #

        builds = QWidget()

        form = QFormLayout(builds)

        export_folder = QHBoxLayout()

        export_folder.addWidget(
            self.builds_export_folder
        )

        export_folder.addWidget(
            self.builds_export_browse
        )

        form.addRow(
            "Default Export Folder",
            export_folder,
        )

        tabs.addTab(
            builds,
            "Builds",
        )

        #
        # Layout
        #

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.addWidget(
            tabs
        )

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def load_settings(self, settings: dict):
        """
        Populate the editor from a settings dictionary.
        """

        self.workspace.setText(
            settings.get("BffRoot", "")
        )

        self.obs_host.setText(
            settings.get("ObsWebSocketHost", "")
        )

        self.obs_port.setText(
            str(
                settings.get(
                    "ObsWebSocketPort",
                    ""
                )
            )
        )

        self.obs_password.setText(
            settings.get(
                "ObsWebSocketPassword",
                ""
            )
        )

        self.brb_scene.setText(
            settings.get(
                "BrbSceneName",
                ""
            )
        )

        self.end_scene.setText(
            settings.get(
                "EndSceneName",
                ""
            )
        )

        self.archive_folder.setText(
            settings.get(
                "ArchiveFolder",
                ""
            )
        )

        self.counters_folder.setText(
            settings.get(
                "CountersFolder",
                ""
            )
        )

        self.achievement_data.setText(
            settings.get(
                "AchievementData",
                ""
            )
        )

        self.achievement_progress.setText(
            settings.get(
                "AchievementProgress",
                ""
            )
        )

        self.eso_logs_client_id.setText(
            settings.get(
                "EsoLogsClientId",
                ""
            )
        )

        self.eso_logs_client_secret.setText(
            settings.get(
                "EsoLogsClientSecret",
                ""
            )
        )

        self.builds_export_folder.setText(
            settings.get(
                "BuildsExportFolder",
                ""
            )
        )

    @property
    def settings(self) -> dict:
        """
        Return the current settings.
        """

        return {
            "EsoLogsClientId": self.eso_logs_client_id.text().strip(),

            "EsoLogsClientSecret": self.eso_logs_client_secret.text(),

            "BuildsExportFolder": self.builds_export_folder.text().strip(),

            "BffRoot": self.workspace.text(),

            "ObsWebSocketHost": self.obs_host.text(),

            "ObsWebSocketPort": int(
                self.obs_port.text() or 4455
            ),

            "ObsWebSocketPassword": self.obs_password.text(),

            "BrbSceneName": self.brb_scene.text(),

            "EndSceneName": self.end_scene.text(),

            "ArchiveFolder": self.archive_folder.text(),

            "CountersFolder": self.counters_folder.text(),

            "AchievementData": self.achievement_data.text(),

            "AchievementProgress": self.achievement_progress.text(),
        }