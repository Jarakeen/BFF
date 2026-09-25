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

from engine.config import get_data_dir, get_user_database_path
from services.achievement_progress_service import AchievementProgressService
from services.encounter_boss_guide import EncounterBossGuideService
from services.encounter_runtime_guide_projection_service import EncounterRuntimeGuideProjectionService
from services.eso_achievement_database_service import EsoAchievementDatabaseService
from services.expedition_service import ExpeditionService
from services.optional_modules import broadcast_enabled
from services.profiled_collectible_service import ProfiledCollectibleService
from ui.achievements_page import AchievementsPage
from ui.asylum_perfecta_timer_page import AsylumPerfectaTimerPage
from ui.themed_builds_page import BuildsPage
from ui.capabilities_page import CapabilitiesPage
from ui.brittle_uptime_page import BrittleUptimePage
from ui.collectibles_dashboard_page import CollectiblesDashboardPage
from ui.collectibles_page import CollectiblesPage
from ui.comp_builder_page import CompBuilderPage
from ui.community_news_page import CommunityNewsPage
from ui.components.foundry_sidebar import FoundrySidebar
from ui.coverage_page import CoveragePage
from ui.encounters_page import EncountersPage
from ui.foundry_page import FoundryPage
from ui.gear_lookup_page import GearLookupPage
from ui.incident_page import IncidentPage
from ui.mechanics_runtime_page import RuntimeMechanicsPage
from ui.operations_console import OperationsConsole
from ui.optimization_page import OptimizationPage
from ui.reference_data_page import ReferenceDataPage
from ui.raid_review_page import RaidReviewPage
from ui.phase14_rotation_page import RotationBuilderPage
from ui.themed_roster_page import RosterPage
from ui.settings_page import SettingsPage
from ui.stickerbook_page import StickerbookPage
from ui.ui_safety import attach_save_state_badge, confirm_unsaved_changes


def _tab_index_by_text(tabs, title: str) -> int:
    wanted = str(title or "").strip().casefold()
    for index in range(tabs.count()):
        if str(tabs.tabText(index) or "").strip().casefold() == wanted:
            return index
    return -1


