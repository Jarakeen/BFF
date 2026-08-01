from __future__ import annotations


import json
import random
from datetime import datetime
from pathlib import Path
import re

from PySide6.QtCore import Qt, QTimer, QAbstractTableModel, QModelIndex
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

from console.engine.source.data_miner import DataBuilderService
from models.expedition_model import ExpeditionModel, StatusFlags
from models.incident_model import IncidentModel, ResponsiblePartyFlags, IncidentStatusFlags
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
from ui.reference_browser import ReferenceBrowserWindow
from ui.theme import ThemeManager

WEATHER_SOURCE_MAP = {
    "Clear": "TOP_clear",
    "Partly Cloudy": "TOP_partly_cloudy",
    "Cloudy": "TOP_cloudy",
    "Light Rain": "TOP_rain_light",
    "Heavy Rain": "TOP_rain_heavy",
    "Storm": "TOP_storm",
    "Fog": "TOP_fog",
    "Snow": "TOP_snow",
    "Windy": "TOP_wind",
}

COFFEE_SOURCE_MAP = {
        "Unavailable": "Unavailable",
        "Requested" : "Requested",        
        "Brewing": "Brewing",   
        "Operational": "Operational",   
        "Enhanced": "Enhanced", 
        "Maximum": "Maximum", 
        "Experimental": "Experimental"
}

SEVERITY_OPTIONS = ["Minor", "Moderate", "Major", "Critical"]

OTTER_VARIABLES = [
    "Nominal",
    "Recursive",
    "Sentient",
    "Unsupervised",
    "Orthogonal",
    "Ceremonial",
    "Migratory",
    "Seasonal",
    "Temporal",
    "Peripheral",
    "Ambient",
    "Speculative",
    "Probabilistic",
    "Inexplicable",
    "Contrarian",
    "Percolating",
    "Ferrous",
    "Buoyant",
    "Obstinate",
    "Misfiled",
]

RESPONSIBLE_PARTY_LABELS = {
    "MooseGremlin": "Moose Gremlin",
    "Lag": "Lag",
    "UserError": "User Error",
    "ESO": "ESO",
    "Unknown": "Unknown",
    "UnderInvestigation": "Under Investigation",
}

INCIDENT_STATUS_LABELS = {
    "Filed": "Filed",
    "PendingReview": "Pending Review",
    "RequiresFollowUp": "Requires Follow-Up",
    "Archived": "Archived",
}


