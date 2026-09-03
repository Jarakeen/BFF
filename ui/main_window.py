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
from services.optional_modules import broadcast_enabled
from ui.achievements_page import AchievementsPage
from ui.builds_page import BuildsPage
from ui.capabilities_page import CapabilitiesPage
from ui.collectibles_dashboard import CollectiblesDashboard
from ui.collectibles_page import CollectiblesPage
from ui.components.foundry_sidebar import FoundrySidebar
from ui.coverage_page import CoveragePage
from ui.encounters_page import EncountersPage
from ui.foundry_page import FoundryPage
from ui.incident_page import IncidentPage
from ui.mechanics_page import MechanicsPage
from ui.operations_console import OperationsConsole
from ui.optimization_page import OptimizationPage
from ui.reference_data_page import ReferenceDataPage
from ui.roster_page import RosterPage
from ui.settings_page import SettingsPage


class MainWindow(QMainWindow):
    """Black Feather Foundry main window."""

    def __init__(self, expedition=None):
        super().__init__()
        data_dir = get_data_dir()
        self.eso_data_service = EsoAchievementDatabaseService(data_dir / "eso.db")
        self.expedition_service = expedition if expedition is not None else ExpeditionService()
        self.broadcast_enabled = broadcast_enabled()
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

        self.sidebar = FoundrySidebar(include_broadcast=self.broadcast_enabled)
        layout.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        core_pages = {
            "achievements": AchievementsPage(),
            "collectibles": CollectiblesDashboard(),
            "collectibles_browser": CollectiblesPage(),
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
            "incident": IncidentPage(),
        }

        broadcast_pages = {}
        if self.broadcast_enabled:
            from ui.archive_page import ArchivePage
            from ui.broadcast_page import BroadcastPage
            from ui.field_notes_page import FieldNotesPage
            from ui.stream_elements_page import LiveOperationsPage

            broadcast_pages = {
                "broadcast": BroadcastPage(),
                "field_office": FieldNotesPage(),
                "live_operations": LiveOperationsPage(),
                "archive": ArchivePage(),
            }

        self.pages = {**broadcast_pages, **core_pages}

        self.page_containers = {}
        for name, page in self.pages.items():
            container = self.wrap_page(page)
            self.page_containers[name] = container
            self.stack.addWidget(container)

    def connect_signals(self):
        self.sidebar.pageRequested.connect(self.show_page)
        dashboard = self.pages.get("collectibles")
        if dashboard is not None and hasattr(dashboard, "routeRequested"):
            dashboard.routeRequested.connect(self.show_page)

    def _confirm_collectible_navigation(self, target_page: str) -> bool:
        collectibles_page = self.pages.get("collectibles_browser")
        if collectibles_page is None or not collectibles_page.has_pending_changes():
            return True
        if self.stack.currentWidget() is not self.page_containers.get("collectibles_browser"):
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

    def _active_collection_profile(self) -> str:
        achievements_page = self.pages.get("achievements")
        progress = getattr(achievements_page, "achievement_progress_service", None)
        return str(getattr(progress, "active_profile", "") or "").strip() or "Default"

    def _refresh_collectibles_for_active_profile(self) -> None:
        """Keep the dashboard and category browser aligned to Achievements."""
        profile = self._active_collection_profile()
        collectibles_page = self.pages.get("collectibles_browser")
        service = getattr(collectibles_page, "service", None)
        if service is not None and hasattr(service, "set_active_profile"):
            service.set_active_profile(profile)
            reload_combo = getattr(collectibles_page, "_reload_profile_combo", None)
            if callable(reload_combo):
                reload_combo(profile)
        if collectibles_page is not None:
            collectibles_page.refresh()

        dashboard = self.pages.get("collectibles")
        if dashboard is not None:
            set_profile = getattr(dashboard, "set_profile", None)
            if callable(set_profile):
                set_profile(profile)
            else:
                refresh = getattr(dashboard, "refresh", None)
                if callable(refresh):
                    refresh()

    def show_page(self, page_name: str):
        if not self._confirm_collectible_navigation(page_name):
            return

        if page_name.startswith("collectibles:"):
            category = page_name.split(":", 1)[1]
            collectibles_page = self.pages["collectibles_browser"]
            self._refresh_collectibles_for_active_profile()
            collectibles_page.set_category(category)
            self.sidebar.set_current(page_name)
            self.stack.setCurrentWidget(self.page_containers["collectibles_browser"])
            return

        if page_name not in self.page_containers:
            print(f"[FoundryDock] Unknown navigation page: {page_name}")
            return

        # Settings -> Data Management can import progress through a separate
        # service instance. Refresh the long-lived pages when they become
        # visible so those external writes appear immediately.
        if page_name == "achievements":
            self.pages["achievements"].refresh()
        elif page_name == "collectibles":
            self._refresh_collectibles_for_active_profile()

        self.sidebar.set_current(page_name)
        self.stack.setCurrentWidget(self.page_containers[page_name])

    def wrap_page(self, page):
        if isinstance(page, FoundryPage):
            page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            return page

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        scroll.setWidget(page)
        return scroll