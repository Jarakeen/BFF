# ui/settings_page.py

from __future__ import annotations


import json
import random
from datetime import datetime
from pathlib import Path
import re

from services.achievement_progress_service import AchievementProgressService
from services.archive_service import ArchiveService
from services.eso_data_service import EsoAchievementDataService
from services.google_sheets_service import GoogleSheetsNotConfigured, GoogleSheetsService
from services.incident_json_service import IncidentJsonService
from services.json_service import JsonService
from services.narrator_service import NarratorService
from services.obs_websocket_service import ObsWebSocketService
from services.reference_service import ReferenceLibrary
from services.settings_service import SettingsService
from services.stream_event_service import StreamEventService
from services.tamriel_calendar import get_tamriel_date
from services.validation_service import ValidationService
from services.ai_service import AIService


from PySide6.QtCore import Qt, QTimer, QAbstractTableModel, QModelIndex, QSize
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableView,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form = QFormLayout()
        self.bff_root_edit = QLineEdit()
        self.current_path_edit = QLineEdit()
        self.current_incident_edit = QLineEdit()
        self.field_note_counter_edit = QLineEdit()
        self.counters_folder_edit = QLineEdit()
        self.archive_folder_edit = QLineEdit()
        self.weather_folder_edit = QLineEdit()
        self.brb_scene_edit = QLineEdit()
        self.end_of_stream_scene_edit = QLineEdit()
        self.obs_websocket_host_edit = QLineEdit()
        self.obs_websocket_port_edit = QLineEdit()
        self.obs_websocket_password_edit = QLineEdit()
        self.obs_websocket_password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        settings = self.settings_service.load()
        self.bff_root_edit.setText(settings["BffRoot"])
        self.current_path_edit.setText(settings["CurrentExpeditionPath"])
        self.current_incident_edit.setText(settings["CurrentIncidentPath"])
        self.field_note_counter_edit.setText(settings["FieldNoteCounterPath"])
        self.counters_folder_edit.setText(settings["CountersFolder"])
        self.archive_folder_edit.setText(settings["ArchiveFolder"])
        self.weather_folder_edit.setText(settings["WeatherFolder"])
        self.brb_scene_edit.setText(settings["BrbSceneName"])
        self.end_of_stream_scene_edit.setText(settings["EndOfStreamSceneName"])
        self.ai_service = AIService(Path(settings["BffRoot"]))
        self.obs_websocket_host_edit.setText(settings["ObsWebSocketHost"])
        self.obs_websocket_port_edit.setText(str(settings["ObsWebSocketPort"]))
        self.obs_websocket_password_edit.setText(settings["ObsWebSocketPassword"])

        form.addRow("BFF Workspace", self.bff_root_edit)    
        form.addRow("CurrentExpedition.json", self.current_path_edit)
        form.addRow("CurrentIncident.json", self.current_incident_edit)
        form.addRow("FieldNoteCounter.txt", self.field_note_counter_edit)
        form.addRow("Counters Folder", self.counters_folder_edit)
        form.addRow("Archive Folder", self.archive_folder_edit)
        form.addRow("Weather Folder", self.weather_folder_edit)
        form.addRow("BRB Scene Name (must match OBS exactly)", self.brb_scene_edit)
        form.addRow("End of Stream Scene Name (must match OBS exactly)", self.end_of_stream_scene_edit)
        form.addRow("OBS WebSocket Host", self.obs_websocket_host_edit)
        form.addRow("OBS WebSocket Port", self.obs_websocket_port_edit)
        form.addRow("OBS WebSocket Password", self.obs_websocket_password_edit)

        save_settings_btn = QPushButton("Save Settings")
        save_settings_btn.clicked.connect(self.save_settings)

        rebuild_db_btn = QPushButton("Rebuild Database")
        rebuild_db_btn.clicked.connect(self.rebuild_database)

        button_row = QHBoxLayout()
        button_row.addWidget(save_settings_btn)
        button_row.addWidget(rebuild_db_btn)
        button_row.addStretch(1)

        layout.addLayout(form)
        layout.addLayout(button_row)
        return page

