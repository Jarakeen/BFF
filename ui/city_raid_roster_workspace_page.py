from __future__ import annotations

"""Urban Wilderness presentation for the canonical Raid Roster workspace.

The six Collectibles-style cards replace visible tabs as navigation. All existing roster,
character, team, availability, recruitment and archive services remain the data owners.
The visible composition deliberately blends the city-night and field-journal asset packs.
"""

from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_resource_path
from services.roster_share_formats import discord_roster_text, export_roster_csv
from ui.components.foundry_card import FoundryCard
from ui.themed_raid_roster_workspace_page import ThemedRaidRosterWorkspacePage


class CityRaidRosterWorkspacePage(ThemedRaidRosterWorkspacePage):
    """One-screen Roster dashboard plus card-driven detail views, with no visible tabs."""

    _CARD_INDEX = {
        "players": 0,
        "characters": 1,
        "teams": 2,
        "availability": 3,
        "recruitment": 4,
        "archive": 5,
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._install_city_dashboard()
        self.refresh()

    def _install_city_dashboard(self) -> None:
        self.header.title.setText("Roster")
        self.header.subtitle.setText("Same people. Different rooftops. Better runs.")
        self.header.department.setText("RAID • ROSTER")

        self.tabs.tabBar().hide()
        self.tabs.setDocumentMode(True)
        for key, card in self.metric_cards.items():
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setProperty("workspaceIndex", self._CARD_INDEX[key])
            card.installEventFilter(self)
            card.setToolTip(f"Open {key.title()} workspace")

        old_players = self.tabs.widget(0)
        dashboard = self._build_city_players_dashboard()
        self.tabs.removeTab(0)
        self.tabs.insertTab(0, dashboard, "PLAYERS")
        self.tabs.setCurrentIndex(0)
        if old_players is not None:
            old_players.deleteLater()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonRelease:
            index = watched.property("workspaceIndex") if hasattr(watched, "property") else None
            if isinstance(index, int) and 0 <= index < self.tabs.count():
                self.tabs.setCurrentIndex(index)
                return True
        return super().eventFilter(watched, event)

    def _build_city_players_dashboard(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        top = QHBoxLayout()
        roster = FoundryCard("Active Roster", "group")
        roster.addWidget(self.table)
        top.addWidget(roster, 7)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        quick = FoundryCard("Quick Actions", "warning")
        for title, callback in (
            ("Add Player", self._show_new_player_editor),
            ("Import Roster", self._import_roster),
            ("Manage Teams", lambda: self.tabs.setCurrentIndex(2)),
            ("Edit Availability", lambda: self.tabs.setCurrentIndex(3)),
            ("Send Message", self._copy_roster_message),
            ("Export Roster", self._export_roster),
        ):
            button = QPushButton(title)
            button.clicked.connect(callback)
            quick.addWidget(button)
        right_layout.addWidget(quick)
        right_layout.addWidget(self._theme_art("roster_people", prefer="city", fallback="Same people. Higher standards."), 1)
        top.addWidget(right, 3)
        root.addLayout(top, 5)

        bottom = QHBoxLayout()
        snapshot = FoundryCard("Team Snapshot", "group")
        self.city_team_snapshot = QLabel("")
        self.city_team_snapshot.setWordWrap(True)
        snapshot.addWidget(self.city_team_snapshot)
        bottom.addWidget(snapshot, 2)

        bottom.addWidget(self._theme_art("roster_team", prefer="field", fallback="A stronger tomorrow, with the same crew."), 3)

        needs = FoundryCard("Recruitment Needs", "group")
        self.city_recruitment_needs = QLabel("")
        self.city_recruitment_needs.setWordWrap(True)
        needs.addWidget(self.city_recruitment_needs)
        open_recruitment = QPushButton("Open Recruitment")
        open_recruitment.clicked.connect(lambda: self.tabs.setCurrentIndex(4))
        needs.addWidget(open_recruitment)
        bottom.addWidget(needs, 2)

        recent = FoundryCard("Recent Activity", "archive")
        self.city_recent_activity = QLabel("")
        self.city_recent_activity.setWordWrap(True)
        recent.addWidget(self.city_recent_activity)
        bottom.addWidget(recent, 3)
        root.addLayout(bottom, 2)

        note = FoundryCard("Field Note", "feather")
        note.setProperty("parchment", True)
        note_text = QLabel("Good people make hard things possible. Different rooftops. Same horizon.")
        note_text.setWordWrap(True)
        note.addWidget(note_text)
        root.addWidget(note)

        self.player_editor_panel = FoundryCard("Player Editor", "feather")
        self.player_editor_panel.addWidget(self.record)
        self.player_editor_panel.addWidget(self.actions)
        close_editor = QPushButton("Close Editor")
        close_editor.clicked.connect(lambda: self.player_editor_panel.setVisible(False))
        self.player_editor_panel.addWidget(close_editor)
        self.player_editor_panel.setVisible(False)
        root.addWidget(self.player_editor_panel)
        return page

    @staticmethod
    def _theme_art(stem: str, *, prefer: str, fallback: str) -> QLabel:
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumHeight(130)

        candidates = []
        if prefer == "field":
            candidates.extend((
                get_resource_path("assets", "themes", "bff", "field_journal", "roster", f"{stem}.jpg"),
                get_resource_path("assets", "themes", "bff", "city_night", "roster", f"{stem}.webp"),
            ))
        else:
            candidates.extend((
                get_resource_path("assets", "themes", "bff", "city_night", "roster", f"{stem}.webp"),
                get_resource_path("assets", "themes", "bff", "field_journal", "roster", f"{stem}.jpg"),
            ))

        pixmap = QPixmap()
        for path in candidates:
            if Path(path).is_file():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    break
        if pixmap.isNull():
            label.setText(fallback)
            label.setWordWrap(True)
        else:
            label.setPixmap(
                pixmap.scaled(520, 190, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        return label

    def _show_new_player_editor(self) -> None:
        self.tabs.setCurrentIndex(0)
        self.table.clearSelection()
        self.record.clear()
        self.player_editor_panel.setVisible(True)
        self.status.info("New player record ready.")

    def load_member(self, member_id: int) -> None:
        super().load_member(member_id)
        if hasattr(self, "player_editor_panel"):
            self.player_editor_panel.setVisible(True)

    def _import_roster(self) -> None:
        from ui.roster_import_workflow import _import_roster_from_file
        _import_roster_from_file(self)

    def _export_roster(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Export Roster", "roster.csv", "CSV (*.csv)")
        if not filename:
            return
        schedules = [
            schedule
            for team in self.roster_service.list_team_names()
            if (schedule := self.roster_service.get_team_schedule(team)) is not None
        ]
        target = export_roster_csv(filename, self.members, team_schedules=schedules)
        self.status.success(f"Roster exported: {target.name}")

    def _copy_roster_message(self) -> None:
        schedules = [
            schedule
            for team in self.roster_service.list_team_names()
            if (schedule := self.roster_service.get_team_schedule(team)) is not None
        ]
        text = discord_roster_text(self.members, team_schedules=schedules, title="Raid Roster")
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)
        self.status.success("Roster message copied to clipboard.")

    def refresh(self) -> None:
        super().refresh()
        if not hasattr(self, "city_team_snapshot"):
            return
        teams = self.roster_service.list_team_names()
        active = [member for member in self.members if str(member.Status or "").casefold() == "active"]
        recruits = self.workspace_state.list_recruits()
        archive = self.workspace_state.list_archive()
        self.city_team_snapshot.setText(
            f"{len(teams)} Teams    {len(self.members)} Total Players\n"
            f"{len(active)} Active    {len(recruits)} Recruiting\n"
            "Same people. Higher standards."
        )
        roles = [str(member.PrimaryRole or "").casefold() for member in active]
        tanks = sum("tank" in role for role in roles)
        healers = sum("heal" in role for role in roles)
        damage = max(0, len(active) - tanks - healers)
        self.city_recruitment_needs.setText(
            f"Tank       {tanks}\nHealer     {healers}\nDamage     {damage}\n"
            f"Pipeline   {len(recruits)}\n\nOpen Recruitment to manage exact needs."
        )
        activity: list[str] = []
        for recruit in recruits[:4]:
            activity.append(f"Recruiting · {recruit.player_name} · {recruit.status.title()}")
        for record in archive[:4]:
            activity.append(f"Archived · {record.display_name} · {record.entity_type}")
        self.city_recent_activity.setText("\n".join(activity[:7]) or "No recent roster workflow activity yet.")


__all__ = ["CityRaidRosterWorkspacePage"]
