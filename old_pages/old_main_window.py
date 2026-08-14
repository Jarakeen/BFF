# ui/main_window.py
from __future__ import annotations


import json
import random
from datetime import datetime
from pathlib import Path
import re



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

from engine.data_miner import DataBuilderService
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
from ui.theme.theme_manager import ThemeManager
from services.ai_service import AIService
from services.icon_service import IconService


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
      
        self.icons = IconService()

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
                image: url(assets/icons/check_white.svg);
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
        self.tabs.addTab(self._wrap_scrollable(self._build_reference_browser_page()),"Comp Engine")
        self.tabs.addTab(self._wrap_scrollable(self._build_settings_page()), "Settings")
        self.tabs.tabBar().hide()

        self.nav_buttons: list[tuple[QPushButton, int]] = []
        nav_sections = [
            ("CURRENT SESSION", [("Broadcast Desk", 0), ("Field Office", 1)]),
            ("STREAM OPERATIONS", [("Stream Events", 2)]),
            ("RECORDS", [("Incident Report", 4), ("Archive Log", 3)]),
            ("PROJECTS", [("Achievement Run", 5), ("Collections", 6)]),
            ("SYSTEM", [("Comp Engine", 7), ("Settings", 8)]),
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
        titles = ("BROADCAST DESK", "FIELD OFFICE", "STREAM EVENTS", "ARCHIVE LOG", "INCIDENT REPORT", "ACHIEVEMENT RUN TRACKER", "COLLECTIONS", "COMP ENGINE", "SETTINGS")
        self.tabs.setCurrentIndex(index)
        self.page_title.setText(titles[index])
        for button, page_index in self.nav_buttons:
            button.setChecked(page_index == index)
        if index == 1:  # Field Office - Expedition/Difficulty/etc. now live on Broadcast Desk
            self.refresh_top_bar_summary()

    
    

    


    

    

    
   
   
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

#    def refresh_top_bar_summary(self) -> None:
#        """Field Office no longer owns Expedition/Difficulty/Objective/Engineering/
#        Incidents - it just displays them, read-only, from Broadcast Desk (the
#        actual source now). Weather/Coffee/Coffee Level live on Broadcast Desk
#        only and aren't shown here at all."""
#        self.top_bar_expedition_label.setText(self._broadcast_location_text() or "—")
#        self.top_bar_difficulty_label.setText(self._current_difficulty_text() or "—")
#        self.top_bar_objective_label.setText(self.broadcast_goal_edit.text().strip() or "—")
#        self.top_bar_engineering_label.setText(self.broadcast_engineering.currentText() or "—")
#        self.top_bar_incidents_label.setText(self.broadcast_incidents.text() or "—")

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

    def archive_field_note(self):
        """Return the active field note text."""

        if hasattr(self, "field_notes_edit"):
            self.field_notes_edit.clear()

        if hasattr(self, "observation"):
            self.observation.clear()

        return "No observation recorded"


   
       

    