def save_settings(self) -> None:
        existing = self.settings_service.load()
        settings = {
            "BffRoot": self.bff_root_edit.text(),
            "CurrentExpeditionPath": self.current_path_edit.text(),
            "CurrentIncidentPath": self.current_incident_edit.text(),
            "FieldNoteCounterPath": self.field_note_counter_edit.text(),
            "CountersFolder": self.counters_folder_edit.text(),
            "ArchiveFolder": self.archive_folder_edit.text(),
            "WeatherFolder": self.weather_folder_edit.text(),
            "BrbSceneName": self.brb_scene_edit.text(),
            "EndOfStreamSceneName": self.end_of_stream_scene_edit.text(),
            "ObsWebSocketHost": self.obs_websocket_host_edit.text(),
            "ObsWebSocketPort": int(self.obs_websocket_port_edit.text() or 4455),
            "ObsWebSocketPassword": self.obs_websocket_password_edit.text(),
            "StreamEventsPath": existing["StreamEventsPath"],
            "StreamSessionPath": existing["StreamSessionPath"],
            "BossLogPath": existing["BossLogPath"],
            "NarratorContentPath": existing["NarratorContentPath"],
            "AchievementRunDraftPath": existing["AchievementRunDraftPath"],
            "GoogleCredentialsPath": existing["GoogleCredentialsPath"],
            "GoogleSpreadsheetId": existing["GoogleSpreadsheetId"],
            "GoogleSheetsPerson": existing["GoogleSheetsPerson"],
            "AchievementProgressPath": existing["AchievementProgressPath"],
            "MarkerLogPath": existing["MarkerLogPath"],
            "CurrentAchievementRunPath": existing["CurrentAchievementRunPath"],
            "CurrentBroadcastPath": existing["CurrentBroadcastPath"],
            "SessionArchiveFolder": existing["SessionArchiveFolder"],
        }
        self.settings_service.save(settings)
        self.current_path = self._resolve_setting_path(settings["CurrentExpeditionPath"])
        self.current_incident_path = self._resolve_setting_path(settings["CurrentIncidentPath"])
        self.field_note_counter_path = self._resolve_setting_path(settings["FieldNoteCounterPath"])
        self.counters_folder = self._resolve_setting_path(settings["CountersFolder"])
        self.archive_path = self._resolve_setting_path(settings["ArchiveFolder"])
        self.stream_events_path = self._resolve_setting_path(settings["StreamEventsPath"])
        self.stream_session_path = self._resolve_setting_path(settings["StreamSessionPath"])
        self.boss_log_path = self._resolve_setting_path(settings["BossLogPath"])
        self.narrator_content_path = self._resolve_setting_path(settings["NarratorContentPath"])
        self.achievement_draft_path = self._resolve_setting_path(settings["AchievementRunDraftPath"])
        self.google_credentials_path = self._resolve_setting_path(settings["GoogleCredentialsPath"])
        self.google_spreadsheet_id = settings["GoogleSpreadsheetId"]
        self.google_sheets_person = settings["GoogleSheetsPerson"]
        self.achievement_progress_path = self._resolve_setting_path(settings["AchievementProgressPath"])
        self.marker_log_path = self._resolve_setting_path(settings["MarkerLogPath"])
        self.current_achievement_run_path = self._resolve_setting_path(settings["CurrentAchievementRunPath"])
        self.current_broadcast_path = self._resolve_setting_path(settings["CurrentBroadcastPath"])
        self.session_archive_folder = self._resolve_setting_path(settings["SessionArchiveFolder"])
        self.brb_scene_name = settings["BrbSceneName"]
        self.end_of_stream_scene_name = settings["EndOfStreamSceneName"]
        self.obs_websocket_host = settings["ObsWebSocketHost"]
        self.obs_websocket_port = settings["ObsWebSocketPort"]
        self.obs_websocket_password = settings["ObsWebSocketPassword"]
        self.json_service = JsonService(self.current_path)
        self.incident_json_service = IncidentJsonService(self.current_incident_path)
        self.archive_service = ArchiveService(self.counters_folder, self.archive_path)
        self.google_sheets_service = GoogleSheetsService(self.google_credentials_path, self.google_spreadsheet_id)
        self.google_sheets_connected = False
        self.achievement_progress_service = AchievementProgressService(self.achievement_progress_path)
        self.stream_event_service = StreamEventService(
            self.stream_events_path, self.stream_session_path, self.boss_log_path
        ) 
        self.narrator_service = NarratorService(self.narrator_content_path)
        self._create_obs_websocket_service()
        self.status_label.setText("Settings saved")
        
