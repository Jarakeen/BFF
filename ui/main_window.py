# ==================================================
# Black Feather Foundry
# main_window.py
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QWidget,
)

from engine.config import get_data_dir
from services.eso_achievement_database_service import EsoAchievementDatabaseService
from services.expedition_service import ExpeditionService
from ui.achievements_page import AchievementsPage
from ui.archive_page import ArchivePage
from ui.broadcast_page import BroadcastPage
from ui.builds_page import BuildsPage
from ui.capabilities_page import CapabilitiesPage
from ui.collectibles_page import CollectiblesPage
from ui.components.foundry_sidebar import FoundrySidebar
from ui.coverage_page import CoveragePage
from ui.encounters_page import EncountersPage
from ui.field_notes_page import FieldNotesPage
from ui.incident_page import IncidentPage
from ui.mechanics_page import MechanicsPage
from ui.operations_console import OperationsConsole
from ui.optimization_page import OptimizationPage
from ui.reference_data_page import ReferenceDataPage
from ui.roster_page import RosterPage
from ui.settings_page import SettingsPage
from ui.stream_elements_page import LiveOperationsPage


class MainWindow(QMainWindow):
    """Black Feather Foundry main window."""

    def __init__(self, expedition=None):
        super().__init__()
        data_dir = get_data_dir()
        self.eso_data_service = EsoAchievementDatabaseService(data_dir / "eso.db")
        self.expedition_service = expedition if expedition is not None else ExpeditionService()
        self.setWindowTitle("Black Feather Foundry Field Office")
        self.resize(1700, 950)
        self.build_ui()
        self.connect_signals()

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
            "achievements": AchievementsPage(),
            "collectibles": CollectiblesPage(),
            "roster_page": RosterPage(),
            "operations_console": OperationsConsole(expedition=self.expedition_service),
            "console:1": EncountersPage(expedition=self.expedition_service),
            "console:2": BuildsPage(),
            "console:3": CapabilitiesPage(),
            "console:4": MechanicsPage(expedition=self.expedition_service),
            "console:6": OptimizationPage(),
            "console:7": CoveragePage(),
            "console:8": ReferenceDataPage(),
            "settings": SettingsPage(),
        }

        self.page_containers = {}
        for name, page in self.pages.items():
            container = self.wrap_page(page)
            self.page_containers[name] = container
            self.stack.addWidget(container)

    def connect_signals(self):
        self.sidebar.pageRequested.connect(self.show_page)

    def _confirm_collectible_navigation(self, target_page: str) -> bool:
        collectibles_page = self.pages.get("collectibles")
        if collectibles_page is None or not collectibles_page.has_pending_changes():
            return True
        if self.stack.currentWidget() is not self.page_containers.get("collectibles"):
            return True

        box = QMessageBox(self)
        box.setWindowTitle("Unsaved Collection Changes")
        box.setText("You have collectible ownership changes waiting to be saved.")
        box.setInformativeText("Save them before leaving this collection, discard them, or stay here.")
        box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        answer = box.exec()

        if answer == QMessageBox.StandardButton.Save:
            collectibles_page.save_pending_changes()
            return True
        if answer == QMessageBox.StandardButton.Discard:
            collectibles_page.discard_pending_changes()
            return True
        return False

    def show_page(self, page_name: str):
        if not self._confirm_collectible_navigation(page_name):
            return

        if page_name.startswith("collectibles:"):
            category = page_name.split(":", 1)[1]
            collectibles_page = self.pages["collectibles"]
            collectibles_page.set_category(category)
            self.stack.setCurrentWidget(self.page_containers["collectibles"])
            return

        if page_name not in self.page_containers:
            print(f"[FoundryDock] Unknown navigation page: {page_name}")
            return

        self.stack.setCurrentWidget(self.page_containers[page_name])

    def wrap_page(self, page):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        scroll.setWidget(page)
        return scroll
