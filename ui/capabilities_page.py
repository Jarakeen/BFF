# ==================================================
# Black Feather Foundry
#
# File:
# ui/capabilities_page.py
#
# Purpose:
# Capabilities Desk.
#
# Two desk-level tabs:
#   "Ranked Team Builds" -- ESO Logs top-ranked-team gear/skill
#     evidence for a chosen trial (TopTeamCard, untouched here).
#   "Performance Dashboard" -- up to 12 raid team member tabs,
#     each pulling a report/fight from ESO Logs, letting you pick
#     which player in that fight is you (by name, or by an
#     anonymized label like "Anonymous 7" when the report owner
#     hid names), and charting that player's buff/debuff uptime
#     plus their healing or damage output.
#
# Wired to the sidebar's existing "Capabilities" nav entry
# (Raid Operations > Capabilities, page key "console:3").
#
# ==================================================

from __future__ import annotations

import csv
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QMessageBox,
    QWidget,
    QFileDialog,
)

from engine.config import get_data_dir
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.foundry_page import FoundryPage

from widgets.capability_editor import CapabilityEditor
from widgets.performance_dashboard import PerformanceDashboard
from widgets.top_team_card import TopTeamCard
from widgets.build_dashboard import BuildDashboard

from models.capability_model import CapabilityRoster, CapabilityProfile
from models.performance_model import PerformanceRoster, PerformanceProfile
from services.capability_service import CapabilityService
from services.performance_dashboard_service import PerformanceDashboardService
from services.top_team_service import TopTeamService
from services.top_team_template_intake import TopTeamTemplateIntake
from services.team_prescription_template_catalog import (
    TeamPrescriptionTemplateCatalog,
)
from services.esologs_client import EsoLogsClient, EsoLogsApiError
from services.eso_database import EsoDatabase
from services.reference_data_service import ReferenceDataService
from services.settings_service import SettingsService

# Legacy path -- still read/written by the untouched
# _load_roster_from_disk / save_capabilities / export_csv methods
# below. Left as-is; the new Performance Dashboard tab reads and
# writes its own file instead (see performance_path).
CAPABILITIES_PATH = "data/capabilities.json"


