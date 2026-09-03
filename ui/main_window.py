# ==================================================
# Black Feather Foundry
# main_window.py
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidgetItem,
    QWidget,
)

from engine.config import get_data_dir
from services.eso_achievement_database_service import EsoAchievementDatabaseService
from services.expedition_service import ExpeditionService
from services.optional_modules import broadcast_enabled
from ui.achievements_page import AchievementsPage
from ui.builds_page import BuildsPage
from ui.capabilities_page import CapabilitiesPage
from ui.collectibles_dashboard_page import CollectiblesDashboardPage
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

        # Keep the historical constructor contract intact because the runtime
        # antiquities compatibility layer patches CollectiblesPage.__init__.
        # The dashboard shares the browser's already-created service instead
        # of injecting a new keyword argument into that patched constructor.
        collectible_browser = CollectiblesPage()
        self.collectible_service = collectible_browser.service
        collectible_dashboard = CollectiblesDashboardPage(self.collectible_service)
        collectible_dashboard.categoryRequested.connect(
            lambda category: self.show_page(f"collectibles:{category}")
        )

        roster_page = RosterPage()
        roster_page.header.title.setText("Roster")
        roster_page.header.subtitle.setText("Team members, optimized assignments, responsibilities, and readiness.")
        roster_page.header.department.setText("RAID ENGINE • ROSTER")

        optimization_page = OptimizationPage()
        send_team_button = QPushButton("Send Team to Roster")
        send_team_button.setProperty("primary", True)
        send_team_button.setToolTip(
            "Send the currently selected optimization team into Roster as an assignment plan."
        )
        send_team_button.clicked.connect(self._send_optimized_team_to_roster)
        optimization_page.header.add_context_widget(send_team_button)

        core_pages = {
            "achievements": AchievementsPage(),
            "collectibles": collectible_dashboard,
            "collectibles_browser": collectible_browser,
            "roster_page": roster_page,
            "operations_console": OperationsConsole(expedition=self.expedition_service),
            "console:1": EncountersPage(expedition=self.expedition_service),
            "console:2": BuildsPage(),
            "console:3": CapabilitiesPage(),
            "console:4": MechanicsPage(expedition=self.expedition_service),
            "console:6": optimization_page,
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

    def _refresh_collectibles_for_active_profile(self) -> None:
        """Keep collection browser/dashboard aligned with the achievement profile."""
        achievements_page = self.pages.get("achievements")
        collectibles_page = self.pages.get("collectibles_browser")
        dashboard = self.pages.get("collectibles")
        service = getattr(collectibles_page, "service", None)
        progress = getattr(achievements_page, "achievement_progress_service", None)

        if service is not None and progress is not None and hasattr(service, "set_active_profile"):
            profile = str(progress.active_profile or "").strip()
            if profile:
                service.set_active_profile(profile)
                reload_combo = getattr(collectibles_page, "_reload_profile_combo", None)
                if callable(reload_combo):
                    reload_combo(profile)

        if collectibles_page is not None:
            collectibles_page.refresh()
        if dashboard is not None:
            dashboard.refresh()

    @staticmethod
    def _build_identity(build) -> tuple[str, str, str]:
        player = (
            getattr(build, "Name", "")
            or getattr(build, "Gamertag", "")
            or "Unnamed Player"
        )
        character = getattr(build, "CharacterName", "") or player
        build_name = getattr(build, "BuildName", "") or "Current Build"
        return str(player), str(character), str(build_name)

    def _current_optimized_team_plan(self) -> list[dict[str, str]]:
        page = self.pages.get("console:6")
        if page is None or not hasattr(page, "team_table"):
            return []

        table = page.team_table
        if hasattr(page, "team_tabs") and page.team_tabs.currentIndex() == 1:
            table = page.team_b_table

        rows: list[dict[str, str]] = []
        for row in range(table.rowCount()):
            role_item = table.item(row, 0)
            role = role_item.text() if role_item is not None else f"Slot {row + 1}"
            selector = table.cellWidget(row, 1)
            selection = selector.currentData() if isinstance(selector, QComboBox) else None

            if isinstance(selection, int) and 0 <= selection < len(page.roster.Members):
                build = page.roster.Members[selection]
                player, character, build_name = self._build_identity(build)
                rows.append({
                    "kind": "saved",
                    "slot": role,
                    "player": player,
                    "character": character,
                    "class": str(getattr(build, "EsoClass", "") or "—"),
                    "build": build_name,
                })
            elif isinstance(selection, str) and selection.startswith("recruitment:"):
                rows.append({
                    "kind": "recruitment",
                    "slot": role,
                    "player": "Recruitment Needed",
                    "character": "—",
                    "class": "Flexible",
                    "build": "Open requirement",
                })
        return rows

    @staticmethod
    def _matching_roster_member(roster_page, plan_row: dict[str, str]):
        player = plan_row.get("player", "").strip().lower()
        character = plan_row.get("character", "").strip().lower()
        for member in roster_page.members:
            candidates = {
                str(member.PlayerName or "").strip().lower(),
                str(member.CharacterName or "").strip().lower(),
            }
            if player in candidates or (character and character != "—" and character in candidates):
                return member
        return None

    def _send_optimized_team_to_roster(self) -> None:
        plan = self._current_optimized_team_plan()
        optimization_page = self.pages.get("console:6")
        if not plan:
            if optimization_page is not None:
                optimization_page.status.warning(
                    "No planned team slots are selected. Generate or select a team before sending it to Roster."
                )
            return

        roster_page = self.pages["roster_page"]
        roster_page.optimized_team_plan = tuple(plan)
        roster_page.tabs.setCurrentIndex(0)
        roster_page.assignment_table.setRowCount(0)

        matched = 0
        recruitment = 0
        missing_records = 0
        for plan_row in plan:
            row = roster_page.assignment_table.rowCount()
            roster_page.assignment_table.insertRow(row)
            member = None
            if plan_row["kind"] == "saved":
                member = self._matching_roster_member(roster_page, plan_row)
                matched += int(member is not None)
                missing_records += int(member is None)
            else:
                recruitment += 1

            if plan_row["kind"] == "recruitment":
                notes = "Optimization recruitment requirement; no roster person was fabricated."
                ready = "OPEN"
                secondary = "Recruit / qualify candidate"
            elif member is None:
                notes = "Saved optimized build; matching personnel record not found in Roster."
                ready = "⚠"
                secondary = "Add or match roster record"
            else:
                notes = "Imported from Team Optimization"
                ready = "✓" if member.Status == "Active" else "•"
                secondary = roster_page._secondary_assignment(plan_row["slot"])

            values = [
                plan_row["player"],
                plan_row["slot"],
                plan_row["class"],
                plan_row["build"],
                "Optimized team slot",
                secondary,
                "—",
                notes,
                ready,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col in {0, 1, 2, 3, 8}:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                roster_page.assignment_table.setItem(row, col, item)

        roster_page.status.success(
            f"Optimization plan loaded: {len(plan)} slot(s), {matched} matched roster member(s), "
            f"{recruitment} recruitment requirement(s), {missing_records} unmatched saved build(s). "
            "Personnel records were not overwritten."
        )
        self.show_page("roster_page")

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
        # service instance. Refresh the long-lived pages when they become visible.
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