class MainWindow(QMainWindow):
    """Black Feather Foundry main window."""

    def __init__(self, expedition=None):
        super().__init__()
        data_dir = get_data_dir()
        self.eso_data_service = EsoAchievementDatabaseService(data_dir / "eso.db")
        self.achievement_progress_service = AchievementProgressService(get_user_database_path())
        self.encounter_boss_guide_service = EncounterBossGuideService(data_dir / "eso.db")
        self.encounter_runtime_guide_service = EncounterRuntimeGuideProjectionService(data_dir)
        self.expedition_service = expedition if expedition is not None else ExpeditionService()
        self.broadcast_enabled = broadcast_enabled()
        self.setWindowTitle("Black Feather Foundry Field Office")
        self.resize(1400, 900)
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

        # The dashboard is intentionally eager because it is the lightweight,
        # visual Collections landing page. The heavier category browser may be
        # lazy-loaded, so MainWindow owns the one shared profile-aware service.
        self.collectible_service = ProfiledCollectibleService(
            get_data_dir() / "eso.db"
        )
        self.collectible_service.set_active_profile(
            self.achievement_progress_service.active_profile
        )
        collectible_browser = CollectiblesPage(service=self.collectible_service)
        collectible_dashboard = CollectiblesDashboardPage(self.collectible_service)
        collectible_dashboard.categoryRequested.connect(
            lambda category: self.show_page(f"collectibles:{category}")
        )
        stickerbook_page = StickerbookPage()

        roster_page = RosterPage()
        roster_page.header.title.setText("Roster")
        roster_page.header.subtitle.setText("Team members, optimized assignments, responsibilities, and readiness.")
        roster_page.header.department.setText("RAID ENGINE • ROSTER")

        comp_builder_page = CompBuilderPage()

        optimization_page = OptimizationPage()

        core_pages = {
            "achievements": AchievementsPage(),
            "collectibles": collectible_dashboard,
            "collectibles_browser": collectible_browser,
            "stickerbook": stickerbook_page,
            "roster_page": roster_page,
            "comp_builder": comp_builder_page,
            "operations_console": OperationsConsole(expedition=self.expedition_service),
            "console:1": EncountersPage(expedition=self.expedition_service),
            "console:2": BuildsPage(),
            "console:3": CapabilitiesPage(),
            "console:4": RuntimeMechanicsPage(
                expedition=self.expedition_service,
                guide_service=self.encounter_boss_guide_service,
                runtime_guide_service=self.encounter_runtime_guide_service,
            ),
            "console:6": optimization_page,
            "console:7": CoveragePage(),
            "console:8": ReferenceDataPage(),
            "raid_review": RaidReviewPage(),
            "brittle_uptime": BrittleUptimePage(),
            "rotations": RotationBuilderPage(),
            "gear_lookup": GearLookupPage(),
            "timers": AsylumPerfectaTimerPage(),
            "community_news": CommunityNewsPage(),
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

        # Help joins Settings after all canonical pages exist, so its contextual
        # buttons can bind directly without replacing MainWindow.build_ui.
        from ui.help_support import install_help_surfaces

        install_help_surfaces(self)

        # Raid Engine pages join the canonical page registry directly. Their
        # preconstruction extensions are composed by the application bootstrap.
        from ui.raid_engine_dashboard_support import register_raid_engine_pages

        register_raid_engine_pages(self)

        self._install_page_safety_badges()

    def _install_page_safety_badges(self) -> None:
        """Give every page participating in the unsaved contract one status badge."""
        for page in self.pages.values():
            if callable(getattr(page, "has_pending_changes", None)):
                attach_save_state_badge(page)

    def _dirty_pages(self) -> list:
        dirty = []
        for page in self.pages.values():
            has_pending = getattr(page, "has_pending_changes", None)
            if not callable(has_pending):
                continue
            try:
                if has_pending():
                    dirty.append(page)
            except Exception:
                dirty.append(page)
        return dirty

    def closeEvent(self, event) -> None:
        """Do not let application close silently discard edits on any page."""
        for page in self._dirty_pages():
            if not confirm_unsaved_changes(
                self,
                page,
                action_text="close FoundryDock",
            ):
                event.ignore()
                return
        event.accept()

    def connect_signals(self):
        self.sidebar.pageRequested.connect(self.show_page)

    def _persist_comp_plan_state_to_raid_plan(
        self,
        *,
        navigate: bool,
    ):
        """Persist canonical Comp state, finalizing a new Raid Plan when unbound."""
        from services.comp_plan_state_service import CompPlanStateService

        raid_plans = self.pages.get("raid_plans")
        comp = self.pages.get("comp_builder")
        if raid_plans is None or comp is None:
            return None

        state = getattr(comp, "_comp_plan_state", None)
        if state is None:
            raid_plans.status.warning(
                "Comp Maker is not bound to a Raid Plan; direct Raid Plan save is unavailable."
            )
            return None

        if state.is_raid_plan_bound:
            base_plan = raid_plans.plan_repository.get(str(state.raid_plan_id))
            if base_plan is None:
                raid_plans.status.error(
                    f'Could not reload originating Raid Plan "{state.raid_plan_name}".'
                )
                return None
            expected = getattr(comp, "_raid_plan_origin_snapshot", None)
            if expected is None or expected.plan_id != base_plan.plan_id:
                raise RuntimeError("Comp Maker lost its saved Raid Plan baseline. Reload the plan before saving.")
            plan = CompPlanStateService.to_raid_plan(state, base_plan=base_plan)
        else:
            existing_ids = tuple(
                plan.plan_id
                for plan in raid_plans.plan_repository.list_plans()
            )
            plan_id = CompPlanStateService.unique_raid_plan_id(
                state,
                existing_ids=existing_ids,
            )
            plan = CompPlanStateService.to_new_raid_plan(
                state,
                plan_id=plan_id,
            )
            expected = None
        from services.raid_plan_repository import duplicate_occupied_player_seats
        duplicates = duplicate_occupied_player_seats(plan)
        if duplicates:
            raise RuntimeError(
                "One player appears in multiple Comp seats: " + "; ".join(duplicates)
            )
        raid_plans.plan_repository.save(
            plan, expected=expected, must_be_new=expected is None,
        )
        persisted = raid_plans.plan_repository.get(plan.plan_id)
        if persisted is None or persisted != plan:
            raid_plans.status.error(
                "Comp Maker state did not round-trip through Raid Plan storage exactly; "
                "the app is refusing to report success."
            )
            return None

        comp._comp_plan_state = CompPlanStateService.from_raid_plan(
            persisted,
            achievement_goal=state.achievement_goal,
        )
        comp._raid_plan_origin_id = persisted.plan_id
        comp._raid_plan_origin_snapshot = persisted
        raid_plans.apply_plan(persisted)
        raid_plans._refresh_overview()
        raid_plans.status.success(
            f"Comp Maker changes saved directly to Raid Plan: {persisted.name}."
        )
        if navigate:
            raid_plans._show_local_view(0)
            self.show_page("raid_plans")
        return persisted

    def _current_page_for_navigation(self):
        current = self.stack.currentWidget()
        for route, container in self.page_containers.items():
            if container is current:
                return self.pages.get(route), container
        return None, current

    def _confirm_unsaved_navigation(self, target_page: str) -> bool:
        target_container = self.page_containers.get(target_page)
        page, current_container = self._current_page_for_navigation()
        if page is None or target_container is current_container:
            return True
        return confirm_unsaved_changes(
            self,
            page,
            action_text="leave this page",
        )

    def _confirm_collectible_navigation(self, target_page: str) -> bool:
        collectibles_page = self.pages.get("collectibles_browser")
        has_pending = getattr(collectibles_page, "has_pending_changes", None)
        if not callable(has_pending) or not has_pending():
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

    def _refresh_collectibles_for_active_profile(self, *, refresh_browser: bool = True) -> None:
        """Keep collection browser/dashboard/stickerbook aligned with the achievement profile."""
        collectibles_page = self.pages.get("collectibles_browser")
        dashboard = self.pages.get("collectibles")
        stickerbook = self.pages.get("stickerbook")
        service = self.collectible_service

        # Active-profile state is lightweight persisted application state. Do not
        # force the full Achievements page to exist just so Collectibles can learn
        # which profile is active.
        self.achievement_progress_service.reload(preserve_active_profile=False)
        active_profile = str(
            self.achievement_progress_service.active_profile or ""
        ).strip()

        if service is not None and active_profile and hasattr(service, "set_active_profile"):
            service.set_active_profile(active_profile)
            reload_combo = getattr(collectibles_page, "_reload_profile_combo", None)
            if callable(reload_combo):
                reload_combo(active_profile)

        if stickerbook is not None and active_profile and hasattr(stickerbook, "set_profile"):
            stickerbook.set_profile(active_profile)

        browser_refresh = getattr(collectibles_page, "refresh", None)
        if refresh_browser and callable(browser_refresh):
            browser_refresh()
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
                    "No planned team slots are selected. Generate or select a team before sending it to Raid Plan."
                )
            return

        roster_workspace = self.pages.get("roster_workspace")
        if roster_workspace is None:
            if optimization_page is not None:
                optimization_page.status.warning(
                    "The current Roster workspace is unavailable."
                )
            return

        load_plan = getattr(roster_workspace, "load_optimizer_plan", None)
        if not callable(load_plan):
            if optimization_page is not None:
                optimization_page.status.warning(
                    "The current Roster workspace cannot accept an Optimizer plan."
                )
            return

        load_plan(tuple(plan))
        self.show_page("roster_workspace")

    def _open_player_builds(self, gamertag: str) -> None:
        self.show_page("console:2")
        builds_page = self.pages.get("console:2")
        if builds_page is None:
            return
        show_player = getattr(builds_page, "show_player_builds", None)
        if callable(show_player):
            show_player(gamertag)

    def show_page(self, page_name: str):
        if not self._confirm_unsaved_navigation(page_name):
            return

        if page_name == "assignments":
            assignments = self.pages.get("assignments")
            roles = self.pages.get("raid_plans")
            if assignments is not None and getattr(assignments, "_loaded_plan_snapshot", None) is None:
                plan = getattr(roles, "_loaded_plan_snapshot", None)
                if plan is not None and not assignments.load_plan_by_id(plan.plan_id):
                    return

        if page_name == "comp_builder":
            comp = self.pages.get("comp_builder")
            if comp is not None:
                refresh_names = getattr(comp, "_refresh_raid_plan_name_choices", None)
                if callable(refresh_names):
                    refresh_names()
                from ui.comp_builder_phase14_shell_support import (
                    refresh_phase14_presentation,
                )
                refresh_phase14_presentation(comp)

        if page_name == "console:6":
            optimizer = self.pages.get("console:6")
            raid_plan_container = self.page_containers.get("raid_plans")
            if (
                optimizer is not None
                and raid_plan_container is not None
                and self.stack.currentWidget() is raid_plan_container
            ):
                raid_plans = self.pages.get("raid_plans")
                origin = getattr(raid_plans, "_loaded_plan_snapshot", None)
                if origin is not None:
                    optimizer._raid_plan_origin_id = origin.plan_id
                    optimizer._raid_plan_origin_trial_id = origin.trial_id
                    optimizer._raid_plan_origin_name = origin.name
                    optimizer._raid_plan_origin_team_name = origin.team_name or ""

        if page_name == "console:2":
            builds_page = self.pages.get("console:2")
            reload_builds = getattr(builds_page, "_load", None)
            if callable(reload_builds):
                reload_builds()
            clear_filter = getattr(builds_page, "clear_player_build_filter", None)
            if callable(clear_filter):
                clear_filter()

        if page_name.startswith("collectibles:"):
            category = page_name.split(":", 1)[1]
            collectibles_page = self.pages["collectibles_browser"]
            self._refresh_collectibles_for_active_profile(refresh_browser=False)
            collectibles_page.set_category(category)
            self.sidebar.set_current(page_name)
            self.stack.setCurrentWidget(self.page_containers["collectibles_browser"])
            return

        # Some sidebar entries intentionally expose focused views of existing
        # stateful pages instead of creating duplicate editors and services.
        if page_name == "characters":
            roster_page = self.pages.get("roster_page")
            if roster_page is not None:
                refresh = getattr(roster_page, "refresh", None)
                if callable(refresh):
                    refresh()
                if hasattr(roster_page, "tabs"):
                    personnel_index = _tab_index_by_text(roster_page.tabs, "PERSONNEL")
                    if personnel_index >= 0:
                        roster_page.tabs.setCurrentIndex(personnel_index)
                roster_page.header.title.setText("Characters")
                roster_page.header.subtitle.setText("People and characters available to your raid roster.")
                roster_page.header.department.setText("ROSTER • CHARACTERS")
            self.sidebar.set_current(page_name)
            self.stack.setCurrentWidget(self.page_containers["roster_page"])
            return

        if page_name == "scribed_skills":
            builds_page = self.pages.get("console:2")
            if builds_page is not None and hasattr(builds_page, "build_tabs"):
                builds_page.build_tabs.setCurrentIndex(3)
            self.sidebar.set_current(page_name)
            self.stack.setCurrentWidget(self.page_containers["console:2"])
            return

        if page_name == "tools:reference_data":
            self.sidebar.set_current(page_name)
            self.stack.setCurrentWidget(self.page_containers["console:8"])
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
        elif page_name == "stickerbook":
            self._refresh_collectibles_for_active_profile()
            self.pages["stickerbook"].refresh()
        elif page_name == "operations_console":
            # The overview is a long-lived page. Performance Focus goals are
            # persisted while the user is on Capabilities, so rebuild the
            # overview whenever it becomes visible instead of showing the card
            # state captured when the application first launched.
            self.pages["operations_console"].refresh()
        elif page_name == "console:7":
            self.pages["console:7"].refresh()
        elif page_name == "rotations":
            from ui.rotation_tank_provider_scope_transfer_support import (
                prepare_rotation_tank_provider_scope,
            )

            prepare_rotation_tank_provider_scope(self)
        elif page_name == "console:4":
            self.pages["console:4"].refresh_context()
        elif page_name == "gear_lookup":
            self.pages["gear_lookup"].refresh()
        elif page_name == "timers":
            self.pages["timers"].refresh_context()
        elif page_name == "roster_page":
            roster_page = self.pages["roster_page"]
            roster_page.header.title.setText("Roster")
            roster_page.header.subtitle.setText("Team members, optimized assignments, responsibilities, and readiness.")
            roster_page.header.department.setText("RAID ENGINE • ROSTER")

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