class ReferenceDataTableModel(QAbstractTableModel):
    def __init__(self, records: list[dict] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._records: list[dict] = records or []
        self._headers: list[str] = []

    def set_records(self, records: list[dict]) -> None:
        self.beginResetModel()
        self._records = records
        self._headers = self._collect_headers(records)
        self.endResetModel()

    def _collect_headers(self, records: list[dict]) -> list[str]:
        columns: set[str] = set()
        for record in records:
            if isinstance(record, dict):
                columns.update(record.keys())
        return sorted(columns)

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._records)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._headers[section] if section < len(self._headers) else ""
        return str(section + 1)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role not in {Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole}:
            return None
        record = self._records[index.row()]
        if not isinstance(record, dict):
            return None
        key = self._headers[index.column()]
        value = record.get(key)
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, default=str)
        return str(value)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Black Feather Foundry Field Office")
        self.resize(1400, 900)
        self.setMinimumSize(1100, 760)
        self.setWindowState(Qt.WindowMaximized)

        self.settings_path = Path(__file__).resolve().parents[1] / "settings.json"
        self.settings_service = SettingsService(self.settings_path)
        settings = self.settings_service.load()

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
        self.brb_scene_name = settings["BrbSceneName"]
        self.end_of_stream_scene_name = settings["EndOfStreamSceneName"]
        self.obs_websocket_host = settings["ObsWebSocketHost"]
        self.obs_websocket_port = settings["ObsWebSocketPort"]
        self.obs_websocket_password = settings["ObsWebSocketPassword"]
        self.google_credentials_path = self._resolve_setting_path(settings["GoogleCredentialsPath"])
        self.google_spreadsheet_id = settings["GoogleSpreadsheetId"]
        self.google_sheets_person = settings["GoogleSheetsPerson"]
        self.achievement_progress_path = self._resolve_setting_path(settings["AchievementProgressPath"])
        self.marker_log_path = self._resolve_setting_path(settings["MarkerLogPath"])
        self.current_achievement_run_path = self._resolve_setting_path(settings["CurrentAchievementRunPath"])
        self.current_broadcast_path = self._resolve_setting_path(settings["CurrentBroadcastPath"])
        self.session_archive_folder = self._resolve_setting_path(settings["SessionArchiveFolder"])
        self.json_service = JsonService(self.current_path)
        self.incident_json_service = IncidentJsonService(self.current_incident_path)
        self.archive_service = ArchiveService(self.counters_folder, self.archive_path)
        self.stream_event_service = StreamEventService(
            self.stream_events_path, self.stream_session_path, self.boss_log_path
        )
        self.narrator_service = NarratorService(self.narrator_content_path)
        self._create_obs_websocket_service()

        data_dir = Path(__file__).resolve().parents[1] / "data"
        self.eso_data_service = EsoAchievementDataService(
            data_dir / "eso_tree.json", data_dir / "eso_achievements.json"
        )
        self.achievement_progress_service = AchievementProgressService(self.achievement_progress_path)
        self.google_sheets_service = GoogleSheetsService(self.google_credentials_path, self.google_spreadsheet_id)
        self.google_sheets_connected = False

        self.theme = ThemeManager()

        self._build_ui()
        self._load_stream_session()

    def _resolve_setting_path(self, configured_path: str) -> Path:
        cleaned_path = str(configured_path).strip().strip('"').strip("'")
        candidate = Path(cleaned_path)
        if candidate.is_absolute():
            return candidate
        return self.settings_path.parent / candidate

    def _create_obs_websocket_service(self) -> None:
        self.obs_websocket_service = ObsWebSocketService(
            self.obs_websocket_host,
            self.obs_websocket_port,
            self.obs_websocket_password,
            self,
        )
        self.obs_websocket_service.scene_changed.connect(self._on_obs_scene_changed)
        self.obs_websocket_service.failed.connect(self._on_obs_scene_failed)

    def _on_obs_scene_changed(self, scene_name: str) -> None:
        self.status_label.setText(f"OBS switched to {scene_name}")

    def _on_obs_scene_failed(self, message: str) -> None:
        self.status_label.setText(f"OBS scene switch failed: {message}")

    def _wrap_scrollable(self, page: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(page)
        return scroll

    def _apply_theme(self) -> None:
        """Every color/font/metric here comes from self.theme (ThemeManager) -
        nothing hardcoded. Now that ThemeManager exposes the full colors/
        fonts/metrics/roles namespaces (not just the original 7 convenience
        properties), this draws from those directly for a more complete
        stylesheet."""
        if self.theme.logo:
            self.setWindowIcon(QIcon(self.theme.logo))

        colors = self.theme.colors
        metrics = self.theme.metrics
        title_family = self.theme.title_font.family()
        title_size = self.theme.title_font.pointSize()
        body_family = self.theme.body_font.family()
        body_size = self.theme.body_font.pointSize()

        self.setStyleSheet(f"""
            QMainWindow {{ background: {colors.PAPER}; }}
            QWidget {{
                background: {colors.PAPER};
                color: {colors.TEXT};
                font-family: "{body_family}";
                font-size: {body_size}px;
            }}
            QWidget#sidebar {{
                background: {colors.SIDEBAR};
                border-right: 1px solid {colors.BORDER};
            }}
            QLabel#pageTitle {{
                font-family: "{title_family}";
                font-size: {title_size}px;
                font-weight: bold;
                color: {colors.ACCENT_LIGHT};
            }}
            QLabel#brandMark {{
                font-size: {metrics.BRAND_MARK_SIZE}px;
                color: {colors.ACCENT_LIGHT};
            }}
            QLabel#brandTitle {{
                font-family: "{title_family}";
                font-size: {metrics.BRAND_TITLE_SIZE}px;
                font-weight: bold;
                color: {colors.ACCENT_LIGHT};
            }}
            QLabel#brandSubtitle {{
                font-size: {metrics.BRAND_SUBTITLE_SIZE}px;
                color: {colors.TEXT_MUTED};
                letter-spacing: 2px;
            }}
            QLabel#navSectionHeading {{
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
                color: {colors.TEXT_MUTED};
                padding: 2px 12px 4px 12px;
            }}
            QWidget#navSectionDivider {{
                background: {colors.BORDER};
                margin: 0px 12px 6px 12px;
            }}
            QGroupBox {{
                background: {colors.CARD};
                border: 1px solid {colors.BORDER};
                border-radius: {metrics.CARD_RADIUS}px;
                margin-top: 14px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 6px;
                color: {colors.ACCENT_LIGHT};
                font-weight: bold;
            }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox {{
                background: {colors.INPUT_BG};
                color: {colors.TEXT};
                border: 1px solid {colors.INPUT_BORDER};
                border-radius: 4px;
                padding: 6px;
                selection-background-color: {colors.ACCENT};
            }}
            QPushButton {{
                background: {colors.ACCENT};
                color: {colors.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: {metrics.SM}px {metrics.MD}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {colors.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background: {colors.ACCENT_DARK}; }}
            QPushButton[nav="true"] {{
                background: transparent;
                color: {colors.ACCENT_LIGHT};
                text-align: left;
                border: none;
                border-left: {metrics.NAV_INDICATOR}px solid transparent;
                border-radius: 0px;
                padding: 10px 12px;
            }}
            QPushButton[nav="true"]:hover {{ background: {colors.NAV_HOVER}; }}
            QPushButton[nav="true"]:checked {{
                background: {colors.NAV_ACTIVE};
                border-left: {metrics.NAV_INDICATOR}px solid {colors.NAV_ACTIVE_BORDER};
                color: {colors.TEXT_LIGHT};
            }}
            QCheckBox {{
                color: {colors.TEXT};
                spacing: 7px;
            }}
            QCheckBox::indicator {{
                width: 15px;
                height: 15px;
                border: 1px solid {colors.INPUT_BORDER};
                border-radius: 3px;
                background: {colors.INPUT_BG};
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid {colors.ACCENT_LIGHT};
            }}
            QCheckBox::indicator:checked {{
                background: {colors.ACCENT};
                border: 1px solid {colors.ACCENT_DARK};
            }}
        """)

    def _build_ui(self) -> None:
        self._apply_theme()

        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(258)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(22, 30, 22, 20)
        sidebar_layout.setSpacing(10)

        sidebar_scroll = QScrollArea()
        sidebar_scroll.setObjectName("sidebarScroll")
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QScrollArea.NoFrame)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setWidget(sidebar)

        feather = QLabel("✦")
        feather.setObjectName("brandMark")
        feather.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(feather)

        brand = QLabel("BLACK FEATHER\nFOUNDRY")
        brand.setObjectName("brandTitle")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(brand)

        office = QLabel("FIELD OFFICE")
        office.setObjectName("brandSubtitle")
        office.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(office)
        sidebar_layout.addSpacing(24)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._wrap_scrollable(self._build_broadcast_page()), "Broadcast Desk")
        self.tabs.addTab(self._wrap_scrollable(self._build_expedition_page()), "Field Office")
        self.tabs.addTab(self._wrap_scrollable(self._build_stream_events_page()), "Stream Events")
        self.tabs.addTab(self._wrap_scrollable(self._build_archive_log_page()), "Archive Log")
        self.tabs.addTab(self._wrap_scrollable(self._build_incident_page()), "Incident Report")
        self.tabs.addTab(self._wrap_scrollable(self._build_achievement_page()), "Achievement Run")
        self.tabs.addTab(self._wrap_scrollable(self._build_odds_and_ends_page()), "Collections")
        self.tabs.addTab(self._wrap_scrollable(self._build_reference_browser_page()),"Comp Engine",)
        self.tabs.addTab(self._wrap_scrollable(self._build_settings_page()), "Settings")
        self.tabs.tabBar().hide()

        self.nav_buttons: list[tuple[QPushButton, int]] = []
        nav_sections = [
            ("CURRENT SESSION", [("Broadcast Desk", 0), ("Field Office", 1)]),
            ("STREAM OPERATIONS", [("Stream Events", 2)]),
            ("RECORDS", [("Incident Report", 4), ("Archive Log", 3)]),
            ("PROJECTS", [("Achievement Run", 5), ("Collections", 6)]),
            ("SYSTEM", [("Settings", 8), ("Comp Engine", 7)]),
        ]

        for section_index, (section_label, pages) in enumerate(nav_sections):
            if section_index > 0:
                sidebar_layout.addSpacing(14)
            heading = QLabel(section_label)
            heading.setObjectName("navSectionHeading")
            sidebar_layout.addWidget(heading)
            divider = QWidget()
            divider.setObjectName("navSectionDivider")
            divider.setFixedHeight(1)
            sidebar_layout.addWidget(divider)

            for label, page in pages:
                button = QPushButton(label)
                button.setProperty("nav", True)
                button.setCheckable(True)
                button.clicked.connect(
                    lambda checked=False, page=page: self._select_page(page)
                )
                sidebar_layout.addWidget(button)
                self.nav_buttons.append((button, page))

        sidebar_layout.addStretch(1)
        reminder = QLabel("REMEMBER\n\n• Check the quest log\n• Read the achievements\n• Communicate\n• Have fun\n• Take breaks\n• Drink coffee")
        reminder.setObjectName("reminder")
        sidebar_layout.addWidget(reminder)
        footer = QLabel("FIELD OFFICE ARCHIVES")
        footer.setObjectName("sidebarFooter")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(footer)
        root.addWidget(sidebar_scroll)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 18)
        content_layout.setSpacing(12)
        self.page_title = QLabel()
        self.page_title.setObjectName("pageTitle")
        self.page_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.page_title)
        self.page_subtitle = QLabel("DOCUMENTING PROGRESS. CELEBRATING SMALL VICTORIES.")
        self.page_subtitle.setObjectName("pageSubtitle")
        self.page_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.page_subtitle)
        content_layout.addWidget(self.tabs, 1)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        content_layout.addWidget(self.status_label)
        root.addWidget(content, 1)

        self._select_page(0)

    def _select_page(self, index: int) -> None:
        titles = ("BROADCAST DESK", "FIELD OFFICE", "STREAM EVENTS", "ARCHIVE LOG", "INCIDENT REPORT", "ACHIEVEMENT RUN TRACKER", "COLLECTIONS",  "SETTINGS")
        self.tabs.setCurrentIndex(index)
        self.page_title.setText(titles[index])
        for button, page_index in self.nav_buttons:
            button.setChecked(page_index == index)
        if index == 1:  # Field Office - Expedition/Difficulty/etc. now live on Broadcast Desk
            self.refresh_top_bar_summary()

    def _build_expedition_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        grid = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()

        

        self._build_status_checkboxes()

        clipboard_label = QLabel("CLIPBOARD")
        
        right.addWidget(clipboard_label)
        right.addWidget(self._make_section("Assignment", self.assignment))
        right.addWidget(self._make_clipboard_status_panel())

        field_note_label = QLabel("FIELD NOTE")
        
        right.addWidget(field_note_label)
        right.addWidget(self._make_section("Observation", self.observation))
        right.addWidget(self._make_section("Context", self.context))
        right.addWidget(self._make_section("Recommendations for Future Adventurers", self.next_steps))
        right.addWidget(self._make_fieldnote_status_panel())

        grid.addLayout(left)
        grid.addLayout(right)
        layout.addLayout(grid)

        actions = QHBoxLayout()
        self.clear_btn = QPushButton("Clear")
        self.save_btn = QPushButton("Save to OBS")
        self.new_note_btn = QPushButton("Save to Archive")
        self.load_btn = QPushButton("Load Expedition")
        self.incident_btn = QPushButton("Open Incident Report")

        self.clear_btn.clicked.connect(self.clear_expedition)
        self.load_btn.clicked.connect(self.load_expedition)
        self.save_btn.clicked.connect(self.save_expedition)
        self.new_note_btn.clicked.connect(self.new_field_note)
        self.incident_btn.clicked.connect(lambda: self._select_page(4))

        actions.addWidget(self.clear_btn)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.new_note_btn)
        actions.addWidget(self.load_btn)
        actions.addWidget(self.incident_btn)
        layout.addLayout(actions)
        return page

    def _build_stream_events_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        boss_row = QHBoxLayout()
        boss_row.addWidget(QLabel("Current Boss:"))
        self.current_boss_edit = QLineEdit()
        boss_row.addWidget(self.current_boss_edit)
        layout.addLayout(boss_row)

        counters_box = QGroupBox("This Stream")
        counters_layout = QHBoxLayout(counters_box)
        self.total_pulls_label = QLabel("Total Pulls: 0")
        self.boss_pulls_label = QLabel("Pulls on Boss: 0")
        self.boss_wipes_label = QLabel("Wipes on Boss: 0")
        counters_layout.addWidget(self.total_pulls_label)
        counters_layout.addWidget(self.boss_pulls_label)
        counters_layout.addWidget(self.boss_wipes_label)
        layout.addWidget(counters_box)

        pull_box = QGroupBox("Pull Starts")
        pull_layout = QHBoxLayout(pull_box)
        self.first_pull_cb = QCheckBox("First pull on this boss (marks a chapter)")
        pull_starts_btn = QPushButton("Pull Starts")
        pull_starts_btn.clicked.connect(self.on_pull_starts)
        ult_pull_btn = QPushButton("Ult Pull")
        ult_pull_btn.setMaximumWidth(80)
        ult_pull_btn.setToolTip("Marks a chapter for this pull only - does not touch pull/wipe counters")
        ult_pull_btn.clicked.connect(self.on_ult_pull)
        pull_layout.addWidget(self.first_pull_cb)
        pull_layout.addWidget(pull_starts_btn)
        pull_layout.addWidget(ult_pull_btn)
        layout.addWidget(pull_box)

        wipe_box = QGroupBox("Wipes")
        wipe_layout = QHBoxLayout(wipe_box)
        wipe_layout.addWidget(QLabel("Reached:"))
        self.wipe_percent_spin = QSpinBox()
        self.wipe_percent_spin.setRange(0, 100)
        self.wipe_percent_spin.setSuffix("%")
        wipe_layout.addWidget(self.wipe_percent_spin)
        self.rough_night_cb = QCheckBox("Rough night (skip narrator posts)")
        wipe_layout.addWidget(self.rough_night_cb)
        wipe_btn = QPushButton("Wipes")
        wipe_btn.clicked.connect(self.on_wipe)
        wipe_layout.addWidget(wipe_btn)
        layout.addWidget(wipe_box)

        boss_clear_btn = QPushButton("Boss Clears")
        boss_clear_btn.clicked.connect(self.on_boss_clear)
        layout.addWidget(boss_clear_btn)

        narrator_box = QGroupBox("Natural History Narrator")
        narrator_layout = QHBoxLayout(narrator_box)
        narrator_buttons = [
            ("General Observations", "General"),
            ("Healers", "Healers"),
            ("Tanks", "Tanks"),
            ("DPS", "DPS"),
            ("🤣 Funny Moments", "FunnyMoments"),
            ("📖 Progression", "Progression"),
        ]
        for label, category in narrator_buttons:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked=False, c=category: self.post_narrator_note(c))
            narrator_layout.addWidget(btn)
        layout.addWidget(narrator_box)

        scene_box = QGroupBox("Scene Switches")
        scene_layout = QHBoxLayout(scene_box)
        brb_btn = QPushButton("☕ BRB")
        brb_btn.clicked.connect(self.on_brb)
        end_stream_btn = QPushButton("🌙 End of Stream")
        end_stream_btn.clicked.connect(self.on_end_of_stream)
        scene_layout.addWidget(brb_btn)
        scene_layout.addWidget(end_stream_btn)
        layout.addWidget(scene_box)

        reset_btn = QPushButton("Reset Pull/Wipe Counters (new stream)")
        reset_btn.clicked.connect(self.reset_stream_session)
        layout.addWidget(reset_btn)

        layout.addStretch(1)
        return page

    def _build_archive_log_page(self) -> QWidget:
        page = QWidget()
        outer_layout = QHBoxLayout(page)

        # --- Left column: this session's live logs ---
        left_column = QVBoxLayout()

        intro = QLabel("What's actually being saved when you push buttons on Stream Events.")
        left_column.addWidget(intro)

        marker_box = QGroupBox("Marker Log (Pull Starts, Wipes, Boss Clears, BRB, Field Notes, Incidents)")
        marker_layout = QVBoxLayout(marker_box)
        self.marker_log_view = QTextEdit()
        self.marker_log_view.setReadOnly(True)
        self.marker_log_view.setPlaceholderText("Click Refresh to load this session's marker log.")
        marker_layout.addWidget(self.marker_log_view)
        left_column.addWidget(marker_box, 2)

        boss_box = QGroupBox("Boss Log (from Boss Clears)")
        boss_layout = QVBoxLayout(boss_box)
        self.boss_log_view = QTextEdit()
        self.boss_log_view.setReadOnly(True)
        self.boss_log_view.setPlaceholderText("Click Refresh to load this session's boss log.")
        boss_layout.addWidget(self.boss_log_view)
        left_column.addWidget(boss_box, 1)

        notes_box = QGroupBox("Session Notes (included in the consolidated report)")
        notes_layout = QVBoxLayout(notes_box)
        self.session_notes_edit = QTextEdit()
        self.session_notes_edit.setPlaceholderText("How'd the run go? Anything worth remembering...")
        notes_layout.addWidget(self.session_notes_edit)
        left_column.addWidget(notes_box, 1)

        actions = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        archive_btn = QPushButton("Save to Archive")
        clear_btn = QPushButton("Clear")
        refresh_btn.clicked.connect(self.refresh_archive_log)
        clear_btn.clicked.connect(self.clear_archive)
        archive_btn.clicked.connect(self.archive_current_run)
        actions.addWidget(clear_btn)
        actions.addWidget(refresh_btn)
        actions.addWidget(archive_btn)
        left_column.addLayout(actions)

        outer_layout.addLayout(left_column, 2)

        # --- Right column: browse past archived sessions ---
        right_column = QVBoxLayout()
        browser_box = QGroupBox("Archive Browser")
        browser_layout = QVBoxLayout(browser_box)

        search_row = QHBoxLayout()
        self.archive_search_edit = QLineEdit()
        self.archive_search_edit.setPlaceholderText("Search by serial, boss, location, date...")
        self.archive_search_edit.textChanged.connect(self.filter_archive_browser)
        search_row.addWidget(self.archive_search_edit)
        browser_layout.addLayout(search_row)

        self.archive_browser_list = QListWidget()
        self.archive_browser_list.currentItemChanged.connect(self.on_archive_selected)
        browser_layout.addWidget(self.archive_browser_list, 1)

        browser_refresh_btn = QPushButton("Refresh List")
        browser_refresh_btn.clicked.connect(self.refresh_archive_browser)
        browser_layout.addWidget(browser_refresh_btn)

        right_column.addWidget(browser_box, 1)

        detail_box = QGroupBox("Selected Archive")
        detail_layout = QVBoxLayout(detail_box)
        self.archive_detail_view = QTextEdit()
        self.archive_detail_view.setReadOnly(True)
        self.archive_detail_view.setPlaceholderText("Select an archive on the left to view it here.")
        detail_layout.addWidget(self.archive_detail_view)
        right_column.addWidget(detail_box, 1)

        outer_layout.addLayout(right_column, 2)

        self.refresh_archive_browser()
        return page

    def _parse_archive_summary(self, path: Path) -> dict:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = ""

        def extract(pattern: str) -> str:
            match = re.search(pattern, text, re.MULTILINE)
            return match.group(1).strip() if match else "Unknown"

        return {
            "id": path.stem,
            "location": extract(r"^Location\s+(.+)$"),
            "real_date": extract(r"Real Date:\s*(.+)"),
            "events": extract(r"Marker Events:\s*(\d+)"),
            "text": text,
            "search_blob": text.lower(),
        }

    def refresh_archive_browser(self) -> None:
        self.archive_browser_list.clear()
        if not self.session_archive_folder.exists():
            return
        files = sorted(self.session_archive_folder.glob("ST-*.md"), reverse=True)
        for path in files:
            summary = self._parse_archive_summary(path)
            label = f"{summary['id']}  —  {summary['real_date']}  —  {summary['location']}  ({summary['events']} events)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, summary)
            self.archive_browser_list.addItem(item)
        self.filter_archive_browser()

    def filter_archive_browser(self) -> None:
        query = self.archive_search_edit.text().strip().lower()
        for i in range(self.archive_browser_list.count()):
            item = self.archive_browser_list.item(i)
            summary = item.data(Qt.ItemDataRole.UserRole)
            matches = not query or query in summary["search_blob"] or query in summary["id"].lower()
            item.setHidden(not matches)

    def on_archive_selected(self, current, previous) -> None:
        if current is None:
            return
        summary = current.data(Qt.ItemDataRole.UserRole)
        self.archive_detail_view.setPlainText(summary["text"])


    def archive_current_run(self):
        self.refresh_archive_log()  # pull fresh data from disk rather than archive a stale view

        marker_log = self.marker_log_view.toPlainText()
        boss_log = self.boss_log_view.toPlainText()
        notes = self.session_notes_edit.toPlainText().strip() or "No notes recorded."

        self.session_archive_folder.mkdir(parents=True, exist_ok=True)
        archive_id = self.get_next_archive_number()

        # --- Pull the shared expedition fields straight from Broadcast Desk ---
        location = self._broadcast_location_text() or "Unspecified"
        expedition = self.broadcast_focus_combo.currentText() or "Unspecified"
        objective = self.broadcast_goal_edit.text().strip() or "Unspecified"
        team = self.broadcast_team_edit.text().strip() or "Unspecified"

        # --- Derive stats from the marker log itself, rather than tracking them separately ---
        marker_lines = [line for line in marker_log.splitlines() if line.strip()]
        marker_event_count = len(marker_lines)
        bosses_cleared_count = sum(1 for line in marker_lines if "Boss Clear" in line)
        incident_lines = [line for line in marker_lines if "Incident" in line]
        achievement_lines = [line for line in marker_lines if "Achievement" in line]

        elapsed_time = "Unknown"
        current_status = "No Events Yet"
        if marker_lines:
            last_line = marker_lines[-1]
            stream_match = re.search(r"Stream:\s*([\d:]+|not streaming)", last_line)
            if stream_match:
                stream_value = stream_match.group(1)
                if stream_value == "not streaming":
                    elapsed_time = "Not streaming"
                    current_status = "Not Streaming"
                else:
                    parts = stream_value.split(":")
                    if len(parts) == 3:
                        hours, minutes, _seconds = (int(p) for p in parts)
                        elapsed_time = (f"{hours}h {minutes}m" if hours else f"{minutes}m")
                    else:
                        elapsed_time = stream_value
                    current_status = "Expedition Active"

        real_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        tamriel_date = get_tamriel_date()

        divider = "─" * 24
        section_divider = "-" * 50

        summary = "\n".join([
            "CURRENT RUN",
            f"Archive ID   {archive_id}",
            f"Location     {location}",
            f"Expedition   {expedition}",
            f"Objective    {objective}",
            f"Team         {team}",
            divider,
            f"Marker Events: {marker_event_count}   Bosses Cleared: {bosses_cleared_count}   "
            f"Incidents: {len(incident_lines)}   Achievements: {len(achievement_lines)}   "
            f"Elapsed Time: {elapsed_time}",
            divider,
            f"Current Status  {'✓' if current_status == 'Expedition Active' else '•'} {current_status}",
            f"Real Date: {real_date}",
            f"Tamriel Date: {tamriel_date}",
        ])

        archive_text = "\n".join([
            summary,
            section_divider,
            "## Marker Log",
            "",
            marker_log or "No marker events recorded.",
            section_divider,
            "## Boss Log",
            "",
            boss_log or "No bosses cleared this session.",
            section_divider,
            "## Incident Reports",
            "",
            "\n".join(incident_lines) if incident_lines else "No incidents recorded.",
            section_divider,
            "## Notes",
            "",
            notes,
            "",
        ])

        filename = self.session_archive_folder / f"{archive_id}.md"
        filename.write_text(archive_text, encoding="utf-8")
        self.status_label.setText(f"Archive saved to {filename}")

    def get_next_archive_number(self):
        self.session_archive_folder.mkdir(parents=True, exist_ok=True)
        highest = 0
        for file in self.session_archive_folder.glob("ST-*.md"):
            match = re.match(r"ST-(\d+)\.md", file.name)
            if match:
                highest = max(highest, int(match.group(1)))
        return f"ST-{highest + 1:06d}"

    def refresh_archive_log(self) -> None:
        try:
            if self.marker_log_path.exists():
                self.marker_log_view.setPlainText(self.marker_log_path.read_text(encoding="utf-8"))
            else:
                self.marker_log_view.setPlainText("(No MarkerLog.md yet - nothing has been logged this session.)")
            self.marker_log_view.verticalScrollBar().setValue(self.marker_log_view.verticalScrollBar().maximum())
        except OSError as exc:
            self.marker_log_view.setPlainText(f"Couldn't read Marker Log: {exc}")

        try:
            if self.boss_log_path.exists():
                self.boss_log_view.setPlainText(self.boss_log_path.read_text(encoding="utf-8"))
            else:
                self.boss_log_view.setPlainText("(No BossLog.md yet - no bosses cleared this session.)")
            self.boss_log_view.verticalScrollBar().setValue(self.boss_log_view.verticalScrollBar().maximum())
        except OSError as exc:
            self.boss_log_view.setPlainText(f"Couldn't read Boss Log: {exc}")

    def clear_archive(self):
        """Clear the current archive display."""
        self.marker_log_view.clear()
        self.boss_log_view.clear()
        self.status_label.setText("Archive display cleared.")

    def _build_achievement_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.achievement_run_id_label = QLabel("AR-—")
        self.achievement_run_id_label.setObjectName("achievementRunId")
        id_row = QHBoxLayout()
        id_row.addStretch(1)
        id_row.addWidget(QLabel("RUN ID"))
        id_row.addWidget(self.achievement_run_id_label)
        layout.addLayout(id_row)

        details = QGroupBox("Run Details")
        detail_grid = QGridLayout(details)
        self.achievement_date_edit = QLineEdit(datetime.now().strftime("%m / %d / %Y"))
        self.achievement_content_combo = QComboBox()
        self.achievement_content_combo.setEditable(True)
        self.achievement_content_combo.addItems(self._eso_run_content())
        self.achievement_group_size = QSpinBox()
        self.achievement_group_size.setRange(1, 24)
        self.achievement_group_size.setValue(4)
        detail_grid.addWidget(QLabel("DATE"), 0, 0)
        detail_grid.addWidget(QLabel("DUNGEON / TRIAL"), 0, 1)
        detail_grid.addWidget(QLabel("GROUP SIZE"), 0, 2)
        detail_grid.addWidget(self.achievement_date_edit, 1, 0)
        detail_grid.addWidget(self.achievement_content_combo, 1, 1)
        detail_grid.addWidget(self.achievement_group_size, 1, 2)
        self.achievement_normal_cb = QCheckBox("Normal")
        self.achievement_veteran_cb = QCheckBox("Veteran")
        self.achievement_hard_mode_cb = QCheckBox("Hard Mode")
        self.achievement_perfecta_cb = QCheckBox("Perfecta")
        self.achievement_veteran_cb.setChecked(True)
        difficulty_row = QHBoxLayout()
        for checkbox in (self.achievement_normal_cb, self.achievement_veteran_cb, self.achievement_hard_mode_cb, self.achievement_perfecta_cb):
            difficulty_row.addWidget(checkbox)
        detail_grid.addWidget(QLabel("DIFFICULTY"), 2, 0)
        detail_grid.addLayout(difficulty_row, 3, 0, 1, 2)
        self.achievement_full_clear_cb = QCheckBox("Full Clear")
        self.achievement_only_cb = QCheckBox("Achievements Only")
        self.achievement_speed_run_cb = QCheckBox("Speed Run")
        self.achievement_teaching_cb = QCheckBox("Teaching Run")
        run_type_row = QHBoxLayout()
        for checkbox in (self.achievement_full_clear_cb, self.achievement_only_cb, self.achievement_speed_run_cb, self.achievement_teaching_cb):
            run_type_row.addWidget(checkbox)
        detail_grid.addWidget(QLabel("RUN TYPE"), 2, 2)
        detail_grid.addLayout(run_type_row, 3, 2)
        layout.addWidget(details)

        body = QHBoxLayout()
        targets_box = QGroupBox("Achievements Targeted")
        targets_grid = QGridLayout(targets_box)
        targets_grid.addWidget(QLabel("ACHIEVEMENT"), 0, 0)
        targets_grid.addWidget(QLabel("IN PROGRESS"), 0, 1)
        targets_grid.addWidget(QLabel("COMPLETE"), 0, 2)
        self.achievement_target_edits: list[QLineEdit] = []
        self.achievement_progress_cbs: list[QCheckBox] = []
        self.achievement_complete_cbs: list[QCheckBox] = []
        for row in range(5):
            target = QLineEdit()
            target.setPlaceholderText(f"Achievement {row + 1}")
            in_progress = QCheckBox()
            complete = QCheckBox()
            self.achievement_target_edits.append(target)
            self.achievement_progress_cbs.append(in_progress)
            self.achievement_complete_cbs.append(complete)
            targets_grid.addWidget(target, row + 1, 0)
            targets_grid.addWidget(in_progress, row + 1, 1, Qt.AlignmentFlag.AlignCenter)
            targets_grid.addWidget(complete, row + 1, 2, Qt.AlignmentFlag.AlignCenter)
        body.addWidget(targets_box, 1)

        notes_column = QVBoxLayout()
        self.achievement_notes = QTextEdit()
        self.achievement_notes.setPlaceholderText("Clean pulls, boss notes, and key moments.")
        self.achievement_lessons = QTextEdit()
        self.achievement_lessons.setPlaceholderText("Lessons learned and improvements for next time.")
        self.achievement_next_steps = QTextEdit()
        self.achievement_next_steps.setPlaceholderText("What should the crew try next?")
        notes_column.addWidget(self._make_section("Run Notes / Key Moments", self.achievement_notes))
        notes_column.addWidget(self._make_section("Lessons Learned / Improvements", self.achievement_lessons))
        notes_column.addWidget(self._make_section("What's Next?", self.achievement_next_steps))
        body.addLayout(notes_column, 1)
        layout.addLayout(body)

        outcome = QGroupBox("Run Result")
        outcome_row = QHBoxLayout(outcome)
        self.achievement_success_cb = QCheckBox("Success!")
        self.achievement_partial_cb = QCheckBox("Partial Success")
        self.achievement_not_today_cb = QCheckBox("Not Today")
        self.achievement_time_edit = QLineEdit()
        self.achievement_time_edit.setPlaceholderText("00 : 00 : 00")
        for widget in (self.achievement_success_cb, self.achievement_partial_cb, self.achievement_not_today_cb):
            outcome_row.addWidget(widget)
        outcome_row.addStretch(1)
        outcome_row.addWidget(QLabel("FINAL SCORE / TIME"))
        outcome_row.addWidget(self.achievement_time_edit)
        layout.addWidget(outcome)

        actions = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        obs_btn = QPushButton("Save to OBS")
        draft_btn = QPushButton("Save Draft")
        load_btn = QPushButton("Load Draft")
        archive_btn = QPushButton("Save to Archive")
        clear_btn.clicked.connect(self.clear_achievement_run)
        obs_btn.clicked.connect(self.save_achievement_to_obs)
        draft_btn.clicked.connect(self.save_achievement_draft)
        load_btn.clicked.connect(self.load_achievement_draft)
        archive_btn.clicked.connect(self.archive_achievement_run)
        actions.addWidget(clear_btn)
        actions.addWidget(obs_btn)
        actions.addWidget(load_btn)
        actions.addStretch(1)
        actions.addWidget(draft_btn)
        actions.addWidget(archive_btn)
        layout.addLayout(actions)
        return page

    def _build_broadcast_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        intro = QLabel("Prepare an on-brand field dispatch for your next expedition.")
        intro.setObjectName("broadcastIntro")
        intro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(intro)

        briefing = QGroupBox("Tonight's Briefing")
        form = QFormLayout(briefing)
        self.broadcast_focus_combo = QComboBox()
        self.broadcast_focus_combo.addItems(["Trials", "Dungeons", "Achievement Hunt", "Progression Night", "Field Notes", "Open Expedition"])
        self.broadcast_focus_combo.currentTextChanged.connect(self.on_broadcast_focus_changed)

        # Location swaps between free text and a Trial/Dungeon dropdown
        # depending on what's picked in EXPEDITION TYPE above.
        self.broadcast_location_stack = QStackedWidget()
        self.broadcast_location_edit = QLineEdit()
        self.broadcast_location_edit.setPlaceholderText("e.g. Black Rose Prison, Cloudrest, or Tamriel")
        self.broadcast_location_combo = QComboBox()
        self.broadcast_location_combo.setEditable(True)
        self.broadcast_location_stack.addWidget(self.broadcast_location_edit)  # index 0: free text
        self.broadcast_location_stack.addWidget(self.broadcast_location_combo)  # index 1: dropdown

        self.broadcast_goal_edit = QLineEdit()
        self.broadcast_goal_edit.setPlaceholderText("e.g. Perfecta practice, no-death attempt, or cozy collecting")
        self.broadcast_mood_combo = QComboBox()
        self.broadcast_mood_combo.addItems(["Focused", "Funny", "Questing", "Hardmode"])
        self.broadcast_team_edit = QLineEdit()
        self.broadcast_team_edit.setPlaceholderText("e.g. Black Feather Foundry")

        difficulty_row = QHBoxLayout()
        self.broadcast_difficulty_checkboxes = {
            "Normal": QCheckBox("Normal"),
            "Veteran": QCheckBox("Veteran"),
            "Hardmode": QCheckBox("Hardmode"),
        }
        for checkbox in self.broadcast_difficulty_checkboxes.values():
            difficulty_row.addWidget(checkbox)
        difficulty_row.addStretch(1)

        self.broadcast_weather = self._build_weather_selector()
        self.broadcast_coffee = self._build_coffee_selector()
        self.broadcast_coffee_level = self._build_field("Coffee Level")
        self.broadcast_engineering = QComboBox()
        self.broadcast_engineering.setEditable(True)
        self.broadcast_engineering.addItems(OTTER_VARIABLES)
        self.broadcast_engineering.setCurrentText("")
        self.broadcast_incidents = self._build_field("Incidents")

        coffee_level_row = QHBoxLayout()
        coffee_level_row.addWidget(self.broadcast_coffee_level)
        coffee_level_randomize_btn = QPushButton("🎲")
        coffee_level_randomize_btn.setToolTip("Randomize coffee level")
        coffee_level_randomize_btn.setFixedWidth(36)
        coffee_level_randomize_btn.clicked.connect(self.randomize_coffee_level)
        coffee_level_row.addWidget(coffee_level_randomize_btn)

        form.addRow("EXPEDITION TYPE", self.broadcast_focus_combo)
        form.addRow("LOCATION / CONTENT", self.broadcast_location_stack)
        form.addRow("TONIGHT'S GOAL", self.broadcast_goal_edit)
        form.addRow("DIFFICULTY", difficulty_row)
        form.addRow("WEATHER", self.broadcast_weather)
        form.addRow("COFFEE", self.broadcast_coffee)
        form.addRow("COFFEE LEVEL", coffee_level_row)
        form.addRow("ENGINEERING", self.broadcast_engineering)
        form.addRow("INCIDENT COUNTER", self.broadcast_incidents)
        form.addRow("TONE", self.broadcast_mood_combo)
        form.addRow("TEAM NAME", self.broadcast_team_edit)
        layout.addWidget(briefing)

        generate_btn = QPushButton("Generate Broadcast Copy")
        generate_btn.clicked.connect(self.generate_broadcast_copy)
        layout.addWidget(generate_btn)

        output_row = QHBoxLayout()
        title_box = QGroupBox("Stream Title (click one to copy)")
        title_layout = QVBoxLayout(title_box)
        self.stream_title_list = QListWidget()
        self.stream_title_list.itemClicked.connect(
            lambda item: self.copy_broadcast_text(item.text(), "Stream title copied")
        )
        title_layout.addWidget(self.stream_title_list)
        output_row.addWidget(title_box, 1)

        notification_box = QGroupBox("Live Notification (click one to copy)")
        notification_layout = QVBoxLayout(notification_box)
        self.live_notification_list = QListWidget()
        self.live_notification_list.setWordWrap(True)
        self.live_notification_list.itemClicked.connect(
            lambda item: self.copy_broadcast_text(item.text(), "Live notification copied")
        )
        notification_layout.addWidget(self.live_notification_list)
        output_row.addWidget(notification_box, 1)
        layout.addLayout(output_row)

        actions = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        obs_btn = QPushButton("Save to OBS")
        archive_btn = QPushButton("Save to Archive")
        clear_btn.clicked.connect(self.clear_broadcast)
        obs_btn.clicked.connect(self.save_broadcast_to_obs)
        archive_btn.clicked.connect(self.archive_broadcast)
        actions.addWidget(clear_btn)
        actions.addWidget(obs_btn)
        actions.addWidget(archive_btn)
        layout.addLayout(actions)

        layout.addStretch(1)
        return page

    def on_broadcast_focus_changed(self, focus: str) -> None:
        if focus == "Trials":
            names = [n for n in self.eso_data_service.subcategories("Trials") if n != "General"]
            self.broadcast_location_combo.clear()
            self.broadcast_location_combo.addItems(sorted(names))
            self.broadcast_location_stack.setCurrentWidget(self.broadcast_location_combo)
        elif focus == "Dungeons":
            names = [n for n in self.eso_data_service.subcategories("Dungeons") if n != "General"]
            names += [n for n in self.eso_data_service.subcategories("DLC Dungeons") if n != "General"]
            self.broadcast_location_combo.clear()
            self.broadcast_location_combo.addItems(sorted(names))
            self.broadcast_location_stack.setCurrentWidget(self.broadcast_location_combo)
        else:
            self.broadcast_location_stack.setCurrentWidget(self.broadcast_location_edit)

    def _broadcast_location_text(self) -> str:
        if self.broadcast_location_stack.currentWidget() is self.broadcast_location_combo:
            return self.broadcast_location_combo.currentText().strip()
        return self.broadcast_location_edit.text().strip()

    def generate_broadcast_copy(self) -> None:
        focus = self.broadcast_focus_combo.currentText()
        location = self._broadcast_location_text() or "the field"
        goal = self.broadcast_goal_edit.text().strip() or "documenting the expedition"
        mood = self.broadcast_mood_combo.currentText()
        team = self.broadcast_team_edit.text().strip()

        titles = self._generate_stream_titles(focus, location, goal, mood)
        if team:
            titles = [f"{title} — {team}" for title in titles]
        notifications = self._generate_live_notifications(focus, location, goal, mood)

        self.stream_title_list.clear()
        self.stream_title_list.addItems(titles)
        self.live_notification_list.clear()
        self.live_notification_list.addItems(notifications)
        self.status_label.setText(f"Generated {len(titles)} titles and {len(notifications)} notifications")

    @staticmethod
    def _generate_stream_titles(focus: str, location: str, goal: str, mood: str) -> list[str]:
        mood_lower = mood.lower()
        candidates = [
            f"Field Notes: {location} — {goal}",
            f"{location} Survey, Continued",
            f"Documenting {location} Tonight",
            f"Foundry Field Report — {location}",
            f"An Expedition to {location}",
            f"{location}: Observations in Progress",
            f"Cataloging {location} — {goal}",
            f"Field Office Live: {location}",
            f"Weather Permitting: {location}",
            f"Tonight's Log: {location} ({mood})",
            f"Routine Survey — {location}",
            f"{goal}, Documented Live from {location}",
        ]
        seen = set()
        unique = []
        for title in candidates:
            if title not in seen:
                seen.add(title)
                unique.append(title)
        return unique[:10]

    @staticmethod
    def _generate_live_notifications(focus: str, location: str, goal: str, mood: str) -> list[str]:
        mood_lower = mood.lower()
        goal_lower = goal[:1].lower() + goal[1:] if goal else goal
        candidates = [
            f"The Foundry has resumed operations at {location}. Tonight's objective: {goal}. Findings to follow.",
            f"Field notes are being taken at {location}. Conditions: {mood_lower}.",
            f"An expedition has been dispatched to {location}. Purpose: {goal}.",
            f"Observed: the crew has returned to {location}. Documentation ongoing.",
            f"Tonight's survey covers {location}. Objective: {goal}. Weather: {mood_lower}.",
            f"The archive grows. Tonight: {location}, {goal_lower}.",
            f"Field Office open. Currently investigating {location}. No further remarks at this time.",
            f"Routine documentation of {location} is underway. All quiet so far.",
        ]
        trimmed = []
        for text in candidates:
            if len(text) > 140:
                text = text[:137].rstrip() + "..."
            trimmed.append(text)
        seen = set()
        unique = []
        for text in trimmed:
            if text not in seen:
                seen.add(text)
                unique.append(text)
        return unique[:8]

    def copy_broadcast_text(self, text: str, status: str) -> None:
        if not text.strip():
            self.status_label.setText("Generate the broadcast copy first")
            return
        QApplication.clipboard().setText(text)
        self.status_label.setText(status)

    def clear_broadcast(self) -> None:
        self.broadcast_focus_combo.setCurrentIndex(0)
        self.broadcast_location_stack.setCurrentWidget(self.broadcast_location_edit)
        self.broadcast_location_edit.clear()
        self.broadcast_goal_edit.clear()
        self.broadcast_mood_combo.setCurrentIndex(0)
        self.broadcast_team_edit.clear()
        for checkbox in self.broadcast_difficulty_checkboxes.values():
            checkbox.setChecked(False)
        if self.broadcast_weather.count() > 0:
            self.broadcast_weather.setCurrentIndex(0)
        if self.broadcast_coffee.count() > 0:
            self.broadcast_coffee.setCurrentIndex(0)
        self.broadcast_coffee_level.clear()
        self.broadcast_engineering.setCurrentText("")
        self.broadcast_incidents.clear()
        self.stream_title_list.clear()
        self.live_notification_list.clear()
        self.refresh_top_bar_summary()
        self.status_label.setText("Broadcast Desk cleared")

    def save_broadcast_to_obs(self) -> None:
        title_item = self.stream_title_list.currentItem()
        notification_item = self.live_notification_list.currentItem()
        if not title_item or not notification_item:
            self.status_label.setText("Click a title and a notification in the lists first, then Save to OBS")
            return
        try:
            payload = {
                "Title": title_item.text(),
                "Notification": notification_item.text(),
                "Team": self.broadcast_team_edit.text().strip(),
                "Expedition": self._broadcast_location_text(),
                "Difficulty": self._current_difficulty_text(),
                "Objective": self.broadcast_goal_edit.text().strip(),
                "Weather": self.broadcast_weather.currentText(),
                "Coffee": self.broadcast_coffee.currentText(),
                "CoffeeLevel": self.broadcast_coffee_level.text(),
                "Engineering": self.broadcast_engineering.currentText(),
                "Incidents": self.broadcast_incidents.text(),
            }
            self.current_broadcast_path.parent.mkdir(parents=True, exist_ok=True)
            self.current_broadcast_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=4), encoding="utf-8"
            )
            self.status_label.setText(
                "Saved to OBS (CurrentBroadcast.json) - matching OBS text sources not wired up yet"
            )
        except OSError as exc:
            self.status_label.setText(f"Save to OBS failed: {exc}")

    def archive_broadcast(self) -> None:
        title_item = self.stream_title_list.currentItem()
        notification_item = self.live_notification_list.currentItem()
        if not title_item or not notification_item:
            self.status_label.setText("Click a title and a notification in the lists first, then Save to Archive")
            return
        try:
            focus = self.broadcast_focus_combo.currentText()
            location = self._broadcast_location_text() or "the field"
            goal = self.broadcast_goal_edit.text().strip()
            mood = self.broadcast_mood_combo.currentText()
            team = self.broadcast_team_edit.text().strip()
            difficulty = self._current_difficulty_text()
            weather = self.broadcast_weather.currentText()
            coffee = self.broadcast_coffee.currentText()
            coffee_level = self.broadcast_coffee_level.text()
            engineering = self.broadcast_engineering.currentText()
            incidents = self.broadcast_incidents.text()
            title = title_item.text()
            notification = notification_item.text()

            def build_lines(report_id: str, number: int) -> list[str]:
                return [
                    f"# Broadcast {report_id}",
                    "",
                    f"- Expedition Type: {focus}",
                    f"- Location / Content: {location}",
                    f"- Difficulty: {difficulty or 'None recorded'}",
                    f"- Tonight's Goal: {goal or 'None recorded'}",
                    f"- Weather: {weather}",
                    f"- Coffee: {coffee}",
                    f"- Coffee Level: {coffee_level or 'None recorded'}",
                    f"- Engineering: {engineering or 'None recorded'}",
                    f"- Incidents: {incidents or 'None recorded'}",
                    f"- Tone: {mood}",
                    f"- Team: {team or 'None recorded'}",
                    f"- Title: {title}",
                    f"- Notification: {notification}",
                    f"- Filed: {datetime.now().isoformat(timespec='seconds')}",
                    "",
                ]

            report_id, path = self.archive_service.file_form("EX", build_lines)
            self.status_label.setText(f"Broadcast archived: {report_id} ({path.name})")
        except OSError as exc:
            self.status_label.setText(f"Broadcast archive failed: {exc}")

    @staticmethod
    def _eso_run_content() -> list[str]:
        # Full list of Trials, base Dungeons, and DLC Dungeons pulled directly
        # from the parsed ESO achievement category tree (esoAchievementData50.php),
        # so this stays accurate to the actual game rather than a hand-typed
        # subset. The combo box is editable, so anything missing (very recent
        # zones not yet in that data export) can still be typed in manually.
        return [
            "Aetherian Archive", "Arx Corinium", "Asylum Sanctorium", "Bal Sunnar",
            "Banished Cells I", "Banished Cells II", "Bedlam Veil", "Black Drake Villa",
            "Black Gem Foundry", "Blackheart Haven", "Blessed Crucible", "Bloodroot Forge",
            "Castle Thorn", "City of Ash I", "City of Ash II", "Cloudrest", "Coral Aerie",
            "Cradle of Shadows", "Crypt of Hearts I", "Crypt of Hearts II",
            "Darkshade Caverns I", "Darkshade Caverns II", "Depths of Malatar",
            "Direfrost Keep", "Dread Cellar", "Dreadsail Reef", "Earthen Root Enclave",
            "Elden Hollow I", "Elden Hollow II", "Exiled Redoubt", "Falkreath Hold",
            "Fang Lair", "Frostvault", "Fungal Grotto I", "Fungal Grotto II",
            "Graven Deep", "Halls of Fabrication", "Hel Ra Citadel", "Icereach",
            "Imperial City Prison", "Kyne's Aegis", "Lair of Maarselok", "Lep Seclusa",
            "Lucent Citadel", "March of Sacrifices", "Maw of Lorkhaj", "Moon Hunter Keep",
            "Moongrave Fane", "Naj-Caldeesh", "Oathsworn Pit", "Ossein Cage",
            "Red Petal Bastion", "Rockgrove", "Ruins of Mazzatun", "Sanctum Ophidia",
            "Sanity's Edge", "Scalecaller Peak", "Scrivener's Hall", "Selene's Web",
            "Shipwright's Regret", "Spindleclutch I", "Spindleclutch II", "Stone Garden",
            "Sunspire", "Tempest Island", "The Cauldron", "Unhallowed Grave",
            "Vaults of Madness", "Volenfell", "Wayrest Sewers I", "Wayrest Sewers II",
            "White Gold Tower",
            # Arenas (solo/duo, but achievement hunters track these too)
            "Blackrose Prison", "Dragonstar Arena", "Maelstrom Arena", "Vateshran Hollows",
        ]

    def _achievement_payload(self) -> dict:
        targets = []
        for target, in_progress, complete in zip(
            self.achievement_target_edits,
            self.achievement_progress_cbs,
            self.achievement_complete_cbs,
        ):
            if target.text().strip() or in_progress.isChecked() or complete.isChecked():
                targets.append({
                    "name": target.text().strip(),
                    "in_progress": in_progress.isChecked(),
                    "complete": complete.isChecked(),
                })
        return {
            "run_id": self.achievement_run_id_label.text(),
            "date": self.achievement_date_edit.text().strip(),
            "content": self.achievement_content_combo.currentText().strip(),
            "group_size": self.achievement_group_size.value(),
            "difficulty": [name for name, box in (
                ("Normal", self.achievement_normal_cb), ("Veteran", self.achievement_veteran_cb),
                ("Hard Mode", self.achievement_hard_mode_cb), ("Perfecta", self.achievement_perfecta_cb),
            ) if box.isChecked()],
            "run_type": [name for name, box in (
                ("Full Clear", self.achievement_full_clear_cb), ("Achievements Only", self.achievement_only_cb),
                ("Speed Run", self.achievement_speed_run_cb), ("Teaching Run", self.achievement_teaching_cb),
            ) if box.isChecked()],
            "targets": targets,
            "notes": self.achievement_notes.toPlainText().strip(),
            "lessons": self.achievement_lessons.toPlainText().strip(),
            "next_steps": self.achievement_next_steps.toPlainText().strip(),
            "result": next((name for name, box in (
                ("Success", self.achievement_success_cb), ("Partial Success", self.achievement_partial_cb),
                ("Not Today", self.achievement_not_today_cb),
            ) if box.isChecked()), ""),
            "final_time": self.achievement_time_edit.text().strip(),
        }

    def _apply_achievement_payload(self, data: dict) -> None:
        self.achievement_run_id_label.setText(data.get("run_id") or "AR-—")
        self.achievement_date_edit.setText(data.get("date", datetime.now().strftime("%m / %d / %Y")))
        self.achievement_content_combo.setCurrentText(data.get("content", ""))
        self.achievement_group_size.setValue(int(data.get("group_size", 4)))
        for name, box in (("Normal", self.achievement_normal_cb), ("Veteran", self.achievement_veteran_cb), ("Hard Mode", self.achievement_hard_mode_cb), ("Perfecta", self.achievement_perfecta_cb)):
            box.setChecked(name in data.get("difficulty", []))
        for name, box in (("Full Clear", self.achievement_full_clear_cb), ("Achievements Only", self.achievement_only_cb), ("Speed Run", self.achievement_speed_run_cb), ("Teaching Run", self.achievement_teaching_cb)):
            box.setChecked(name in data.get("run_type", []))
        for index, target in enumerate(data.get("targets", [])[:5]):
            self.achievement_target_edits[index].setText(target.get("name", ""))
            self.achievement_progress_cbs[index].setChecked(bool(target.get("in_progress")))
            self.achievement_complete_cbs[index].setChecked(bool(target.get("complete")))
        self.achievement_notes.setPlainText(data.get("notes", ""))
        self.achievement_lessons.setPlainText(data.get("lessons", ""))
        self.achievement_next_steps.setPlainText(data.get("next_steps", ""))
        result = data.get("result", "")
        self.achievement_success_cb.setChecked(result == "Success")
        self.achievement_partial_cb.setChecked(result == "Partial Success")
        self.achievement_not_today_cb.setChecked(result == "Not Today")
        self.achievement_time_edit.setText(data.get("final_time", ""))

    def clear_achievement_run(self) -> None:
        self._apply_achievement_payload({})
        for target, in_progress, complete in zip(self.achievement_target_edits, self.achievement_progress_cbs, self.achievement_complete_cbs):
            target.clear()
            in_progress.setChecked(False)
            complete.setChecked(False)
        self.status_label.setText("Achievement run form cleared")

    def save_achievement_to_obs(self) -> None:
        try:
            payload = self._achievement_payload()
            self.current_achievement_run_path.parent.mkdir(parents=True, exist_ok=True)
            self.current_achievement_run_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=4), encoding="utf-8"
            )
            self.status_label.setText(
                "Saved to OBS (CurrentAchievementRun.json) - matching OBS text sources not wired up yet, see AR_ note"
            )
        except OSError as exc:
            self.status_label.setText(f"Save to OBS failed: {exc}")

    def save_achievement_draft(self) -> None:
        try:
            self.achievement_draft_path.parent.mkdir(parents=True, exist_ok=True)
            self.achievement_draft_path.write_text(json.dumps(self._achievement_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
            self.status_label.setText("Achievement run draft saved")
        except OSError as exc:
            self.status_label.setText(f"Achievement draft failed: {exc}")

    def load_achievement_draft(self) -> None:
        try:
            data = json.loads(self.achievement_draft_path.read_text(encoding="utf-8"))
            self.clear_achievement_run()
            self._apply_achievement_payload(data)
            self.status_label.setText("Achievement run draft loaded")
        except (OSError, json.JSONDecodeError) as exc:
            self.status_label.setText(f"Achievement draft unavailable: {exc}")

    def archive_achievement_run(self) -> None:
        data = self._achievement_payload()
        try:
            def build_lines(run_id: str, _number: int) -> list[str]:
                target_lines = [f"- {'✓' if target['complete'] else '•'} {target['name'] or 'Untitled achievement'}" for target in data["targets"]]
                return [
                    f"# Achievement Run {run_id}", "", f"- Date: {data['date']}",
                    f"- Dungeon / Trial: {data['content'] or 'Unspecified'}", f"- Group Size: {data['group_size']}",
                    f"- Difficulty: {', '.join(data['difficulty']) or 'Unspecified'}", f"- Run Type: {', '.join(data['run_type']) or 'Unspecified'}", "",
                    "## Achievements Targeted", *(target_lines or ["- None listed"]), "",
                    "## Run Notes / Key Moments", data["notes"] or "No notes recorded.", "",
                    "## Lessons Learned / Improvements", data["lessons"] or "No lessons recorded.", "",
                    "## What's Next?", data["next_steps"] or "No follow-up recorded.", "",
                    f"- Result: {data['result'] or 'Not recorded'}", f"- Final Score / Time: {data['final_time'] or 'Not recorded'}",
                ]

            run_id, archive_path = self.archive_service.file_form("AR", build_lines)
            self.achievement_run_id_label.setText(run_id)
            self.save_achievement_draft()
            self.stream_event_service.fire_event(
                log_label=f"Achievement Run filed: {run_id} | {data['content'] or 'Unspecified'}"
            )
            self.status_label.setText(f"Achievement run archived: {archive_path.name}")
        except OSError as exc:
            self.status_label.setText(f"Achievement archive failed: {exc}")

    def _load_stream_session(self) -> None:
        session = self.stream_event_service.load_session()
        self.current_boss_edit.setText(session.get("CurrentBoss", ""))
        self._refresh_session_labels(session)

    def _refresh_session_labels(self, session: dict) -> None:
        self.total_pulls_label.setText(f"Total Pulls: {session.get('TotalPulls', 0)}")
        self.boss_pulls_label.setText(f"Pulls on Boss: {session.get('BossPulls', 0)}")
        self.boss_wipes_label.setText(f"Wipes on Boss: {session.get('BossWipes', 0)}")

    def reset_stream_session(self) -> None:
        self.current_boss_edit.clear()
        session = {"TotalPulls": 0, "CurrentBoss": "", "BossPulls": 0, "BossWipes": 0}
        self.stream_event_service.save_session(session)
        self._refresh_session_labels(session)
        self.status_label.setText("Stream session counters reset")

    def on_pull_starts(self) -> None:
        session = self.stream_event_service.load_session()
        boss = self.current_boss_edit.text()
        if session.get("CurrentBoss", "") != boss:
            session["BossPulls"] = 0
            session["BossWipes"] = 0
            session["CurrentBoss"] = boss
        session["TotalPulls"] = session.get("TotalPulls", 0) + 1
        session["BossPulls"] = session.get("BossPulls", 0) + 1
        self.stream_event_service.save_session(session)
        self._refresh_session_labels(session)

        boss_label = boss or "Unnamed Boss"
        pull_summary = f"Pull Starts | Boss: {boss_label} | Pull #{session['BossPulls']} (Total: {session['TotalPulls']})"

        if self.first_pull_cb.isChecked():
            self.stream_event_service.fire_event(chapter_label=f"First Pull: {boss_label}")
            self.first_pull_cb.setChecked(False)
            self.status_label.setText(f"Pull started - chapter marked (First Pull: {boss})")
        else:
            self.stream_event_service.fire_event(log_label=pull_summary)
            self.status_label.setText(f"Pull #{session['BossPulls']} started on {boss_label}")

    def on_ult_pull(self) -> None:
        boss = self.current_boss_edit.text()
        self.stream_event_service.fire_event(chapter_label=f"Ult Pull: {boss or 'Unnamed Boss'}")
        self.status_label.setText(f"Ult pull marked ({boss}) - counters untouched")

    def _flash_widget(self, widget, color: str = "#c9a227", duration_ms: int = 450) -> None:
        original_style = widget.styleSheet()
        widget.setStyleSheet(f"background-color: {color}; font-weight: bold;")
        QTimer.singleShot(duration_ms, lambda: widget.setStyleSheet(original_style))

    def on_wipe(self) -> None:
        session = self.stream_event_service.load_session()
        boss = self.current_boss_edit.text()
        session["BossWipes"] = session.get("BossWipes", 0) + 1
        self.stream_event_service.save_session(session)
        self._refresh_session_labels(session)
        self._flash_widget(self.boss_wipes_label)

        percent = self.wipe_percent_spin.value()
        boss_label = boss or "Unnamed Boss"
        wipe_summary = (
            f"Wipe | Boss: {boss_label} | Wipe #{session['BossWipes']} on Pull #{session.get('BossPulls', 0)} "
            f"| Reached: {percent}%"
        )
        narrator_text = ""
        if not self.rough_night_cb.isChecked():
            narrator_text = self.narrator_service.pick("Wipes")
        self.stream_event_service.fire_event(narrator_text=narrator_text, log_label=wipe_summary)
        self.status_label.setText(f"✅ Wipe #{session['BossWipes']} recorded on {boss_label} at {percent}%")

    def on_boss_clear(self) -> None:
        session = self.stream_event_service.load_session()
        boss = self.current_boss_edit.text()
        pulls = session.get("BossPulls", 0)
        wipes = session.get("BossWipes", 0)
        self.stream_event_service.append_boss_log(boss, pulls, wipes)

        boss_label = boss or "Unnamed Boss"
        narrator_text = self.narrator_service.pick("BossClear")
        self.stream_event_service.fire_event(
            chapter_label=f"Boss Clear: {boss_label} (Pulls: {pulls}, Wipes: {wipes})",
            narrator_text=narrator_text,
        )

        session["BossPulls"] = 0
        session["BossWipes"] = 0
        self.stream_event_service.save_session(session)
        self._refresh_session_labels(session)
        self.status_label.setText(f"Boss clear logged: {boss}")

    def post_narrator_note(self, category: str) -> None:
        narrator_text = self.narrator_service.pick(category)
        self.stream_event_service.fire_event(narrator_text=narrator_text)
        self.status_label.setText(f"Posted a {category} note")

    def on_brb(self) -> None:
        narrator_text = self.narrator_service.pick("BRB")
        self.stream_event_service.fire_event(chapter_label="BRB", narrator_text=narrator_text)
        self.obs_websocket_service.switch_scene(self.brb_scene_name)
        self.status_label.setText("BRB - chapter marked; switching OBS scene")

    def on_end_of_stream(self) -> None:
        narrator_text = self.narrator_service.pick("EndOfStream")
        self.stream_event_service.fire_event(narrator_text=narrator_text)
        self.obs_websocket_service.switch_scene(self.end_of_stream_scene_name)
        self.status_label.setText("End of stream - switching OBS scene")

    def _build_odds_and_ends_page(self) -> QWidget:
        page = QWidget()
        outer_layout = QVBoxLayout(page)

        header = QLabel("Collections — Achievements")
        
        outer_layout.addWidget(header)

        search_row = QHBoxLayout()
        self.odds_search_edit = QLineEdit()
        self.odds_search_edit.setPlaceholderText("Search achievements by name...")
        self.odds_search_edit.returnPressed.connect(self.run_odds_search)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.run_odds_search)
        clear_btn = QPushButton("Clear Search")
        clear_btn.clicked.connect(self.clear_odds_search)
        search_row.addWidget(self.odds_search_edit)
        search_row.addWidget(search_btn)
        search_row.addWidget(clear_btn)
        outer_layout.addLayout(search_row)

        sheets_row = QHBoxLayout()
        self.odds_sheets_status_label = QLabel("Google Sheets: not connected")
        connect_sheets_btn = QPushButton("Connect to Google Sheets")
        connect_sheets_btn.clicked.connect(self.connect_google_sheets)
        sheets_row.addWidget(self.odds_sheets_status_label)
        sheets_row.addWidget(connect_sheets_btn)
        sheets_row.addStretch(1)
        outer_layout.addLayout(sheets_row)

        self.odds_progress_label = QLabel(f"Locally marked complete: {self.achievement_progress_service.completed_count()}")
        outer_layout.addWidget(self.odds_progress_label)

        # Master-detail split: category headings on the left act as their own
        # submenu; picking one loads its subcategories/achievements on the right.
        split_row = QHBoxLayout()

        self.odds_category_list = QListWidget()
        self.odds_category_list.setMaximumWidth(240)
        self.odds_category_list.addItems(self.eso_data_service.top_categories())
        self.odds_category_list.currentItemChanged.connect(self.on_odds_category_selected)
        split_row.addWidget(self.odds_category_list)

        detail_column = QVBoxLayout()
        self.odds_category_heading = QLabel("Select a category on the left")
        
        detail_column.addWidget(self.odds_category_heading)

        self.odds_tree = QTreeWidget()
        self.odds_tree.setHeaderLabels(["Achievement", "Points"])
        self.odds_tree.setColumnWidth(0, 380)
        self.odds_tree.itemExpanded.connect(self.on_odds_tree_expanded)
        self.odds_tree.itemChanged.connect(self.on_odds_item_changed)
        detail_column.addWidget(self.odds_tree)

        self.odds_search_results = QTreeWidget()
        self.odds_search_results.setHeaderLabels(["Achievement", "Category", "Points"])
        self.odds_search_results.itemChanged.connect(self.on_odds_item_changed)
        self.odds_search_results.hide()
        detail_column.addWidget(self.odds_search_results)

        split_row.addLayout(detail_column, 1)
        outer_layout.addLayout(split_row)

        return page

    def on_odds_category_selected(self, current, previous) -> None:
        if current is None:
            return
        category = current.text()
        self.odds_category_heading.setText(category)
        self._populate_odds_subcategories(category)

    def _populate_odds_subcategories(self, category: str) -> None:
        self.odds_tree.blockSignals(True)
        self.odds_tree.clear()
        for subcategory in self.eso_data_service.subcategories(category):
            item = QTreeWidgetItem([subcategory, ""])
            item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "subcategory", "category": category, "subcategory": subcategory})
            item.addChild(QTreeWidgetItem(["Loading...", ""]))  # placeholder so it's expandable
            self.odds_tree.addTopLevelItem(item)
        self.odds_tree.blockSignals(False)

    def on_odds_tree_expanded(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("kind") != "subcategory" or data.get("loaded"):
            return

        self.odds_tree.blockSignals(True)
        item.takeChildren()
        achievements = self.eso_data_service.achievements_in(data["category"], data["subcategory"])
        for achievement in achievements:
            self._add_achievement_leaf(item, achievement)
        data["loaded"] = True
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        self.odds_tree.blockSignals(False)

    def _add_achievement_leaf(self, parent: QTreeWidgetItem, achievement: dict) -> QTreeWidgetItem:
        leaf = QTreeWidgetItem([achievement["name"], str(achievement["points"])])
        leaf.setData(0, Qt.ItemDataRole.UserRole, {"kind": "achievement", "id": achievement["id"], "name": achievement["name"]})
        leaf.setToolTip(0, achievement.get("desc", ""))
        leaf.setFlags(leaf.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        checked = self.achievement_progress_service.is_complete(achievement["id"])
        leaf.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        parent.addChild(leaf)
        return leaf

    def run_odds_search(self) -> None:
        query = self.odds_search_edit.text().strip()
        if not query:
            self.clear_odds_search()
            return

        results = self.eso_data_service.search(query)
        self.odds_tree.hide()
        self.odds_search_results.show()
        self.odds_search_results.blockSignals(True)
        self.odds_search_results.clear()
        for result in results:
            item = QTreeWidgetItem([result["name"], f"{result['category']} / {result['subcategory']}", str(result["points"])])
            item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "achievement", "id": result["id"], "name": result["name"]})
            item.setToolTip(0, result.get("desc", ""))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            checked = self.achievement_progress_service.is_complete(result["id"])
            item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.odds_search_results.addTopLevelItem(item)
        self.odds_search_results.blockSignals(False)
        self.status_label.setText(f"Found {len(results)} matching achievements")

    def clear_odds_search(self) -> None:
        self.odds_search_edit.clear()
        self.odds_search_results.hide()
        self.odds_search_results.clear()
        self.odds_tree.show()

    def on_odds_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("kind") != "achievement":
            return

        checked = item.checkState(0) == Qt.CheckState.Checked
        achievement_id = data["id"]
        achievement_name = data["name"]
        self.achievement_progress_service.set_complete(achievement_id, checked)
        self.odds_progress_label.setText(
            f"Locally marked complete: {self.achievement_progress_service.completed_count()}"
        )

        if self.google_sheets_connected:
            try:
                written = self.google_sheets_service.set_status(achievement_name, self.google_sheets_person, checked)
                if written:
                    self.status_label.setText(f"Synced '{achievement_name}' to Google Sheets")
                else:
                    self.status_label.setText(f"'{achievement_name}' not found in your Google Sheet - saved locally only")
            except Exception as exc:  # pragma: no cover - network/auth failures
                self.status_label.setText(f"Google Sheets sync failed: {exc}")

    def connect_google_sheets(self) -> None:
        self.odds_sheets_status_label.setText("Google Sheets: building index (this can take a moment)...")
        QApplication.processEvents()
        try:
            count = self.google_sheets_service.build_index()
            self.google_sheets_connected = True
            self.odds_sheets_status_label.setText(f"Google Sheets: connected ({count} achievements indexed)")
        except GoogleSheetsNotConfigured as exc:
            self.google_sheets_connected = False
            self.odds_sheets_status_label.setText(f"Google Sheets: not configured - {exc}")
        except Exception as exc:  # pragma: no cover - network/auth/library failures
            self.google_sheets_connected = False
            self.odds_sheets_status_label.setText(f"Google Sheets: connection failed - {exc}")

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form = QFormLayout()
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
        self.current_path_edit.setText(settings["CurrentExpeditionPath"])
        self.current_incident_edit.setText(settings["CurrentIncidentPath"])
        self.field_note_counter_edit.setText(settings["FieldNoteCounterPath"])
        self.counters_folder_edit.setText(settings["CountersFolder"])
        self.archive_folder_edit.setText(settings["ArchiveFolder"])
        self.weather_folder_edit.setText(settings["WeatherFolder"])
        self.brb_scene_edit.setText(settings["BrbSceneName"])
        self.end_of_stream_scene_edit.setText(settings["EndOfStreamSceneName"])
        self.obs_websocket_host_edit.setText(settings["ObsWebSocketHost"])
        self.obs_websocket_port_edit.setText(str(settings["ObsWebSocketPort"]))
        self.obs_websocket_password_edit.setText(settings["ObsWebSocketPassword"])

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

    def _build_incident_page(self) -> QWidget:
        self.incident_tab = QWidget()
        layout = QVBoxLayout(self.incident_tab)

        self.incident_report_number_label = QLabel("Unfiled")
        
        report_row = QHBoxLayout()
        report_row.addWidget(QLabel("Report Number:"))
        report_row.addWidget(self.incident_report_number_label)
        report_row.addStretch(1)
        layout.addLayout(report_row)

        grid = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()

        left.addWidget(self._make_section("Location", self.inc_location))
        left.addWidget(self._make_section("Department", self.inc_department))
        left.addWidget(self._make_section("Severity", self.inc_severity))
        left.addWidget(self._make_section("Summary", self.inc_summary))
        left.addWidget(self._make_section("Suspected Cause", self.inc_suspected_cause))
        left.addWidget(self._make_section("Engineering Assessment", self.inc_engineering_assessment))
        left.addWidget(self._make_section("Coffee Recommendation", self.inc_coffee_recommendation))
        left.addWidget(self._make_incident_responsible_panel())

        right.addWidget(self._make_section("Observations", self.inc_observations))
        right.addWidget(self._make_section("Actions Taken", self.inc_actions_taken))
        right.addWidget(self._make_section("Recommendations", self.inc_recommendations))
        right.addWidget(self._make_section("Outstanding Questions", self.inc_outstanding_questions))
        right.addWidget(self._make_incident_status_panel())

        grid.addLayout(left)
        grid.addLayout(right)
        layout.addLayout(grid)

        actions = QHBoxLayout()
        self.incident_clear_btn = QPushButton("Clear")
        self.incident_save_btn = QPushButton("Save to OBS")
        self.incident_file_btn = QPushButton("Save to Archive")
        self.incident_load_btn = QPushButton("Load Incident")

        self.incident_clear_btn.clicked.connect(self.clear_incident)
        self.incident_save_btn.clicked.connect(self.save_incident)
        self.incident_load_btn.clicked.connect(self.load_incident)
        self.incident_file_btn.clicked.connect(self.file_incident_report)

        actions.addWidget(self.incident_clear_btn)
        actions.addWidget(self.incident_save_btn)
        actions.addWidget(self.incident_file_btn)
        actions.addWidget(self.incident_load_btn)
        layout.addLayout(actions)

        return self.incident_tab

    def _make_incident_responsible_panel(self) -> QGroupBox:
        box = QGroupBox("Responsible Party")
        layout = QVBoxLayout(box)

        self.inc_party_checkboxes: dict[str, QCheckBox] = {}
        for field_name, label in RESPONSIBLE_PARTY_LABELS.items():
            checkbox = QCheckBox(label)
            self.inc_party_checkboxes[field_name] = checkbox
            layout.addWidget(checkbox)
        return box

    def _make_incident_status_panel(self) -> QGroupBox:
        box = QGroupBox("Status")
        layout = QVBoxLayout(box)

        self.inc_status_checkboxes: dict[str, QCheckBox] = {}
        for field_name, label in INCIDENT_STATUS_LABELS.items():
            checkbox = QCheckBox(label)
            self.inc_status_checkboxes[field_name] = checkbox
            layout.addWidget(checkbox)
        return box

    def _build_reference_browser_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Composition Engine")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.reference_library = ReferenceLibrary(str(Path(__file__).resolve().parents[1] / "console" / "game_data" / "eso"))
        self.reference_data_page = QWidget()
        self.reference_data_layout = QVBoxLayout(self.reference_data_page)

        controls = QHBoxLayout()
        self.reference_search_edit = QLineEdit()
        self.reference_search_edit.setPlaceholderText("Search by name")
        self.reference_search_edit.textChanged.connect(self._refresh_reference_data_view)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._reload_reference_library)
        controls.addWidget(self.reference_search_edit, 1)
        controls.addWidget(refresh_btn)
        self.reference_data_layout.addLayout(controls)

        explorer_splitter = QSplitter(Qt.Orientation.Horizontal)
        explorer_splitter.setChildrenCollapsible(False)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.reference_dataset_list = QListWidget()
        self.reference_dataset_list.currentRowChanged.connect(self._populate_reference_dataset)
        left_layout.addWidget(self.reference_dataset_list)
        explorer_splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)
        self.reference_table = QTableView()
        self.reference_table.setAlternatingRowColors(True)
        self.reference_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.reference_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.reference_table.clicked.connect(self._show_reference_row_details)
        self.reference_table.setSortingEnabled(True)
        right_layout.addWidget(self.reference_table)

        self.reference_inspector = QTextEdit()
        self.reference_inspector.setReadOnly(True)
        self.reference_inspector.setPlaceholderText("Select a row to inspect the full JSON object.")
        right_layout.addWidget(self.reference_inspector)
        explorer_splitter.addWidget(right_panel)
        explorer_splitter.setSizes([260, 760])
        self.reference_data_layout.addWidget(explorer_splitter, 1)

        relationship_panel = QWidget()
        relationship_layout = QVBoxLayout(relationship_panel)
        relationship_layout.setContentsMargins(0, 12, 0, 0)
        relationship_title = QLabel("Relationship Explorer")
        relationship_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        relationship_layout.addWidget(relationship_title)

        relationship_controls = QHBoxLayout()
        self.relationship_query_edit = QLineEdit()
        self.relationship_query_edit.setPlaceholderText("Search for an effect like Major Courage")
        self.relationship_query_edit.returnPressed.connect(self._run_relationship_query)
        relationship_run_btn = QPushButton("Query")
        relationship_run_btn.clicked.connect(self._run_relationship_query)
        relationship_controls.addWidget(self.relationship_query_edit, 1)
        relationship_controls.addWidget(relationship_run_btn)
        relationship_layout.addLayout(relationship_controls)

        self.relationship_output = QTextEdit()
        self.relationship_output.setReadOnly(True)
        self.relationship_output.setPlaceholderText("Relationship results will appear here.")
        relationship_layout.addWidget(self.relationship_output, 1)
        self.reference_data_layout.addWidget(relationship_panel)

        layout.addWidget(self.reference_data_page)
        self._build_reference_data_explorer()
        return page

    @property
    def inc_location(self) -> QLineEdit:
        if not hasattr(self, "_inc_location"):
            self._inc_location = self._build_field("Location")
        return self._inc_location

    @property
    def inc_department(self) -> QLineEdit:
        if not hasattr(self, "_inc_department"):
            self._inc_department = self._build_field("Department")
        return self._inc_department

    @property
    def inc_severity(self) -> QComboBox:
        if not hasattr(self, "_inc_severity"):
            self._inc_severity = QComboBox()
            for option in SEVERITY_OPTIONS:
                self._inc_severity.addItem(option)
        return self._inc_severity

    @property
    def inc_summary(self) -> QTextEdit:
        if not hasattr(self, "_inc_summary"):
            self._inc_summary = QTextEdit()
            self._inc_summary.setPlaceholderText("Summary")
        return self._inc_summary

    @property
    def inc_suspected_cause(self) -> QLineEdit:
        if not hasattr(self, "_inc_suspected_cause"):
            self._inc_suspected_cause = self._build_field("Suspected Cause")
        return self._inc_suspected_cause

    @property
    def inc_engineering_assessment(self) -> QTextEdit:
        if not hasattr(self, "_inc_engineering_assessment"):
            self._inc_engineering_assessment = QTextEdit()
            self._inc_engineering_assessment.setPlaceholderText("Engineering Assessment")
        return self._inc_engineering_assessment

    @property
    def inc_coffee_recommendation(self) -> QLineEdit:
        if not hasattr(self, "_inc_coffee_recommendation"):
            self._inc_coffee_recommendation = self._build_field("Coffee Recommendation")
        return self._inc_coffee_recommendation

    @property
    def inc_observations(self) -> QTextEdit:
        if not hasattr(self, "_inc_observations"):
            self._inc_observations = QTextEdit()
            self._inc_observations.setPlaceholderText("Observations")
        return self._inc_observations

    @property
    def inc_actions_taken(self) -> QTextEdit:
        if not hasattr(self, "_inc_actions_taken"):
            self._inc_actions_taken = QTextEdit()
            self._inc_actions_taken.setPlaceholderText("Actions Taken")
        return self._inc_actions_taken

    @property
    def inc_recommendations(self) -> QTextEdit:
        if not hasattr(self, "_inc_recommendations"):
            self._inc_recommendations = QTextEdit()
            self._inc_recommendations.setPlaceholderText("Recommendations")
        return self._inc_recommendations

    @property
    def inc_outstanding_questions(self) -> QTextEdit:
        if not hasattr(self, "_inc_outstanding_questions"):
            self._inc_outstanding_questions = QTextEdit()
            self._inc_outstanding_questions.setPlaceholderText("Outstanding Questions")
        return self._inc_outstanding_questions

    def _dataset_key_from_label(self, item_text: str) -> str:
        normalized = item_text.split(" (")[0].strip().casefold().replace(" ", "_")
        mapping = {
            "skills": "skills",
            "gear_sets": "gear_sets",
            "champion_points": "champion_points",
            "foods": "foods",
            "potions": "potions",
            "encounters": "encounters",
            "mechanics": "mechanics",
            "buff": "buff",
            "debuffs": "debuffs",
            "status_effects": "status_effects",
            "races": "races",
            "guild_passives": "guild_passives",
            "weapon_passives": "weapon_passives",
            "armor_passives": "armor_passives",
        }
        return mapping.get(normalized, normalized)

    def _build_reference_data_explorer(self) -> None:
        self.reference_dataset_list.clear()
        self.reference_model = ReferenceDataTableModel([])
        self.reference_table.setModel(self.reference_model)

        dataset_names = [
            "skills",
            "gear_sets",
            "champion_points",
            "foods",
            "potions",
            "encounters",
            "mechanics",
            "buff",
            "debuffs",
            "status_effects",
            "races",
            "guild_passives",
            "weapon_passives",
            "armor_passives",
        ]

        for dataset_name in dataset_names:
            try:
                data = self.reference_library.get_data(dataset_name)
                records = self.reference_library._records(data)
            except Exception as exc:
                records = []
                self.reference_dataset_list.addItem(f"{dataset_name} (error: {exc})")
                continue

            count = len(records)
            label = f"{dataset_name.replace('_', ' ').title()} ({count})"
            self.reference_dataset_list.addItem(label)

        if self.reference_dataset_list.count() > 0:
            self.reference_dataset_list.setCurrentRow(0)

    def _populate_reference_dataset(self, row: int) -> None:
        if row < 0:
            self.reference_inspector.clear()
            self.reference_model.set_records([])
            return

        item_text = self.reference_dataset_list.item(row).text()
        dataset_key = self._dataset_key_from_label(item_text)
        try:
            data = self.reference_library.get_data(dataset_key)
            records = self.reference_library._records(data)
        except Exception as exc:
            self.reference_model.set_records([])
            self.reference_inspector.setPlainText(f"Loading failed: {exc}")
            return

        filtered = []
        query = self.reference_search_edit.text().strip().casefold()
        for record in records:
            if not isinstance(record, dict):
                continue
            name = str(record.get("name", "")).casefold()
            if not query or query in name:
                filtered.append(record)

        self.reference_model.set_records(filtered)
        self.reference_table.resizeColumnsToContents()
        if filtered:
            self.reference_inspector.setPlainText("No selection yet. Select a row to inspect its JSON object.")
        else:
            self.reference_inspector.setPlainText("No Records")

    def _refresh_reference_data_view(self) -> None:
        current_row = self.reference_dataset_list.currentRow()
        if current_row >= 0:
            self._populate_reference_dataset(current_row)

    def _reload_reference_library(self) -> None:
        try:
            self.reference_library = ReferenceLibrary(str(Path(__file__).resolve().parents[1] / "console" / "game_data" / "eso"))
            self._build_reference_data_explorer()
            self.reference_inspector.setPlainText("ReferenceLibrary reloaded.")
        except Exception as exc:
            self.reference_inspector.setPlainText(f"Reload failed: {exc}")

    def _show_reference_row_details(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        record = self.reference_model._records[index.row()]
        self.reference_inspector.setPlainText(json.dumps(record, ensure_ascii=False, indent=2, default=str))

    def _run_relationship_query(self) -> None:
        effect = self.relationship_query_edit.text().strip()
        if not effect:
            self.relationship_output.setPlainText("Enter an effect name to search.")
            return
        try:
            result = self.reference_library.find_everything_using(effect)
            lines = [f"Effect: {effect}", ""]
            providers = result.get("providers", [])
            encounters = result.get("encounters", [])
            mechanics = result.get("mechanics", [])

            lines.append(f"Providers ({len(providers)}):")
            for provider in providers[:20]:
                lines.append(f"- {provider.get('name', 'Unnamed')} [{provider.get('source_layer', 'unknown')}]")
            if len(providers) > 20:
                lines.append(f"- ... {len(providers) - 20} more")

            lines.append("")
            lines.append(f"Encounters requiring it ({len(encounters)}):")
            for item in encounters[:20]:
                lines.append(f"- {item.get('name', 'Unnamed')}")
            if len(encounters) > 20:
                lines.append(f"- ... {len(encounters) - 20} more")

            lines.append("")
            lines.append(f"Mechanics requiring it ({len(mechanics)}):")
            for item in mechanics[:20]:
                lines.append(f"- {item.get('name', 'Unnamed')}")
            if len(mechanics) > 20:
                lines.append(f"- ... {len(mechanics) - 20} more")

            self.relationship_output.setPlainText("\n".join(lines))
        except Exception as exc:
            self.relationship_output.setPlainText(f"Relationship query failed: {exc}")

    def _collect_incident_model(self) -> IncidentModel:
        party = ResponsiblePartyFlags(
            **{name: cb.isChecked() for name, cb in self.inc_party_checkboxes.items()}
        )
        status = IncidentStatusFlags(
            **{name: cb.isChecked() for name, cb in self.inc_status_checkboxes.items()}
        )
        report_number = self.incident_report_number_label.text()
        if report_number == "Unfiled":
            report_number = ""

        return IncidentModel(
            ReportNumber=report_number,
            Location=self.inc_location.text(),
            Department=self.inc_department.text(),
            Severity=self.inc_severity.currentText(),
            Summary=self.inc_summary.toPlainText(),
            SuspectedCause=self.inc_suspected_cause.text(),
            EngineeringAssessment=self.inc_engineering_assessment.toPlainText(),
            CoffeeRecommendation=self.inc_coffee_recommendation.text(),
            Observations=self.inc_observations.toPlainText(),
            ActionsTaken=self.inc_actions_taken.toPlainText(),
            Recommendations=self.inc_recommendations.toPlainText(),
            OutstandingQuestions=self.inc_outstanding_questions.toPlainText(),
            ResponsibleParty=party,
            Status=status,
        )

    def _apply_incident_model(self, model: IncidentModel) -> None:
        self.incident_report_number_label.setText(model.ReportNumber or "Unfiled")
        self.inc_location.setText(model.Location)
        self.inc_department.setText(model.Department)
        if model.Severity in SEVERITY_OPTIONS:
            self.inc_severity.setCurrentText(model.Severity)
        elif self.inc_severity.count() > 0:
            self.inc_severity.setCurrentIndex(0)
        self.inc_summary.setPlainText(model.Summary)
        self.inc_suspected_cause.setText(model.SuspectedCause)
        self.inc_engineering_assessment.setPlainText(model.EngineeringAssessment)
        self.inc_coffee_recommendation.setText(model.CoffeeRecommendation)
        self.inc_observations.setPlainText(model.Observations)
        self.inc_actions_taken.setPlainText(model.ActionsTaken)
        self.inc_recommendations.setPlainText(model.Recommendations)
        self.inc_outstanding_questions.setPlainText(model.OutstandingQuestions)

        for field_name, checkbox in self.inc_party_checkboxes.items():
            checkbox.setChecked(getattr(model.ResponsibleParty, field_name))
        for field_name, checkbox in self.inc_status_checkboxes.items():
            checkbox.setChecked(getattr(model.Status, field_name))

    def clear_incident(self) -> None:
        self._apply_incident_model(IncidentModel())
        self.status_label.setText("Incident Report cleared")

    def load_incident(self) -> None:
        self.status_label.setText("Loading incident...")
        try:
            model = self.incident_json_service.load()
            self._apply_incident_model(model)
            self.status_label.setText("Incident loaded")
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Incident load failed: {exc}")

    def save_incident(self) -> None:
        self.status_label.setText("Saving incident...")
        try:
            model = self._collect_incident_model()
            self.incident_json_service.save(model)
            self.status_label.setText("Incident saved")
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Incident save failed: {exc}")

    def _make_section(self, label: str, widget: QWidget) -> QGroupBox:
        box = QGroupBox(label)
        layout = QVBoxLayout(box)
        layout.addWidget(widget)
        return box

    def randomize_coffee_level(self) -> None:
        self.broadcast_coffee_level.setText(f"{random.randint(0, 100)}%")

    def _build_status_checkboxes(self) -> None:
        if hasattr(self, "observe_cb"):
            return
        self.observe_cb = QCheckBox("Observe")
        self.document_cb = QCheckBox("Document")
        self.learn_cb = QCheckBox("Learn")
        self.share_cb = QCheckBox("Share the Lesson")
        self.in_progress_cb = QCheckBox("In Progress")
        self.complete_cb = QCheckBox("Complete")
        self.under_review_cb = QCheckBox("Under Review")

    def _make_clipboard_status_panel(self) -> QGroupBox:
        box = QGroupBox("Status")
        layout = QVBoxLayout(box)
        layout.addWidget(self.observe_cb)
        layout.addWidget(self.document_cb)
        layout.addWidget(self.learn_cb)
        layout.addWidget(self.share_cb)
        return box

    def _make_fieldnote_status_panel(self) -> QGroupBox:
        box = QGroupBox("Status")
        layout = QVBoxLayout(box)
        layout.addWidget(self.in_progress_cb)
        layout.addWidget(self.complete_cb)
        layout.addWidget(self.under_review_cb)
        return box

    def _build_field(self, placeholder: str) -> QLineEdit:
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        return field

    def _build_weather_selector(self) -> QComboBox:
        combo = QComboBox()
        for label in WEATHER_SOURCE_MAP:
            combo.addItem(label)
        return combo

    def _build_coffee_selector(self) -> QComboBox:
        combo = QComboBox()
        for label in COFFEE_SOURCE_MAP:
            combo.addItem(label)
        return combo

    @property
    def assignment(self) -> QTextEdit:
        if not hasattr(self, "_assignment"):
            self._assignment = QTextEdit()
            self._assignment.setPlaceholderText("Assignment")
        return self._assignment

    @property
    def observation(self) -> QTextEdit:
        if not hasattr(self, "_observation"):
            self._observation = QTextEdit()
            self._observation.setPlaceholderText("Observation")
        return self._observation

    @property
    def context(self) -> QTextEdit:
        if not hasattr(self, "_context"):
            self._context = QTextEdit()
            self._context.setPlaceholderText("Context / Conditions")
        return self._context

    @property
    def next_steps(self) -> QTextEdit:
        if not hasattr(self, "_next_steps"):
            self._next_steps = QTextEdit()
            self._next_steps.setPlaceholderText("Recommendations for Future Adventurers")
        return self._next_steps

    def _current_difficulty_text(self) -> str:
        checked = [label for label, cb in self.broadcast_difficulty_checkboxes.items() if cb.isChecked()]
        return " ".join(checked)

    def _set_difficulty_text(self, value: str) -> None:
        checked_labels = set(value.split())
        for label, checkbox in self.broadcast_difficulty_checkboxes.items():
            checkbox.setChecked(label in checked_labels)

    def refresh_top_bar_summary(self) -> None:
        """Field Office no longer owns Expedition/Difficulty/Objective/Engineering/
        Incidents - it just displays them, read-only, from Broadcast Desk (the
        actual source now). Weather/Coffee/Coffee Level live on Broadcast Desk
        only and aren't shown here at all."""
        self.top_bar_expedition_label.setText(self._broadcast_location_text() or "—")
        self.top_bar_difficulty_label.setText(self._current_difficulty_text() or "—")
        self.top_bar_objective_label.setText(self.broadcast_goal_edit.text().strip() or "—")
        self.top_bar_engineering_label.setText(self.broadcast_engineering.currentText() or "—")
        self.top_bar_incidents_label.setText(self.broadcast_incidents.text() or "—")

    def clear_expedition(self) -> None:
        self.assignment.setPlainText("")
        self.observation.setPlainText("")
        self.context.setPlainText("")
        self.next_steps.setPlainText("")
        self.observe_cb.setChecked(False)
        self.document_cb.setChecked(False)
        self.learn_cb.setChecked(False)
        self.share_cb.setChecked(False)
        self.in_progress_cb.setChecked(False)
        self.complete_cb.setChecked(False)
        self.under_review_cb.setChecked(False)
        self.status_label.setText("Field Office cleared (shared expedition data on Broadcast Desk left untouched)")

    def load_expedition(self) -> None:
        self.status_label.setText("Loading expedition...")
        try:
            model = self.json_service.load()
            self._apply_model(model)
            self.status_label.setText("Expedition loaded")
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Load failed: {exc}")

    def save_expedition(self) -> None:
        self.status_label.setText("Saving expedition...")
        try:
            model = self._collect_model()
            self.json_service.save(model)
            self.status_label.setText("Expedition saved")
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Save failed: {exc}")

    def new_field_note(self) -> None:
        self.status_label.setText("Updating field note counter...")
        try:
            counter_path = self.field_note_counter_path
            archive_folder = self.archive_path
            archive_folder.mkdir(parents=True, exist_ok=True)

            if not counter_path.exists():
                counter_path.parent.mkdir(parents=True, exist_ok=True)
                counter_path.write_text("0", encoding="utf-8")

            current_value = int(counter_path.read_text(encoding="utf-8").strip().strip('"').strip("'"))
            new_value = current_value + 1
            counter_path.write_text(str(new_value), encoding="utf-8")

            note_path = archive_folder / f"FieldNote_{new_value:04d}.md"
            note_text = "\n".join(
                [
                    "# Field Note",
                    "",
                    f"- Expedition: {self._broadcast_location_text() or 'Unknown'}",
                    f"- Objective: {self.broadcast_goal_edit.text().strip() or 'Unknown'}",
                    f"- Weather: {self.broadcast_weather.currentText() or 'Unknown'}",
                    f"- Coffee: {self.broadcast_coffee.currentText() or 'Unknown'}",
                    f"- Note: {self.observation.toPlainText().strip() or 'No observation recorded'}",
                    f"- Created: {datetime.now().isoformat(timespec='seconds')}",
                    "",
                ]
            )
            note_path.write_text(note_text, encoding="utf-8")
            self.status_label.setText(f"Field note counter: {new_value} | Note: {note_path.name}")
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Counter update failed: {exc}")

    def file_incident_report(self) -> None:
        self.status_label.setText("Filing incident report...")
        try:
            model = self._collect_incident_model()

            def build_lines(report_id: str, number: int) -> list[str]:
                party_active = [
                    RESPONSIBLE_PARTY_LABELS[name]
                    for name, checked in model.ResponsibleParty.__dict__.items()
                    if checked
                ]
                status_active = [
                    INCIDENT_STATUS_LABELS[name]
                    for name, checked in model.Status.__dict__.items()
                    if checked
                ]
                return [
                    f"# Incident Report {report_id}",
                    "",
                    f"- Location: {model.Location or 'Unknown'}",
                    f"- Department: {model.Department or 'Unknown'}",
                    f"- Severity: {model.Severity or 'Unknown'}",
                    f"- Summary: {model.Summary or 'None recorded'}",
                    f"- Suspected Cause: {model.SuspectedCause or 'Unknown'}",
                    f"- Engineering Assessment: {model.EngineeringAssessment or 'None recorded'}",
                    f"- Coffee Recommendation: {model.CoffeeRecommendation or 'None'}",
                    f"- Observations: {model.Observations or 'None recorded'}",
                    f"- Actions Taken: {model.ActionsTaken or 'None recorded'}",
                    f"- Recommendations: {model.Recommendations or 'None recorded'}",
                    f"- Outstanding Questions: {model.OutstandingQuestions or 'None'}",
                    f"- Responsible Party: {', '.join(party_active) or 'None marked'}",
                    f"- Status: {', '.join(status_active) or 'None marked'}",
                    f"- Filed: {datetime.now().isoformat(timespec='seconds')}",
                    "",
                ]

            report_id, report_path = self.archive_service.file_form("IR", build_lines)

            model.ReportNumber = report_id
            model.Status.Filed = True
            self._apply_incident_model(model)
            self.incident_json_service.save(model)

            self.status_label.setText(f"Incident filed: {report_id} ({report_path.name})")
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Incident report failed: {exc}")

    def rebuild_database(self) -> None:
        self.status_label.setText("Rebuilding database files...")
        QApplication.processEvents()
        try:
            database_path = Path(__file__).resolve().parents[1] / "console" / "game_data" / "eso"
            builder = DataBuilderService(database_path)
            results = builder.build_all()
            validator = ValidationService(database_path)
            report = validator.validate_directory()
            summary = report["summary"]
            message = (
                f"Database rebuilt: {' | '.join(results)} | "
                f"records={summary['total_records']} files={summary['present_files']} "
                f"issues={len(report['issues'])}"
            )
            self.status_label.setText(message)
            QMessageBox.information(self, "Database Rebuild", message)
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Database rebuild failed: {exc}")
            QMessageBox.critical(self, "Database Rebuild", str(exc))

    def save_settings(self) -> None:
        existing = self.settings_service.load()
        settings = {
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

    def _collect_model(self) -> ExpeditionModel:
        status = StatusFlags(
            Observe=self.observe_cb.isChecked(),
            Document=self.document_cb.isChecked(),
            Learn=self.learn_cb.isChecked(),
            ShareTheLesson=self.share_cb.isChecked(),
            InProgress=self.in_progress_cb.isChecked(),
            Complete=self.complete_cb.isChecked(),
            UnderReview=self.under_review_cb.isChecked(),
        )

        return ExpeditionModel(
            Expedition=self._broadcast_location_text(),
            Difficulty=self._current_difficulty_text(),
            Objective=self.broadcast_goal_edit.text().strip(),
            Weather=self.broadcast_weather.currentText(),
            Coffee=COFFEE_SOURCE_MAP.get(self.broadcast_coffee.currentText(), self.broadcast_coffee.currentText()),
            CoffeeLevel=self.broadcast_coffee_level.text(),
            Engineering=self.broadcast_engineering.currentText(),
            Incidents=self.broadcast_incidents.text(),
            Assignment=self.assignment.toPlainText(),
            Observation=self.observation.toPlainText(),
            Context=self.context.toPlainText(),
            NextSteps=self.next_steps.toPlainText(),
            Status=status,
        )

    def _apply_model(self, model: ExpeditionModel) -> None:
        # Expedition/Difficulty/Objective/Weather/Coffee/CoffeeLevel/Engineering/
        # Incidents now live on Broadcast Desk (the shared source) - loading a
        # saved snapshot writes back there, and Field Office's read-only
        # summary picks it up via refresh_top_bar_summary().
        if self.broadcast_location_stack.currentWidget() is self.broadcast_location_combo:
            self.broadcast_location_combo.setCurrentText(model.Expedition)
        else:
            self.broadcast_location_edit.setText(model.Expedition)
        self._set_difficulty_text(model.Difficulty)
        self.broadcast_goal_edit.setText(model.Objective)
        current_weather = model.Weather
        if current_weather in WEATHER_SOURCE_MAP:
            self.broadcast_weather.setCurrentText(current_weather)
        elif self.broadcast_weather.count() > 0:
            self.broadcast_weather.setCurrentIndex(0)
        current_coffee = model.Coffee
        for label, mapped_value in COFFEE_SOURCE_MAP.items():
            if mapped_value == current_coffee:
                self.broadcast_coffee.setCurrentText(label)
                break
        else:
            if self.broadcast_coffee.count() > 0:
                self.broadcast_coffee.setCurrentIndex(0)
        self.broadcast_coffee_level.setText(model.CoffeeLevel)
        self.broadcast_engineering.setCurrentText(model.Engineering)
        self.broadcast_incidents.setText(model.Incidents)
        self.assignment.setPlainText(model.Assignment)
        self.observation.setPlainText(model.Observation)
        self.context.setPlainText(model.Context)
        self.next_steps.setPlainText(model.NextSteps)
        self.observe_cb.setChecked(model.Status.Observe)
        self.document_cb.setChecked(model.Status.Document)
        self.learn_cb.setChecked(model.Status.Learn)
        self.share_cb.setChecked(model.Status.ShareTheLesson)
        self.in_progress_cb.setChecked(model.Status.InProgress)
        self.complete_cb.setChecked(model.Status.Complete)
        self.under_review_cb.setChecked(model.Status.UnderReview)
        self.refresh_top_bar_summary()
