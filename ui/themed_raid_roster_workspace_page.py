from __future__ import annotations

"""City After Midnight Roster dashboard.

The rebuilt Roster intentionally has no top-level tabs. The six Collectibles-style
summary cards are navigation/summary surfaces; detailed editors stay available as
explicit workspaces so the canonical roster/team/availability/recruitment services
remain the only data owners.

The dashboard itself contains no decorative roster photo/filler panels. Parchment
sketches belong only on deliberate field-journal note surfaces, while full-color art
belongs only on dark framed surfaces elsewhere in the app.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.roster_share_formats import discord_roster_text, export_roster_csv
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.raid_roster_workspace_page import RaidRosterWorkspacePage, _MetricCard, _clean
from widgets.roster_actions import RosterActions
from widgets.roster_record import RosterRecord
from widgets.roster_table import RosterTable


class _DashboardMetricCard(_MetricCard):
    clicked = Signal()

    def __init__(self, ordinal: int, title: str, glyph: str, parent=None) -> None:
        super().__init__(ordinal, title, glyph, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(f"Open {title}")

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ThemedRaidRosterWorkspacePage(RaidRosterWorkspacePage):
    """Single-page roster dashboard with stable, art-independent geometry."""

    def __init__(self, parent=None) -> None:
        self._detail_dialogs: dict[str, QDialog] = {}
        super().__init__(parent)
        self.refresh_theme_assets()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Roster",
            subtitle="Built from static, stubbornness, and one more pull.",
            department="RAID • PEOPLE & TEAMS",
        )
        self.set_header(self.header)

        self.team_filter = self._make_team_filter()
        self.search = self._make_search()
        self.header.add_context_widget(self.team_filter)
        self.header.add_context_widget(self.search)

        metrics = QWidget()
        metrics_layout = QGridLayout(metrics)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setHorizontalSpacing(6)
        metrics_layout.setVerticalSpacing(6)
        specs = (
            (1, "Players", "●●●", "players"),
            (2, "Characters", "♜", "characters"),
            (3, "Teams", "◆", "teams"),
            (4, "Availability", "▣", "availability"),
            (5, "Recruitment", "◇", "recruitment"),
            (6, "Archive", "▤", "archive"),
        )
        self.metric_cards: dict[str, _DashboardMetricCard] = {}
        for column, (ordinal, title, glyph, detail_key) in enumerate(specs):
            card = _DashboardMetricCard(ordinal, title, glyph)
            card.clicked.connect(lambda key=detail_key: self._show_detail(key))
            self.metric_cards[title.casefold()] = card
            metrics_layout.addWidget(card, 0, column)
            metrics_layout.setColumnStretch(column, 1)
        self.workspace_layout.addWidget(metrics)

        self._build_detail_workspaces()

        dashboard = QWidget()
        grid = QGridLayout(dashboard)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 5)
        grid.setColumnStretch(1, 2)

        roster_card = FoundryCard("Active Roster", "group")
        self.table = RosterTable()
        roster_card.addWidget(self.table)
        grid.addWidget(roster_card, 0, 0, 2, 1)

        # Keep functional cards in the right column. Decorative filler no longer
        # owns layout space or influences the page's minimum size.
        grid.addWidget(self._build_quick_actions_card(), 0, 1)

        self.recent_activity_card = FoundryCard("Recent Activity", "stopwatch")
        self.recent_activity = QTableWidget(0, 2)
        self.recent_activity.setHorizontalHeaderLabels(("Activity", "When"))
        self.recent_activity.verticalHeader().setVisible(False)
        self.recent_activity.horizontalHeader().setStretchLastSection(False)
        self.recent_activity.horizontalHeader().setSectionResizeMode(
            0, self.recent_activity.horizontalHeader().ResizeMode.Stretch
        )
        self.recent_activity.horizontalHeader().setSectionResizeMode(
            1, self.recent_activity.horizontalHeader().ResizeMode.ResizeToContents
        )
        self.recent_activity.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_activity.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.recent_activity_card.addWidget(self.recent_activity)
        grid.addWidget(self.recent_activity_card, 1, 1)

        lower = QWidget()
        lower_layout = QHBoxLayout(lower)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(8)
        lower_layout.addWidget(self._build_team_snapshot_card(), 1)
        lower_layout.addWidget(self._build_recruitment_needs_card(), 1)
        grid.addWidget(lower, 2, 0, 1, 2)

        self.add_workspace(dashboard)
        self.status = FoundryStatusBar()
        self.set_status(self.status)

    def _make_team_filter(self):
        from PySide6.QtWidgets import QComboBox

        combo = QComboBox()
        combo.addItem("All Teams")
        combo.setMinimumWidth(175)
        combo.currentTextChanged.connect(self._apply_player_filter)
        return combo

    def _make_search(self):
        from PySide6.QtWidgets import QLineEdit

        search = QLineEdit()
        search.setMinimumWidth(285)
        search.setPlaceholderText("Search players, characters, or notes…")
        search.textChanged.connect(self._apply_player_filter)
        return search

    def _build_detail_workspaces(self) -> None:
        self.record = RosterRecord()
        self.actions = RosterActions()
        player_page = QWidget()
        player_layout = QVBoxLayout(player_page)
        player_layout.setContentsMargins(8, 8, 8, 8)
        player_card = FoundryCard("Player Record", "person")
        player_card.addWidget(self.record)
        player_layout.addWidget(player_card, 1)
        player_layout.addWidget(self.actions)

        self._install_detail_dialog("players", "Player Record", player_page, (760, 720))
        self._install_detail_dialog(
            "characters",
            "Characters",
            RaidRosterWorkspacePage._build_characters_tab(self),
            (1050, 720),
        )
        self._install_detail_dialog(
            "teams", "Teams", RaidRosterWorkspacePage._build_teams_tab(self), (1120, 760)
        )
        self._install_detail_dialog(
            "availability",
            "Availability",
            RaidRosterWorkspacePage._build_availability_tab(self),
            (1250, 720),
        )
        self._install_detail_dialog(
            "recruitment",
            "Recruitment",
            RaidRosterWorkspacePage._build_recruitment_tab(self),
            (1180, 760),
        )
        self._install_detail_dialog(
            "archive", "Archive", RaidRosterWorkspacePage._build_archive_tab(self), (1050, 680)
        )

    def _install_detail_dialog(self, key: str, title: str, page: QWidget, size: tuple[int, int]) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(*size)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(page)
        self._detail_dialogs[key] = dialog

    def _show_detail(self, key: str) -> None:
        dialog = self._detail_dialogs.get(key)
        if dialog is None:
            return
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _build_quick_actions_card(self) -> FoundryCard:
        card = FoundryCard("Quick Actions", "warning")
        actions = (
            ("Add Player", self._new_player),
            ("Import Roster", self._import_roster),
            ("Manage Teams", lambda: self._show_detail("teams")),
            ("Edit Availability", lambda: self._show_detail("availability")),
            ("Send Message", self._copy_team_message),
            ("Export Roster", self._export_roster),
        )
        for label, callback in actions:
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, fn=callback: fn())
            card.addWidget(button)
        return card

    def _build_team_snapshot_card(self) -> FoundryCard:
        card = FoundryCard("Team Snapshot", "group")
        self.team_snapshot_label = QLabel("")
        self.team_snapshot_label.setWordWrap(True)
        self.team_snapshot_label.setProperty("rosterDashboardSummary", True)
        card.addWidget(self.team_snapshot_label)
        return card

    def _build_recruitment_needs_card(self) -> FoundryCard:
        card = FoundryCard("Recruitment Needs", "person")
        self.recruitment_needs_label = QLabel("")
        self.recruitment_needs_label.setWordWrap(True)
        self.recruitment_needs_label.setProperty("rosterDashboardSummary", True)
        card.addWidget(self.recruitment_needs_label)
        return card

    def _new_player(self) -> None:
        self.table.clearSelection()
        self.record.clear()
        self._show_detail("players")
        self.status.info("New player record. Fill it in and save.")

    def load_member(self, member_id: int) -> None:
        super().load_member(member_id)

    def _import_roster(self) -> None:
        from ui.roster_import_workflow import _import_roster_from_file

        _import_roster_from_file(self)

    def _copy_team_message(self) -> None:
        team = _clean(self.team_filter.currentText())
        members = self.members if not team or team == "All Teams" else self._team_members(team)
        schedules = [
            schedule
            for name in self.roster_service.list_team_names()
            if (schedule := self.roster_service.get_team_schedule(name)) is not None
        ]
        title = team if team and team != "All Teams" else "Raid Roster"
        text = discord_roster_text(members, team_schedules=schedules, title=title)
        QApplication.clipboard().setText(text)
        self.status.success("Roster message copied to the clipboard.")

    def _export_roster(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Roster",
            "roster.csv",
            "CSV (*.csv)",
        )
        if not filename:
            return
        team = _clean(self.team_filter.currentText())
        members = self.members if not team or team == "All Teams" else self._team_members(team)
        schedules = [
            schedule
            for name in self.roster_service.list_team_names()
            if (schedule := self.roster_service.get_team_schedule(name)) is not None
        ]
        target = export_roster_csv(filename, members, team_schedules=schedules)
        self.status.success(f"Roster exported: {target.name}")

    def refresh(self) -> None:
        super().refresh()
        self._refresh_dashboard_cards()

    def _refresh_dashboard_cards(self) -> None:
        if not hasattr(self, "team_snapshot_label"):
            return

        active = [member for member in self.members if _clean(member.Status).casefold() == "active"]
        teams = self.roster_service.list_team_names()
        recruits = self.workspace_state.list_recruits()

        role_counts = {"tank": 0, "healer": 0, "damage": 0, "support": 0, "other": 0}
        for member in active:
            role = _clean(member.PrimaryRole).casefold()
            if "tank" in role:
                role_counts["tank"] += 1
            elif "heal" in role:
                role_counts["healer"] += 1
            elif any(token in role for token in ("damage", "dps", "dd")):
                role_counts["damage"] += 1
            elif "support" in role:
                role_counts["support"] += 1
            else:
                role_counts["other"] += 1

        self.team_snapshot_label.setText(
            f"{len(teams)}  Teams     {len(active)}  Active players\n"
            f"{role_counts['tank']}  Tanks     {role_counts['healer']}  Healers     "
            f"{role_counts['damage']}  Damage     {role_counts['support']}  Support"
        )

        recruit_roles: dict[str, int] = {}
        for candidate in recruits:
            role = _clean(candidate.desired_role) or "Unspecified"
            recruit_roles[role] = recruit_roles.get(role, 0) + 1
        if recruit_roles:
            lines = [
                f"{role}  •  {count} candidate{'s' if count != 1 else ''}"
                for role, count in sorted(recruit_roles.items())
            ]
            self.recruitment_needs_label.setText("\n".join(lines[:6]))
        else:
            self.recruitment_needs_label.setText("No active recruitment candidates.")

        activity: list[tuple[str, str]] = []
        for candidate in recruits:
            when = candidate.updated_at or candidate.created_at
            activity.append((f"Recruitment · {candidate.player_name} · {candidate.status.title()}", when))
        for record in self.workspace_state.list_archive():
            activity.append((f"Archived · {record.display_name}", record.archived_at))
        activity.sort(key=lambda item: item[1], reverse=True)

        self.recent_activity.setRowCount(0)
        for event, when in activity[:8]:
            row = self.recent_activity.rowCount()
            self.recent_activity.insertRow(row)
            self.recent_activity.setItem(row, 0, QTableWidgetItem(event))
            display_when = when.replace("T", " ")[:16] if when else "—"
            self.recent_activity.setItem(row, 1, QTableWidgetItem(display_when))
        if not activity:
            self.recent_activity.setRowCount(1)
            self.recent_activity.setItem(
                0, 0, QTableWidgetItem("No roster workflow activity recorded yet.")
            )
            self.recent_activity.setItem(0, 1, QTableWidgetItem("—"))

    def refresh_theme_assets(self) -> None:
        self.header.subtitle.setText("Built from static, stubbornness, and one more pull.")
        refresh_header = getattr(self.header, "refresh_visual_theme", None)
        if callable(refresh_header):
            refresh_header()


__all__ = ["ThemedRaidRosterWorkspacePage"]