class CapabilitiesPage(FoundryPage):
    """
    Capabilities Desk -- ranked-team build evidence, plus one tab
    per raid team member's ESO Logs-driven performance dashboard.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_services()

        self.build_ui()
        self.connect_signals()

        self.refresh()

    # --------------------------------------------------
    # Services
    # --------------------------------------------------

    def build_services(self):

        data_dir = get_data_dir()

        # Legacy -- kept only because _apply_roster / add_member /
        # remove_current_member / suggest_watches / fetch (all
        # untouched) still depend on them. Not used by the new
        # Performance Dashboard tab.
        self.database = EsoDatabase(data_dir / "eso.db")
        self.reference = ReferenceDataService(self.database)
        self.capabilities_path = data_dir / "capabilities.json"

        self.settings_service = SettingsService(Path("settings.json"))

        self.performance_path = data_dir / "performance_dashboard.json"

        self.top_team_template_intake = TopTeamTemplateIntake.for_data_dir(
            data_dir
        )
        self.template_catalog_snapshot = TeamPrescriptionTemplateCatalog(
            data_dir / "team_prescription_templates.json"
        ).load()

    def _build_esologs_client(self) -> EsoLogsClient:
        settings = self.settings_service.load()

        return EsoLogsClient(
            client_id=settings.get("EsoLogsClientId", ""),
            client_secret=settings.get("EsoLogsClientSecret", ""),
        )

    def _build_capability_service(self) -> CapabilityService:
        """
        Legacy -- kept only for the untouched fetch()/
        suggest_watches() methods below. Not used by the new
        Performance Dashboard tab; see _build_performance_service.
        """

        return CapabilityService(self._build_esologs_client(), self.reference)

    def _build_performance_service(self) -> PerformanceDashboardService:
        """
        Rebuilt on demand (not cached) so a Client ID/Secret
        change on the Settings page takes effect on the next
        Load Fight without restarting the Foundry.
        """

        return PerformanceDashboardService(self._build_esologs_client())

    def _build_top_team_service(self) -> TopTeamService:
        """Rebuild on demand so credential changes apply without restart."""
        return TopTeamService(self._build_esologs_client())

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        self.header = FoundryHeader(
            title="Capabilities",
            subtitle=(
                "Buff/debuff uptime and ranked-team build evidence from ESO Logs."
            ),
            department="Planning",
        )

        self.set_header(self.header)

        #
        # Top-team gear card (left column) beside the tab strip +
        # per-member editor stack (right column) -- a horizontal
        # split rather than stacking the gear card above everything,
        # so it grows tall enough to match the editor stack next to
        # it instead of leaving dead space below a short card.
        #

        self.top_team_card = TopTeamCard(
            service_factory=self._build_top_team_service,
            template_intake=self.top_team_template_intake,
            default_game_update=self.template_catalog_snapshot.game_update,
        )
        self.top_team_card.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )

        #
        # Tab strip
        #

        self.tab_row = QHBoxLayout()

        self.tab_row.setSpacing(8)

        self.tabs_container = QHBoxLayout()

        self.tabs_widget = None

        self.add_member_button = FoundryButton(
            "+ Add Member",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        self.remove_member_button = FoundryButton(
            "Remove Member",
            role=ButtonRole.DANGER,
            compact=True,
        )

        self.tab_row.addLayout(self.tabs_container, 1)
        self.tab_row.addWidget(self.add_member_button)
        self.tab_row.addWidget(self.remove_member_button)

        #
        # Per-member editors (legacy watch-list feature) -- built,
        # but not added to any visible layout; kept only so
        # _apply_roster / add_member / remove_current_member /
        # save_capabilities / export_csv still have everything they
        # reference and keep working untouched if called.
        #

        self.stack = QStackedWidget()

        self.editors: list[CapabilityEditor] = []

        self.member_column = QWidget()

        member_column_layout = QVBoxLayout(self.member_column)

        member_column_layout.setContentsMargins(0, 0, 0, 0)

        member_column_layout.setSpacing(8)

        member_column_layout.addLayout(self.tab_row)

        member_column_layout.addWidget(self.stack, 1)

        #
        # Performance Dashboard -- the tab strip + stack that
        # actually shows in the desk tab below, replacing the
        # legacy watch-list editors above.
        #

        self.performance_tab_row = QHBoxLayout()
        self.performance_tab_row.setSpacing(8)

        self.performance_tabs_container = QHBoxLayout()
        self.performance_tabs_widget = None

        self.add_performance_member_button = FoundryButton(
            "+ Add Member",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        self.remove_performance_member_button = FoundryButton(
            "Remove Member",
            role=ButtonRole.DANGER,
            compact=True,
        )

        self.performance_tab_row.addLayout(self.performance_tabs_container, 1)
        self.performance_tab_row.addWidget(self.add_performance_member_button)
        self.performance_tab_row.addWidget(self.remove_performance_member_button)

        self.performance_stack = QStackedWidget()

        self.performance_dashboards: list[PerformanceDashboard] = []

        self.performance_member_column = QWidget()

        performance_column_layout = QVBoxLayout(self.performance_member_column)

        performance_column_layout.setContentsMargins(0, 0, 0, 0)

        performance_column_layout.setSpacing(8)

        performance_column_layout.addLayout(self.performance_tab_row)

        performance_column_layout.addWidget(self.performance_stack, 1)

        #
        # Desk-level tabs: ranked-team build evidence and per-member
        # performance dashboards. Use a real QTabBar here (and
        # for the member roster below) so tabs read as tabs instead
        # of rounded action pills.
        #

        self.desk_tabs = QTabBar()
        self.desk_tabs.setExpanding(False)
        self.desk_tabs.setDrawBase(True)
        self.desk_tabs.addTab("Ranked Team Builds")
        self.desk_tabs.addTab("Performance Dashboard")
        self.desk_tabs.currentChanged.connect(self._select_desk_tab)

        self.desk_stack = QStackedWidget()

        self.desk_stack.addWidget(self.top_team_card)  # index 0: Ranked Team Builds

        self.desk_stack.addWidget(self.performance_member_column)  # index 1: Performance Dashboard

        desk_container = QWidget()

        desk_container_layout = QVBoxLayout(desk_container)

        desk_container_layout.setContentsMargins(0, 0, 0, 0)

        desk_container_layout.setSpacing(8)

        desk_container_layout.addWidget(self.desk_tabs)

        desk_container_layout.addWidget(self.desk_stack, 1)

        self.add_workspace(desk_container)

        #
        # Actions
        #

        self.actions = QWidget()

        actions_layout = QHBoxLayout(self.actions)

        actions_layout.setContentsMargins(0, 0, 0, 0)

        # Legacy buttons -- built and wired exactly as before (see
        # connect_signals) so save_capabilities/export_csv stay
        # reachable and unchanged, but not shown; the visible
        # actions bar below is for the new Performance Dashboard.
        self.save_button = FoundryButton(
            "Save Watch Lists",
            role=ButtonRole.SUCCESS,
        )

        self.export_csv_button = FoundryButton(
            "Export CSV...",
            role=ButtonRole.SECONDARY,
        )

        self.save_performance_button = FoundryButton(
            "Save Dashboard Picks",
            role=ButtonRole.SUCCESS,
        )

        self.export_performance_csv_button = FoundryButton(
            "Export CSV...",
            role=ButtonRole.SECONDARY,
        )

        actions_layout.addWidget(self.save_performance_button)
        actions_layout.addWidget(self.export_performance_csv_button)
        actions_layout.addStretch()

        self.set_actions(self.actions)

        #
        # Status
        #

        self.status = FoundryStatusBar()

        self.set_status(self.status)

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        # Legacy -- unchanged, kept only so add_member/
        # remove_current_member/save_capabilities/export_csv stay
        # reachable exactly as before.
        self.add_member_button.clicked.connect(self.add_member)

        self.remove_member_button.clicked.connect(self.remove_current_member)

        self.save_button.clicked.connect(self.save_capabilities)

        self.export_csv_button.clicked.connect(self.export_csv)

        # New Performance Dashboard wiring.
        self.add_performance_member_button.clicked.connect(self.add_performance_member)

        self.remove_performance_member_button.clicked.connect(
            self.remove_current_performance_member
        )

        self.save_performance_button.clicked.connect(self.save_performance_dashboard)

        self.export_performance_csv_button.clicked.connect(self.export_performance_csv)

    # --------------------------------------------------
    # Loading
    # --------------------------------------------------

    def refresh(self):

        try:

            roster = self._load_roster_from_disk()

        except Exception as exc:

            self.status.error(f"Failed to load capabilities: {exc}")

            roster = CapabilityRoster()

        self._apply_roster(roster)

        try:

            performance_roster = self._load_performance_roster_from_disk()

        except Exception as exc:

            self.status.error(f"Failed to load performance dashboard: {exc}")

            performance_roster = PerformanceRoster()

        self._apply_performance_roster(performance_roster)

        self.status.info(
            f"{len(performance_roster.Members)} member tab(s) loaded."
        )

    def _load_roster_from_disk(self) -> CapabilityRoster:

        if not self.capabilities_path.exists():
            return CapabilityRoster()

        data = json.loads(self.capabilities_path.read_text(encoding="utf-8"))

        return CapabilityRoster.from_dict(data)

    def _apply_roster(self, roster: CapabilityRoster):

        while self.stack.count():

            widget = self.stack.widget(0)

            self.stack.removeWidget(widget)

            widget.deleteLater()

        self.editors = []

        skill_choices = self.reference.list_skill_names()

        for member in roster.Members:

            editor = self._new_editor(skill_choices)

            editor.load(member)

            self.editors.append(editor)

            dashboard = BuildDashboard(editor)
            self.stack.addWidget(dashboard)

        self._rebuild_tabs()

    def _new_editor(self, skill_choices: list[str]) -> CapabilityEditor:

        editor = CapabilityEditor()

        editor.set_watch_name_choices(skill_choices)

        editor.nameChanged.connect(self._rebuild_tabs)

        editor.fetchRequested.connect(lambda e=editor: self.fetch(e))

        editor.suggestRequested.connect(lambda e=editor: self.suggest_watches(e))

        return editor

    # --------------------------------------------------
    # Tabs
    # --------------------------------------------------

    def _rebuild_tabs(self, *_args):

        current = self.stack.currentIndex()

        if current < 0:
            current = 0

        while self.tabs_container.count():

            item = self.tabs_container.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        labels = [
            editor.model.display_label(f"Member {i + 1}")
            for i, editor in enumerate(self.editors)
        ]

        if not labels:
            return

        self.tabs_widget = QTabBar()
        self.tabs_widget.setExpanding(False)
        self.tabs_widget.setDrawBase(True)
        self.tabs_widget.setUsesScrollButtons(True)
        for label in labels:
            self.tabs_widget.addTab(label)
        self.tabs_widget.setCurrentIndex(min(current, len(labels) - 1))
        self.tabs_widget.currentChanged.connect(self._select_tab_by_index)

        self.tabs_container.addWidget(self.tabs_widget)

        self.remove_member_button.setEnabled(len(self.editors) > 1)

        self.add_member_button.setEnabled(
            len(self.editors) < CapabilityRoster.MAX_MEMBERS
        )

    def _select_tab_by_index(self, index: int):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    def _select_desk_tab(self, index: int):
        if 0 <= index < self.desk_stack.count():
            self.desk_stack.setCurrentIndex(index)

    # --------------------------------------------------
    # Member management
    # --------------------------------------------------

    def add_member(self):

        if len(self.editors) >= CapabilityRoster.MAX_MEMBERS:

            self.status.warning(
                f"Capabilities is limited to {CapabilityRoster.MAX_MEMBERS} members."
            )

            return

        editor = self._new_editor(self.reference.list_skill_names())

        self.editors.append(editor)

        dashboard = BuildDashboard(editor)
        self.stack.addWidget(dashboard)

        self.stack.setCurrentWidget(dashboard)

        self._rebuild_tabs()

        self.status.info("New member tab added.")

    def remove_current_member(self):

        if len(self.editors) <= 1:

            self.status.warning("At least one member is required.")

            return

        index = self.stack.currentIndex()

        if index < 0:
            return

        editor = self.editors[index]

        label = editor.model.display_label(f"Member {index + 1}")

        confirm = QMessageBox.question(
            self,
            "Remove Member",
            f"Remove the Capabilities tab for {label}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.editors.pop(index)

        widget = self.stack.widget(index)
        self.stack.removeWidget(widget)
        widget.deleteLater()

        self._rebuild_tabs()

        self.status.success(f"Removed {label}.")

    # --------------------------------------------------
    # Suggestions
    # --------------------------------------------------

    def suggest_watches(self, editor: CapabilityEditor):

        set_names = [
            s.strip()
            for s in editor.equipped_sets.text().split(",")
            if s.strip()
        ]

        if not set_names:

            self.status.warning(
                "Enter equipped sets (comma-separated) before suggesting watches."
            )

            return

        service = self._build_capability_service()

        suggestions = service.suggest_watches(set_names)

        if not suggestions:

            self.status.info("No buffs/debuffs found in those sets' bonus text.")

            return

        for watch in suggestions:
            editor.add_watch(watch)

        self.status.success(f"Added {len(suggestions)} suggested watch(es).")

    # --------------------------------------------------
    # Fetch
    # --------------------------------------------------

    def fetch(self, editor: CapabilityEditor):

        report_code = editor.report_code.text().strip()

        fight_text = editor.fight_id.text().strip()

        if not report_code or not fight_text:

            self.status.warning("Enter a report code and fight number first.")

            return

        try:
            fight_id = int(fight_text)
        except ValueError:

            self.status.error("Fight number must be an integer.")

            return

        watches = editor.active_watches

        if not watches:

            self.status.warning("Check at least one watch before fetching.")

            return

        service = self._build_capability_service()

        self.status.info(f"Fetching {report_code} #{fight_text} from ESO Logs...")

        immunity_name = editor.immunity_buff_name.text().strip()

        boss_active_seconds: float | None = None

        if immunity_name:

            # Immunity buff given -- always recompute and overwrite
            # Boss Active Time from it, rather than trusting whatever
            # was typed there before (this box is now driven by the
            # immunity buff, not manually maintained).
            try:

                boss_active_seconds = service.compute_boss_active_seconds(
                    report_code,
                    fight_id,
                    immunity_name,
                    editor.immunity_buff_kind.currentText(),
                )

            except EsoLogsApiError as exc:

                self.status.error(str(exc))

                return

            except Exception as exc:

                self.status.error(f"Failed to compute boss active time: {exc}")

                return

            editor.boss_active_seconds.setText(f"{boss_active_seconds:.1f}")

        else:

            # No immunity buff configured -- fall back to whatever
            # the user manually typed in Boss Active Time, exactly
            # as before this feature existed.
            active_text = editor.boss_active_seconds.text().strip()

            if active_text:

                try:
                    boss_active_seconds = float(active_text)
                except ValueError:

                    self.status.error("Boss active time must be a number of seconds.")

                    return

        try:

            summary, results = service.fetch_uptime(
                report_code,
                fight_id,
                watches,
                boss_active_seconds=boss_active_seconds,
            )

        except EsoLogsApiError as exc:

            self.status.error(str(exc))

            return

        except Exception as exc:

            self.status.error(f"Fetch failed: {exc}")

            return

        editor.record_results(summary, results)

        self.status.success(
            f"Fetched {len(results)} watched effect(s) for {summary.get('name', 'the fight')}."
        )

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    def _current_roster(self) -> CapabilityRoster:

        return CapabilityRoster(
            Members=[editor.model for editor in self.editors]
        )

    def save_capabilities(self):

        try:

            self.capabilities_path.parent.mkdir(parents=True, exist_ok=True)

            self.capabilities_path.write_text(
                json.dumps(self._current_roster().to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            self.status.success("Capabilities saved.")

        except Exception as exc:

            self.status.error(f"Save failed: {exc}")

    # --------------------------------------------------
    # Export
    # --------------------------------------------------

    def export_csv(self):

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Capabilities as CSV",
            "raid_capabilities.csv",
            "CSV Files (*.csv)",
        )

        if not filename:
            return

        try:

            with open(filename, "w", newline="", encoding="utf-8") as handle:

                writer = csv.writer(handle)

                writer.writerow(
                    [
                        "Member",
                        "Report",
                        "Fight",
                        "Fight Name",
                        "Watching",
                        "Type",
                        "Uptime % (Full Fight)",
                        "Uptime % (Boss Active)",
                    ]
                )

                for editor in self.editors:

                    model = editor.model

                    if not model.LastResults:
                        continue

                    for result in model.LastResults:

                        writer.writerow(
                            [
                                model.Name,
                                model.ReportCode,
                                model.FightId,
                                model.LastFightName,
                                result.Name,
                                result.Kind,
                                f"{result.UptimePercentFull:.1f}",
                                f"{result.UptimePercentActive:.1f}",
                            ]
                        )

            self.status.success(f"Exported CSV to {filename}")

        except Exception as exc:

            self.status.error(f"CSV export failed: {exc}")

    # ==================================================
    # Performance Dashboard (new -- parallels the legacy
    # roster/editor/save/export methods above without touching them)
    # ==================================================

    # --------------------------------------------------
    # Loading / persistence
    # --------------------------------------------------

    def _load_performance_roster_from_disk(self) -> PerformanceRoster:

        if not self.performance_path.exists():
            return PerformanceRoster()

        data = json.loads(self.performance_path.read_text(encoding="utf-8"))

        return PerformanceRoster.from_dict(data)

    def _apply_performance_roster(self, roster: PerformanceRoster):

        while self.performance_stack.count():

            widget = self.performance_stack.widget(0)

            self.performance_stack.removeWidget(widget)

            widget.deleteLater()

        self.performance_dashboards = []

        for profile in roster.Members:

            dashboard = self._new_performance_dashboard()

            dashboard.load(profile)

            self.performance_dashboards.append(dashboard)

            self.performance_stack.addWidget(dashboard)

        self._rebuild_performance_tabs()

    def _new_performance_dashboard(self) -> PerformanceDashboard:

        dashboard = PerformanceDashboard()

        dashboard.nameChanged.connect(self._rebuild_performance_tabs)

        dashboard.loadFightRequested.connect(
            lambda d=dashboard: self.load_fight_for_dashboard(d)
        )

        dashboard.showPerformanceRequested.connect(
            lambda d=dashboard: self.show_performance_for_dashboard(d)
        )

        return dashboard

    # --------------------------------------------------
    # Tabs
    # --------------------------------------------------

    def _rebuild_performance_tabs(self, *_args):

        current = self.performance_stack.currentIndex()

        if current < 0:
            current = 0

        while self.performance_tabs_container.count():

            item = self.performance_tabs_container.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        labels = [
            dashboard.model.display_label(f"Member {i + 1}")
            for i, dashboard in enumerate(self.performance_dashboards)
        ]

        if not labels:
            return

        self.performance_tabs_widget = QTabBar()
        self.performance_tabs_widget.setExpanding(False)
        self.performance_tabs_widget.setDrawBase(True)
        self.performance_tabs_widget.setUsesScrollButtons(True)

        for label in labels:
            self.performance_tabs_widget.addTab(label)

        self.performance_tabs_widget.setCurrentIndex(min(current, len(labels) - 1))
        self.performance_tabs_widget.currentChanged.connect(
            self._select_performance_tab_by_index
        )

        self.performance_tabs_container.addWidget(self.performance_tabs_widget)

        self.remove_performance_member_button.setEnabled(
            len(self.performance_dashboards) > 1
        )

        self.add_performance_member_button.setEnabled(
            len(self.performance_dashboards) < PerformanceRoster.MAX_MEMBERS
        )

    def _select_performance_tab_by_index(self, index: int):
        if 0 <= index < self.performance_stack.count():
            self.performance_stack.setCurrentIndex(index)

    # --------------------------------------------------
    # Member management
    # --------------------------------------------------

    def add_performance_member(self):

        if len(self.performance_dashboards) >= PerformanceRoster.MAX_MEMBERS:

            self.status.warning(
                f"Performance Dashboard is limited to "
                f"{PerformanceRoster.MAX_MEMBERS} members."
            )

            return

        dashboard = self._new_performance_dashboard()

        self.performance_dashboards.append(dashboard)

        self.performance_stack.addWidget(dashboard)

        self.performance_stack.setCurrentWidget(dashboard)

        self._rebuild_performance_tabs()

        self.status.info("New member tab added.")

    def remove_current_performance_member(self):

        if len(self.performance_dashboards) <= 1:

            self.status.warning("At least one member is required.")

            return

        index = self.performance_stack.currentIndex()

        if index < 0:
            return

        dashboard = self.performance_dashboards[index]

        label = dashboard.model.display_label(f"Member {index + 1}")

        confirm = QMessageBox.question(
            self,
            "Remove Member",
            f"Remove the Performance Dashboard tab for {label}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.performance_dashboards.pop(index)

        widget = self.performance_stack.widget(index)
        self.performance_stack.removeWidget(widget)
        widget.deleteLater()

        self._rebuild_performance_tabs()

        self.status.success(f"Removed {label}.")

    # --------------------------------------------------
    # Load Fight / Show My Performance
    # --------------------------------------------------

    def load_fight_for_dashboard(self, dashboard: PerformanceDashboard):

        report_code = dashboard.report_code_value

        fight_text = dashboard.fight_id_value

        if not report_code or not fight_text:

            self.status.warning("Enter a report code and fight number first.")

            return

        try:
            fight_id = int(fight_text)
        except ValueError:

            self.status.error("Fight number must be an integer.")

            return

        service = self._build_performance_service()

        self.status.info(f"Loading {report_code} #{fight_text} from ESO Logs...")

        try:

            summary, choices = service.list_actors(report_code, fight_id)

        except EsoLogsApiError as exc:

            self.status.error(str(exc))

            return

        except Exception as exc:

            self.status.error(f"Load fight failed: {exc}")

            return

        dashboard.show_fight_summary(summary)

        dashboard.set_actor_choices(choices)

        if choices:
            self.status.success(
                f"Loaded {summary.get('name', 'the fight')} -- "
                f"{len(choices)} player(s) found. Pick who you are."
            )
        else:
            self.status.warning(
                "Loaded the fight, but no players were found in it."
            )

    def show_performance_for_dashboard(self, dashboard: PerformanceDashboard):

        report_code = dashboard.report_code_value

        fight_text = dashboard.fight_id_value

        actor = dashboard.selected_actor()

        if not report_code or not fight_text or actor is None:

            self.status.warning("Load a fight and pick who you are first.")

            return

        try:
            fight_id = int(fight_text)
        except ValueError:

            self.status.error("Fight number must be an integer.")

            return

        service = self._build_performance_service()

        role = dashboard.selected_role()

        self.status.info(f"Building your {role} performance dashboard...")

        try:

            snapshot = service.build_snapshot(
                report_code, fight_id, actor.ActorId, actor.Label, role,
            )

        except EsoLogsApiError as exc:

            self.status.error(str(exc))

            return

        except Exception as exc:

            self.status.error(f"Building your dashboard failed: {exc}")

            return

        dashboard.show_snapshot(snapshot)

        self._rebuild_performance_tabs()

        self.status.success(
            f"{actor.Label}: {snapshot.OutputTotal:,.0f} {snapshot.OutputLabel} "
            f"({snapshot.OutputPerSecond:,.0f} {snapshot.OutputRateLabel})."
        )

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    def _current_performance_roster(self) -> PerformanceRoster:

        return PerformanceRoster(
            Members=[dashboard.model for dashboard in self.performance_dashboards]
        )

    def save_performance_dashboard(self):

        try:

            self.performance_path.parent.mkdir(parents=True, exist_ok=True)

            self.performance_path.write_text(
                json.dumps(
                    self._current_performance_roster().to_dict(),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            self.status.success("Performance Dashboard picks saved.")

        except Exception as exc:

            self.status.error(f"Save failed: {exc}")

    # --------------------------------------------------
    # Export
    # --------------------------------------------------

    def export_performance_csv(self):

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Performance Dashboard as CSV",
            "raid_performance.csv",
            "CSV Files (*.csv)",
        )

        if not filename:
            return

        try:

            with open(filename, "w", newline="", encoding="utf-8") as handle:

                writer = csv.writer(handle)

                writer.writerow(
                    [
                        "Member",
                        "Report",
                        "Fight",
                        "Fight Name",
                        "Who",
                        "Role",
                        "Fight Length (s)",
                        "Output Type",
                        "Total Output",
                        "Output Rate",
                        "Best Stretch",
                        "Top Buff Uptimes (name: %)",
                        "Top Debuff Uptimes (name: %)",
                        "Top Abilities (name: total)",
                    ]
                )

                for dashboard in self.performance_dashboards:

                    snapshot = getattr(dashboard, "_last_snapshot", None)

                    if snapshot is None:
                        continue

                    model = dashboard.model

                    buffs = "; ".join(
                        f"{u.Name}: {u.UptimePercent:.1f}%"
                        for u in snapshot.BuffUptimes
                    )

                    debuffs = "; ".join(
                        f"{u.Name}: {u.UptimePercent:.1f}%"
                        for u in snapshot.DebuffUptimes
                    )

                    abilities = "; ".join(
                        f"{a.Name}: {a.Total:,.0f}"
                        for a in snapshot.TopAbilities
                    )

                    writer.writerow(
                        [
                            model.Name,
                            model.ReportCode,
                            model.FightId,
                            snapshot.FightName,
                            snapshot.ActorLabel,
                            snapshot.Role,
                            f"{snapshot.FightDurationSeconds:.1f}",
                            snapshot.OutputLabel,
                            f"{snapshot.OutputTotal:.0f}",
                            f"{snapshot.OutputPerSecond:.0f} {snapshot.OutputRateLabel}",
                            snapshot.PeakWindowLabel,
                            buffs,
                            debuffs,
                            abilities,
                        ]
                    )

            self.status.success(f"Exported CSV to {filename}")

        except Exception as exc:

            self.status.error(f"CSV export failed: {exc}")
