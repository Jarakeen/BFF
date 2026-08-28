# ==================================================
# Black Feather Foundry
#
# File:
# main_window.py
#
# Purpose:
# Main application window.
#
# ==================================================

from __future__ import annotations

import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QStackedWidget,
    QScrollArea,
    QSizePolicy,
    QApplication,
)

from engine.config import get_data_dir
from ui.foundry_theme import apply_foundry_theme
from ui.theme.foundry_palette import apply_foundry_palette
from ui.components.foundry_sidebar import FoundrySidebar
from services.eso_achievement_database_service import (
    EsoAchievementDatabaseService,
)

from ui.broadcast_page import BroadcastPage
from ui.field_notes_page import FieldNotesPage
from ui.stream_elements_page import LiveOperationsPage
from ui.archive_page import ArchivePage
from ui.incident_page import IncidentPage
# from ui.achievement_desk_page import AchievementPage
from ui.collections_page import CollectionsPage
from ui.roster_page import RosterPage
from ui.operations_console import OperationsConsole
from ui.settings_page import SettingsPage
from ui.builds_page import BuildsPage
from ui.capabilities_page import CapabilitiesPage
from ui.optimization_page import OptimizationPage
from services.expedition_service import ExpeditionService


class MainWindow(QMainWindow):
    """Black Feather Foundry main window."""

    def __init__(self, expedition=None):
        super().__init__()

        data_dir = get_data_dir()

        self.eso_data_service = EsoAchievementDatabaseService(
            data_dir / "eso.db"
        )

        app = QApplication.instance()
        if app is not None:
            apply_foundry_theme(app)
            apply_foundry_palette(app)

        self.expedition_service = (
            expedition
            if expedition is not None
            else ExpeditionService()
        )

        self.setWindowTitle("Black Feather Foundry Field Office")
        self.resize(1700, 950)

        self.build_ui()
        self.connect_signals()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = FoundrySidebar()
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.pages = {
            "broadcast": BroadcastPage(),
            "field_office": FieldNotesPage(),
            "live_operations": LiveOperationsPage(),
            "archive": ArchivePage(),
            "incident": IncidentPage(),
            # "achievement": AchievementPage(),
            "collections": CollectionsPage(),
            "roster_page": RosterPage(),
            "operations_console": OperationsConsole(
                expedition=self.expedition_service
            ),
            "console:2": BuildsPage(),
            "console:3": CapabilitiesPage(),
            "console:6": OptimizationPage(),
            "settings": SettingsPage(),
        }

        self.page_containers = {}

        for name, page in self.pages.items():
            container = self.wrap_page(page)
            self.page_containers[name] = container
            self.stack.addWidget(container)

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):
        self.sidebar.pageRequested.connect(self.show_page)

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------

    def show_page(self, page_name: str):
        if page_name not in self.page_containers:
            print(f"[FoundryDock] Unknown navigation page: {page_name}")
            return

        self.stack.setCurrentWidget(self.page_containers[page_name])

    def wrap_page(self, page):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        page.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        scroll.setWidget(page)
        return scroll
