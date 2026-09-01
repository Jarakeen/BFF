# ==================================================
# Black Feather Foundry
#
# File:
# ui/settings_page.py
#
# Purpose:
# Foundry Settings.
#
# A two-column settings console inspired by the Field
# Office wireframe while preserving the existing settings
# keys and services.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from services.obs_websocket_service import ObsWebSocketService
from services.settings_service import SettingsService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar


class SettingsPage(QWidget):
    """Field Office settings console."""

    SECTIONS = (
        ("⚙", "General"),
        ("⌘", "Integrations"),
        ("▣", "Archive"),
        ("▤", "Broadcast"),
        ("♢", "Notifications"),
        ("⌁", "Appearance"),
        ("⚒", "Advanced"),
        ("ⓘ", "About & Credits"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_service = SettingsService(Path("settings.json"))
        self._loaded_settings: dict = {}
        self._section_buttons: list[QPushButton] = []

        self._build_ui()
        self._connect_signals()
        self.load_settings()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Settings",
            subtitle="Configure Foundry Dock to fit your workflow.",
            department="Administration",
        )

        self.status = FoundryStatusBar()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)
        root.addWidget(self.header)

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        # Left settings rail
        rail = QFrame()
        rail.setProperty("settingsRail", True)
        rail.setFixedWidth(190)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(8, 8, 8, 8)
        rail_layout.setSpacing(4)

        self.stack = QStackedWidget()

        page_builders = (
            self._general_page,
            self._integrations_page,
            self._archive_page,
            self._broadcast_page,
            self._notifications_page,
            self._appearance_page,
            self._advanced_page,
            self._about_page,
        )

        for index, ((icon, label), builder) in enumerate(zip(self.SECTIONS, page_builders)):
            button = QPushButton(f"{icon}   {label}")
            button.setCheckable(True)
            button.setProperty("settingsNav", True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, i=index: self._show_section(i))
            rail_layout.addWidget(button)
            self._section_buttons.append(button)
            self.stack.addWidget(builder())

        rail_layout.addStretch(1)
        body.addWidget(rail, 0)

        # Main content + right utility column
        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.stack, 3)

        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        right_column.addWidget(self._integration_status_card())
        right_column.addWidget(self._data_management_card())
        right_column.addStretch(1)
        content.addLayout(right_column, 2)

        body.addLayout(content, 1)
        root.addWidget(self.status)

        self._show_section(0)

    def _page_shell(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        card = FoundryCard(title.upper())
        layout.addWidget(card)
        layout.addStretch(1)
        return page, card.body_layout

    @staticmethod
    def _browse_row(edit: QLineEdit, button: QPushButton) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(edit, 1)
        layout.addWidget(button)
        return widget

    @staticmethod
    def _muted_note(text: str) -> QLabel:
        note = QLabel(text)
        note.setWordWrap(True)
        note.setProperty("muted", True)
        note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return note

    def _general_page(self) -> QWidget:
        page, layout = self._page_shell("General Settings")
        form = QFormLayout()
        form.setSpacing(9)

        self.workspace = QLineEdit()
        self.workspace_browse = QPushButton("Browse…")
        form.addRow("Foundry Workspace", self._browse_row(self.workspace, self.workspace_browse))

        self.builds_export_folder = QLineEdit()
        self.builds_export_browse = QPushButton("Browse…")
        form.addRow("Default Builds Export", self._browse_row(self.builds_export_folder, self.builds_export_browse))

        layout.addLayout(form)

        note = QLabel("General application preferences will live here as the UX branch grows.")
        note.setWordWrap(True)
        note.setProperty("muted", True)
        layout.addWidget(note)
        return page

    def _integrations_page(self) -> QWidget:
        page, layout = self._page_shell("Integrations")
        form = QFormLayout()
        form.setSpacing(9)

        self.obs_host = QLineEdit()
        self.obs_port = QLineEdit()
        self.obs_password = QLineEdit()
        self.obs_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.eso_logs_client_id = QLineEdit()
        self.eso_logs_client_secret = QLineEdit()
        self.eso_logs_client_secret.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("OBS Host", self.obs_host)
        form.addRow("OBS Port", self.obs_port)
        form.addRow("OBS Password", self.obs_password)
        form.addRow("ESO Logs Client ID", self.eso_logs_client_id)
        form.addRow("ESO Logs Client Secret", self.eso_logs_client_secret)
        layout.addLayout(form)

        self.test_obs_button = QPushButton("Test OBS Connection")
        layout.addWidget(self.test_obs_button)
        return page

    def _archive_page(self) -> QWidget:
        page, layout = self._page_shell("Archive")
        form = QFormLayout()
        form.setSpacing(9)

        self.archive_folder = QLineEdit()
        self.archive_browse = QPushButton("Browse…")
        self.counters_folder = QLineEdit()
        self.counters_browse = QPushButton("Browse…")

        form.addRow("Archive Folder", self._browse_row(self.archive_folder, self.archive_browse))
        form.addRow("Counters Folder", self._browse_row(self.counters_folder, self.counters_browse))
        layout.addLayout(form)
        return page

    def _broadcast_page(self) -> QWidget:
        page, layout = self._page_shell("Broadcast")
        form = QFormLayout()
        form.setSpacing(9)

        self.brb_scene = QLineEdit()
        self.end_scene = QLineEdit()
        form.addRow("BRB Scene", self.brb_scene)
        form.addRow("End Scene", self.end_scene)
        layout.addLayout(form)

        placeholder = FoundryCard("Broadcast Tools")
        placeholder.addWidget(QLabel("Broadcast visibility and workflow controls will live here."))
        layout.addWidget(placeholder)
        return page

    def _notifications_page(self) -> QWidget:
        page, layout = self._page_shell("Notifications")
        placeholder = QLabel("Notification preferences have not been wired yet.")
        placeholder.setWordWrap(True)
        layout.addWidget(placeholder)
        return page

    def _appearance_page(self) -> QWidget:
        page, layout = self._page_shell("Appearance")
        placeholder = QLabel("Theme, density, and display preferences will live here.")
        placeholder.setWordWrap(True)
        layout.addWidget(placeholder)
        return page

    def _advanced_page(self) -> QWidget:
        page, layout = self._page_shell("Advanced")
        form = QFormLayout()
        form.setSpacing(9)

        self.achievement_data = QLineEdit()
        self.achievement_data_browse = QPushButton("Browse…")
        self.achievement_progress = QLineEdit()
        self.progress_browse = QPushButton("Browse…")

        form.addRow("Achievement Data", self._browse_row(self.achievement_data, self.achievement_data_browse))
        form.addRow("Achievement Progress", self._browse_row(self.achievement_progress, self.progress_browse))
        layout.addLayout(form)
        return page

    def _about_page(self) -> QWidget:
        page, layout = self._page_shell("About & Credits")

        identity = FoundryCard("BLACK FEATHER FOUNDRY")
        identity.addWidget(
            self._muted_note(
                "Foundry Dock is an independent companion application built for personal ESO "
                "research, planning, recordkeeping, and broadcast workflows."
            )
        )
        copyright_label = QLabel("© 2026 Jarakeen. All rights reserved.")
        copyright_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        identity.addWidget(copyright_label)
        layout.addWidget(identity)

        independence = FoundryCard("INDEPENDENT PROJECT")
        independence.addWidget(
            self._muted_note(
                "Black Feather Foundry is not affiliated with, endorsed by, sponsored by, or "
                "approved by ZeniMax Media Inc. or Bethesda Softworks. The Elder Scrolls Online "
                "and related names, marks, characters, artwork, and game content remain the "
                "property of their respective owners."
            )
        )
        layout.addWidget(independence)

        sources = FoundryCard("DATA & SOURCES")
        sources.addWidget(
            self._muted_note(
                "Game facts and third-party reference material retain their original ownership "
                "and licensing. Foundry Dock records source provenance where available and does "
                "not claim ownership of ESO game data or third-party authored material."
            )
        )
        sources.addWidget(
            self._muted_note(
                "Original application code, interface design, documentation, workflows, and "
                "original written material are part of the Black Feather Foundry project."
            )
        )
        layout.addWidget(sources)

        closing = QLabel("Leave better records.")
        closing.setProperty("muted", True)
        closing.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(closing)
        return page

    def _integration_status_card(self) -> FoundryCard:
        card = FoundryCard("INTEGRATION STATUS")
        self.integration_labels = {}
        for key, title in (
            ("obs", "OBS Studio"),
            ("websocket", "WebSocket Server"),
            ("archive", "Archive Folder"),
            ("sheets", "Google Sheets"),
            ("ai", "AI Service"),
        ):
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(QLabel(title))
            layout.addStretch(1)
            state = QLabel("●  Not checked")
            state.setProperty("integrationState", True)
            layout.addWidget(state)
            card.addWidget(row)
            self.integration_labels[key] = state
        return card

    def _data_management_card(self) -> FoundryCard:
        card = FoundryCard("DATA MANAGEMENT")
        top = QHBoxLayout()
        bottom = QHBoxLayout()

        self.backup_button = QPushButton("▣  Backup Data")
        self.export_button = QPushButton("▤  Export Settings")
        self.import_button = QPushButton("▧  Import Settings")
        self.reset_button = QPushButton("↺  Reset to Defaults")
        self.reset_button.setProperty("danger", True)

        top.addWidget(self.backup_button)
        top.addWidget(self.export_button)
        bottom.addWidget(self.import_button)
        bottom.addWidget(self.reset_button)
        card.addLayout(top)
        card.addLayout(bottom)
        return card

    # --------------------------------------------------
    # Signals / state
    # --------------------------------------------------

    def _connect_signals(self):
        self.workspace_browse.clicked.connect(lambda: self._browse_folder(self.workspace, "Foundry Workspace"))
        self.builds_export_browse.clicked.connect(lambda: self._browse_folder(self.builds_export_folder, "Default Builds Export Folder"))
        self.archive_browse.clicked.connect(lambda: self._browse_folder(self.archive_folder, "Archive Folder"))
        self.counters_browse.clicked.connect(lambda: self._browse_folder(self.counters_folder, "Counters Folder"))
        self.achievement_data_browse.clicked.connect(lambda: self._browse_file(self.achievement_data, "Achievement Data", "JSON (*.json)"))
        self.progress_browse.clicked.connect(lambda: self._browse_file(self.achievement_progress, "Achievement Progress", "JSON (*.json)"))
        self.test_obs_button.clicked.connect(self.test_obs)

        self.save_button = QPushButton("Save Settings")
        self.save_button.setProperty("primary", True)
        self.header.add_context_widget(self.save_button)
        self.save_button.clicked.connect(self.save_settings)

        self.reload_button = QPushButton("Reload")
        self.header.add_context_widget(self.reload_button)
        self.reload_button.clicked.connect(self.load_settings)

    def _show_section(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self._section_buttons):
            button.setChecked(i == index)

    def _browse_folder(self, target: QLineEdit, title: str):
        folder = QFileDialog.getExistingDirectory(self, title)
        if folder:
            target.setText(folder)

    def _browse_file(self, target: QLineEdit, title: str, file_filter: str):
        filename, _ = QFileDialog.getOpenFileName(self, title, "", file_filter)
        if filename:
            target.setText(filename)

    # --------------------------------------------------
    # Persistence
    # --------------------------------------------------

    def load_settings(self):
        self._loaded_settings = self.settings_service.load()
        s = self._loaded_settings

        self.workspace.setText(s.get("BffRoot", ""))
        self.builds_export_folder.setText(s.get("BuildsExportFolder", ""))
        self.obs_host.setText(s.get("ObsWebSocketHost", ""))
        self.obs_port.setText(str(s.get("ObsWebSocketPort", 4455)))
        self.obs_password.setText(s.get("ObsWebSocketPassword", ""))
        self.eso_logs_client_id.setText(s.get("EsoLogsClientId", ""))
        self.eso_logs_client_secret.setText(s.get("EsoLogsClientSecret", ""))
        self.archive_folder.setText(s.get("ArchiveFolder", ""))
        self.counters_folder.setText(s.get("CountersFolder", ""))
        self.brb_scene.setText(s.get("BrbSceneName", "BRB"))
        self.end_scene.setText(s.get("EndOfStreamSceneName", s.get("EndSceneName", "Ending")))
        self.achievement_data.setText(s.get("AchievementData", ""))
        self.achievement_progress.setText(s.get("AchievementProgress", s.get("AchievementProgressPath", "")))

        archive_ok = bool(self.archive_folder.text().strip())
        self.integration_labels["archive"].setText("●  Ready" if archive_ok else "●  Not configured")
        self.integration_labels["obs"].setText("●  Configured" if self.obs_host.text().strip() else "●  Not configured")
        self.integration_labels["websocket"].setText("●  Configured" if self.obs_host.text().strip() else "●  Not configured")
        self.integration_labels["sheets"].setText("●  Not checked")
        self.integration_labels["ai"].setText("●  Not configured")
        self.status.info("Settings loaded.")

    def save_settings(self):
        settings = dict(self._loaded_settings)
        settings.update(
            {
                "BffRoot": self.workspace.text().strip(),
                "BuildsExportFolder": self.builds_export_folder.text().strip(),
                "ObsWebSocketHost": self.obs_host.text().strip(),
                "ObsWebSocketPort": int(self.obs_port.text().strip() or 4455),
                "ObsWebSocketPassword": self.obs_password.text(),
                "EsoLogsClientId": self.eso_logs_client_id.text().strip(),
                "EsoLogsClientSecret": self.eso_logs_client_secret.text(),
                "ArchiveFolder": self.archive_folder.text().strip(),
                "CountersFolder": self.counters_folder.text().strip(),
                "BrbSceneName": self.brb_scene.text().strip(),
                "EndOfStreamSceneName": self.end_scene.text().strip(),
            }
        )
        self.settings_service.save(settings)
        self._loaded_settings = settings
        self.status.success("Settings saved.")

    def test_obs(self):
        try:
            ObsWebSocketService(
                host=self.obs_host.text().strip() or "127.0.0.1",
                port=int(self.obs_port.text().strip() or 4455),
                password=self.obs_password.text(),
            )
        except Exception as exc:
            self.integration_labels["obs"].setText("●  Error")
            self.integration_labels["websocket"].setText("●  Error")
            self.status.error(str(exc))
            return

        self.integration_labels["obs"].setText("●  Connected")
        self.integration_labels["websocket"].setText("●  Connected")
        self.status.success("OBS settings look valid.")
