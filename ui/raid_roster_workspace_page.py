from __future__ import annotations

"""Raid-lead-first Roster workspace.

This page is a direct, explicit composition surface. It uses canonical roster/team/build
services and the additive roster workflow-state service; it does not install or depend on
runtime UI monkeypatches. Both visual themes use the same layout and information hierarchy.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir, get_resource_path
from models.roster_model import ESO_CLASSES, ROLES, RosterMember
from models.team_schedule import TeamSchedule
from services.accessibility_preferences import VISUAL_THEME_RYLO
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_service import RosterService
from services.roster_workspace_state_service import (
    MemberAvailability,
    RecruitmentCandidate,
    RosterWorkspaceStateService,
)
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from widgets.roster_actions import RosterActions
from widgets.roster_record import RosterRecord
from widgets.roster_table import RosterTable


_DAY_FIELDS = (
    ("Mon", "monday"),
    ("Tue", "tuesday"),
    ("Wed", "wednesday"),
    ("Thu", "thursday"),
    ("Fri", "friday"),
    ("Sat", "saturday"),
    ("Sun", "sunday"),
)
_AVAILABILITY_LABELS = (
    ("Unknown", "unknown"),
    ("Available", "available"),
    ("Unavailable", "unavailable"),
    ("Maybe", "maybe"),
    ("Late", "late"),
    ("Tentative", "tentative"),
)
_RECRUITMENT_STATUS = (
    ("New", "new"),
    ("Review", "review"),
    ("Interview", "interview"),
    ("Trial", "trial"),
    ("Accepted", "accepted"),
    ("Declined", "declined"),
)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _theme_is_rylo() -> bool:
    app = QApplication.instance()
    return bool(app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO)


def _set_readonly(item: QTableWidgetItem) -> QTableWidgetItem:
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class _MetricCard(QFrame):
    """Collectibles-style summary card reused by both visual themes."""

    def __init__(self, ordinal: int, title: str, glyph: str, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("rosterMetricCard", True)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 9, 12, 9)
        root.setSpacing(5)

        title_row = QHBoxLayout()
        number = QLabel(str(ordinal))
        number.setProperty("rosterMetricOrdinal", True)
        label = QLabel(title.upper())
        label.setProperty("rosterMetricTitle", True)
        title_row.addWidget(number)
        title_row.addWidget(label, 1)
        root.addLayout(title_row)

        middle = QHBoxLayout()
        icon = QLabel(glyph)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setProperty("rosterMetricIcon", True)
        icon.setFixedWidth(50)
        middle.addWidget(icon)
        self.value = QLabel("0")
        self.value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value.setProperty("rosterMetricValue", True)
        middle.addWidget(self.value, 1)
        root.addLayout(middle)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setProperty("rosterMetricProgress", True)
        root.addWidget(self.progress)

        self.caption = QLabel("")
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setProperty("muted", True)
        root.addWidget(self.caption)

    def set_metric(self, value: str, percent: int, caption: str) -> None:
        self.value.setText(str(value))
        self.progress.setValue(max(0, min(100, int(percent))))
        self.caption.setText(caption)


class _ThemeSketch(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(150)
        self.setProperty("rosterSketch", True)
        self.refresh_theme()

    def refresh_theme(self) -> None:
        filename = "roster_rylo_sketch.svg" if _theme_is_rylo() else "roster_foundry_sketch.svg"
        path = get_resource_path("assets", "themes", "bff", "grimoire", "assets", filename)
        pixmap = QPixmap(str(path)) if Path(path).exists() else QPixmap()
        if pixmap.isNull():
            self.setText("Same people. Better prepared.")
            return
        self.setPixmap(
            pixmap.scaled(
                520,
                220,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class _TeamColorArt(QLabel):
    """Fixed-height full-color art for the Teams lower-left slot.

    The image is cropped into the widget's current width. It never contributes
    an image-driven size hint that can enlarge the Teams workspace.
    """

    _ASSET = ("assets", "themes", "bff", "urban_wilderness", "notes", "color_night_rect_1.png")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source = QPixmap(str(get_resource_path(*self._ASSET)))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(165)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setProperty("rosterTeamColorArt", True)
        self.setToolTip("Same people. Better prepared.")
        self._refresh_pixmap()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        if self._source.isNull() or self.width() <= 0:
            self.clear()
            if self._source.isNull():
                self.setText("Same people. Better prepared.")
            return

        scaled = self._source.scaled(
            max(1, self.width()),
            self.height(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (scaled.width() - self.width()) // 2)
        y = max(0, (scaled.height() - self.height()) // 2)
        self.setPixmap(
            scaled.copy(
                x,
                y,
                min(self.width(), scaled.width()),
                min(self.height(), scaled.height()),
            )
        )


class RaidRosterWorkspacePage(FoundryPage):
    """Unified Roster / Characters / Teams / Availability / Recruitment / Archive."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        data_dir = get_data_dir()
        self.database = EsoDatabase(data_dir / "eso.db")
        self.roster_service = RosterService(self.database)
        self.workspace_state = RosterWorkspaceStateService(self.database)
        self.build_library = BuildService(data_dir / "builds.json")
        self.members: list[RosterMember] = []
        self._build_ui()
        self._connect_signals()
        self.refresh()

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        subtitle = (
            "Built from static, stubbornness, and one more pull."
            if _theme_is_rylo()
            else "People make the journey. Keep good records."
        )
        self.header = FoundryHeader(
            title="Roster",
            subtitle=subtitle,
            department="RAID • PEOPLE & TEAMS",
        )
        self.set_header(self.header)

        self.team_filter = QComboBox()
        self.team_filter.addItem("All Teams")
        self.team_filter.currentTextChanged.connect(self._apply_player_filter)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search players, characters, teams, builds...")
        self.search.textChanged.connect(self._apply_player_filter)
        self.header.add_context_widget(self.team_filter)
        self.header.add_context_widget(self.search)

        add_player = QPushButton("Add Player")
        add_player.setProperty("primary", True)
        add_player.clicked.connect(self._new_player)
        self.header.add_context_widget(add_player)

        metrics = QWidget()
        metrics_layout = QGridLayout(metrics)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setHorizontalSpacing(8)
        metrics_layout.setVerticalSpacing(8)
        specs = (
            (1, "Players", "●●●"),
            (2, "Characters", "♜"),
            (3, "Teams", "◆"),
            (4, "Availability", "▣"),
            (5, "Recruitment", "◇"),
            (6, "Archive", "▤"),
        )
        self.metric_cards: dict[str, _MetricCard] = {}
        for column, (ordinal, title, glyph) in enumerate(specs):
            card = _MetricCard(ordinal, title, glyph)
            self.metric_cards[title.casefold()] = card
            metrics_layout.addWidget(card, 0, column)
            metrics_layout.setColumnStretch(column, 1)
        self.workspace_layout.addWidget(metrics)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_players_tab(), "PLAYERS")
        self.tabs.addTab(self._build_characters_tab(), "CHARACTERS")
        self.tabs.addTab(self._build_teams_tab(), "TEAMS")
        self.tabs.addTab(self._build_availability_tab(), "AVAILABILITY")
        self.tabs.addTab(self._build_recruitment_tab(), "RECRUITMENT")
        self.tabs.addTab(self._build_archive_tab(), "ARCHIVE")
        self.add_workspace(self.tabs)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    def _build_players_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)

        roster_card = FoundryCard("Active Roster", "group")
        self.table = RosterTable()
        roster_card.addWidget(self.table)
        split.addWidget(roster_card)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        record_card = FoundryCard("Selected Player", "feather")
        self.record = RosterRecord()
        record_card.addWidget(self.record)
        right_layout.addWidget(record_card, 2)
        self.player_sketch = _ThemeSketch()
        right_layout.addWidget(self.player_sketch, 1)
        split.addWidget(right)
        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 2)
        root.addWidget(split, 1)

        self.actions = RosterActions()
        root.addWidget(self.actions)
        return page

    def _build_characters_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        split = QSplitter(Qt.Orientation.Horizontal)
        tree_card = FoundryCard("Players → Characters → Builds", "group")
        self.character_tree = QTreeWidget()
        self.character_tree.setHeaderLabels(("Identity", "Class / Role", "Teams"))
        self.character_tree.setAlternatingRowColors(True)
        self.character_tree.currentItemChanged.connect(self._show_character_detail)
        tree_card.addWidget(self.character_tree)
        split.addWidget(tree_card)

        self.character_detail = FoundryCard("Character Detail", "feather")
        self.character_detail_body = QLabel("Select a player, character, or build.")
        self.character_detail_body.setWordWrap(True)
        self.character_detail.addWidget(self.character_detail_body)
        self.character_detail.addStretch(1)
        split.addWidget(self.character_detail)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        root.addWidget(split, 1)
        return page

    def _build_teams_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        top = QHBoxLayout()
        self.team_combo = QComboBox()
        self.team_combo.currentTextChanged.connect(self._refresh_team_detail)
        self.new_team_name = QLineEdit()
        self.new_team_name.setPlaceholderText("New team name...")
        create = QPushButton("Create Team")
        create.setProperty("primary", True)
        create.clicked.connect(self._create_team)
        top.addWidget(QLabel("TEAM"))
        top.addWidget(self.team_combo, 2)
        top.addStretch(1)
        top.addWidget(self.new_team_name, 2)
        top.addWidget(create)
        root.addLayout(top)

        upper = QHBoxLayout()
        members_card = FoundryCard("Team Members", "group")
        self.team_members_table = QTableWidget(0, 6)
        self.team_members_table.setHorizontalHeaderLabels(
            ("Player", "Character", "Class", "Role", "Status", "Teams")
        )
        self.team_members_table.verticalHeader().setVisible(False)
        self.team_members_table.horizontalHeader().setStretchLastSection(True)
        self.team_members_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        members_card.addWidget(self.team_members_table)
        upper.addWidget(members_card, 3)

        schedule_card = FoundryCard("Team Schedule & Defaults", "stopwatch")
        form = QFormLayout()
        self.team_days = QLineEdit()
        self.team_days.setPlaceholderText("Mon, Wed")
        self.team_time = QLineEdit()
        self.team_time.setPlaceholderText("9:00 PM")
        self.team_timezone = QLineEdit()
        self.team_timezone.setPlaceholderText("America/New_York")
        self.team_focus = QLineEdit()
        self.team_focus.setPlaceholderText("Current progression focus")
        self.team_discord = QLineEdit()
        self.team_discord.setPlaceholderText("https://discord.gg/... or team Discord/channel link")
        self.team_discord.setToolTip(
            "Optional Discord invite, server, or channel link for this team."
        )
        form.addRow("Raid days", self.team_days)
        form.addRow("Start time", self.team_time)
        form.addRow("Timezone", self.team_timezone)
        form.addRow("Current focus", self.team_focus)
        form.addRow("Discord", self.team_discord)
        schedule_card.addLayout(form)
        save = QPushButton("Save Team Defaults")
        save.setProperty("primary", True)
        save.clicked.connect(self._save_team_schedule)
        schedule_card.addWidget(save)
        self.team_schedule_summary = QLabel("")
        self.team_schedule_summary.setWordWrap(True)
        schedule_card.addWidget(self.team_schedule_summary)
        upper.addWidget(schedule_card, 2)
        root.addLayout(upper, 3)

        lower = QHBoxLayout()
        self.team_sketch = _TeamColorArt()
        lower.addWidget(self.team_sketch, 2)
        self.team_stats = FoundryCard("Team Snapshot", "compass")
        self.team_stats_label = QLabel("")
        self.team_stats_label.setWordWrap(True)
        self.team_stats.addWidget(self.team_stats_label)
        lower.addWidget(self.team_stats, 1)
        root.addLayout(lower, 1)
        return page

    def _build_availability_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        card = FoundryCard("Weekly Availability", "stopwatch")
        self.availability_table = QTableWidget(0, 11)
        self.availability_table.setHorizontalHeaderLabels(
            ("Player", "Character", *(short for short, _ in _DAY_FIELDS), "Preferred Times", "Notes")
        )
        self.availability_table.verticalHeader().setVisible(False)
        self.availability_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.availability_table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Stretch)
        card.addWidget(self.availability_table)
        save = QPushButton("Save Availability")
        save.setProperty("primary", True)
        save.clicked.connect(self._save_availability)
        card.addWidget(save)
        root.addWidget(card, 1)
        return page

    def _build_recruitment_tab(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        card = FoundryCard("Recruitment Pipeline", "group")
        self.recruit_table = QTableWidget(0, 8)
        self.recruit_table.setHorizontalHeaderLabels(
            ("Candidate", "Character", "Role", "Class", "Team", "Availability", "Status", "Notes")
        )
        self.recruit_table.verticalHeader().setVisible(False)
        self.recruit_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.recruit_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.recruit_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.recruit_table.horizontalHeader().setStretchLastSection(True)
        self.recruit_table.itemSelectionChanged.connect(self._load_selected_recruit)
        card.addWidget(self.recruit_table)
        root.addWidget(card, 3)

        editor = FoundryCard("Candidate", "feather")
        form = QFormLayout()
        self.recruit_id: int | None = None
        self.recruit_player = QLineEdit()
        self.recruit_character = QLineEdit()
        self.recruit_role = QComboBox()
        self.recruit_role.addItems([item for item in ROLES if item])
        self.recruit_class = QComboBox()
        self.recruit_class.addItems([item for item in ESO_CLASSES if item])
        self.recruit_team = QComboBox()
        self.recruit_team.setEditable(True)
        self.recruit_availability = QLineEdit()
        self.recruit_status = QComboBox()
        for label, key in _RECRUITMENT_STATUS:
            self.recruit_status.addItem(label, key)
        self.recruit_notes = QTextEdit()
        self.recruit_notes.setMaximumHeight(100)
        form.addRow("Player", self.recruit_player)
        form.addRow("Character", self.recruit_character)
        form.addRow("Role", self.recruit_role)
        form.addRow("Class", self.recruit_class)
        form.addRow("Target team", self.recruit_team)
        form.addRow("Availability", self.recruit_availability)
        form.addRow("Status", self.recruit_status)
        form.addRow("Notes", self.recruit_notes)
        editor.addLayout(form)
        buttons = QHBoxLayout()
        new = QPushButton("New")
        new.clicked.connect(self._clear_recruit_editor)
        save = QPushButton("Save Candidate")
        save.setProperty("primary", True)
        save.clicked.connect(self._save_recruit)
        archive = QPushButton("Archive")
        archive.clicked.connect(self._archive_recruit)
        buttons.addWidget(new)
        buttons.addWidget(save)
        buttons.addWidget(archive)
        editor.addLayout(buttons)
        root.addWidget(editor, 2)
        return page

    def _build_archive_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        intro = QLabel(
            "Historical roster workflow records live here. Canonical players, characters, and saved builds remain owned by their source services."
        )
        intro.setWordWrap(True)
        intro.setProperty("pageSubtitle", True)
        root.addWidget(intro)
        card = FoundryCard("Archive", "archive")
        self.archive_table = QTableWidget(0, 6)
        self.archive_table.setHorizontalHeaderLabels(
            ("Name", "Type", "Reason", "Related Team", "Archived", "Reference")
        )
        self.archive_table.verticalHeader().setVisible(False)
        self.archive_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.archive_table.horizontalHeader().setStretchLastSection(True)
        card.addWidget(self.archive_table)
        root.addWidget(card, 1)
        return page

    # ------------------------------------------------------------------
    # Common actions
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.table.memberSelected.connect(self.load_member)
        self.actions.newRequested.connect(self._new_player)
        self.actions.saveRequested.connect(self._save_player)
        self.actions.deleteRequested.connect(self._archive_selected_player)
        self.actions.refreshRequested.connect(self.refresh)

    def load_member(self, member_id: int) -> None:
        member = self.roster_service.get_member(int(member_id))
        if member is not None:
            self.record.load(member)

    def _new_player(self) -> None:
        self.tabs.setCurrentIndex(0)
        self.table.clearSelection()
        self.record.clear()
        self.status.info("New player record. Fill it in and save.")

    def _save_player(self) -> None:
        try:
            model = self.record.model
            if not _clean(model.PlayerName):
                self.status.warning("Player Name is required.")
                return
            if model.Id is None:
                member_id = self.roster_service.create_member(model)
            else:
                self.roster_service.update_member(model)
                member_id = int(model.Id)
            self.refresh()
            self.table.select_member_id(member_id)
            self.status.success(f"Saved {_clean(model.PlayerName)}.")
        except Exception as exc:
            self.status.error(f"Save failed: {exc}")

    def _archive_selected_player(self) -> None:
        member = self.record.model
        if member.Id is None:
            self.status.warning("Select a player first.")
            return
        answer = QMessageBox.question(
            self,
            "Archive Player",
            f"Archive {member.PlayerName or 'this player'} from the active Roster?\n\nThe canonical player/character/build records are not deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.workspace_state.archive(
            entity_type="player",
            entity_key=str(member.Id),
            display_name=member.PlayerName,
            reason="Archived from Roster",
            related_team=member.Team,
            payload=member.to_dict(),
        )
        member.Status = "Inactive"
        self.roster_service.update_member(member)
        self.record.clear()
        self.refresh()
        self.status.success(f"Archived {member.PlayerName} from the active Roster.")

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        try:
            selected_id = self.table.selected_member_id() if hasattr(self, "table") else None
            self.members = self.roster_service.list_members()
            self.table.load_members(self.members)
            self.record.set_team_choices(self.roster_service.list_team_names())
            if selected_id is not None:
                self.table.select_member_id(selected_id)
            self._refresh_team_filters()
            self._refresh_metrics()
            self._refresh_characters()
            self._refresh_teams()
            self._refresh_availability()
            self._refresh_recruitment()
            self._refresh_archive()
            self.status.info(f"{len(self.members)} roster record(s) loaded.")
        except Exception as exc:
            self.status.error(f"Roster refresh failed: {exc}")

    def _refresh_team_filters(self) -> None:
        current = self.team_filter.currentText()
        teams = self.roster_service.list_team_names()
        self.team_filter.blockSignals(True)
        self.team_filter.clear()
        self.team_filter.addItem("All Teams")
        self.team_filter.addItems(teams)
        if current:
            self.team_filter.setCurrentText(current)
        self.team_filter.blockSignals(False)
        self.recruit_team.clear()
        self.recruit_team.addItems(teams)

    def _refresh_metrics(self) -> None:
        active = [member for member in self.members if member.Status.casefold() == "active"]
        teams = self.roster_service.list_team_names()
        catalog = self.build_library.canonical.catalog_service.load()
        characters = [row for row in catalog.get("characters", []) if isinstance(row, dict)]
        availability = [
            self.workspace_state.availability_for(member.Id)
            for member in self.members
            if member.Id is not None
        ]
        responding = sum(
            1
            for item in availability
            if any(getattr(item, field) != "unknown" for _, field in _DAY_FIELDS)
        )
        recruits = self.workspace_state.list_recruits()
        archive = self.workspace_state.list_archive()

        self.metric_cards["players"].set_metric(
            f"{len(active)} / {len(self.members) or 0}",
            round(100 * len(active) / max(1, len(self.members))),
            "Active players",
        )
        self.metric_cards["characters"].set_metric(
            str(len(characters)),
            min(100, round(100 * len(characters) / max(1, len(self.members) * 2))),
            "Canonical characters",
        )
        self.metric_cards["teams"].set_metric(str(len(teams)), min(100, len(teams) * 20), "Teams configured")
        self.metric_cards["availability"].set_metric(
            f"{responding} / {len(availability)}",
            round(100 * responding / max(1, len(availability))),
            "Availability recorded",
        )
        self.metric_cards["recruitment"].set_metric(str(len(recruits)), min(100, len(recruits) * 15), "Candidates in pipeline")
        self.metric_cards["archive"].set_metric(str(len(archive)), min(100, len(archive) * 5), "Historical records")

    def _apply_player_filter(self, *_args) -> None:
        if not hasattr(self, "table"):
            return
        query = _clean(self.search.text()).casefold()
        team = _clean(self.team_filter.currentText())
        for row in range(self.table.rowCount()):
            text = " ".join(
                _clean(self.table.item(row, col).text())
                for col in range(self.table.columnCount())
                if self.table.item(row, col) is not None
            ).casefold()
            row_team = _clean(self.table.item(row, 5).text()) if self.table.item(row, 5) else ""
            visible = (not query or query in text) and (
                not team or team == "All Teams" or team.casefold() in row_team.casefold()
            )
            self.table.setRowHidden(row, not visible)

    # ------------------------------------------------------------------
    # Characters
    # ------------------------------------------------------------------

    def _refresh_characters(self) -> None:
        catalog = self.build_library.canonical.catalog_service.load()
        players = {
            _clean(row.get("player_id")): row
            for row in catalog.get("players", [])
            if isinstance(row, dict) and _clean(row.get("player_id"))
        }
        chars_by_player: dict[str, list[dict]] = {}
        for row in catalog.get("characters", []):
            if isinstance(row, dict):
                chars_by_player.setdefault(_clean(row.get("player_id")), []).append(row)
        builds_by_char: dict[str, list[dict]] = {}
        for row in catalog.get("builds", []):
            if isinstance(row, dict):
                builds_by_char.setdefault(_clean(row.get("character_id")), []).append(row)

        self.character_tree.clear()
        for player_id, player in sorted(players.items(), key=lambda item: _clean(item[1].get("gamertag")).casefold()):
            gamertag = _clean(player.get("gamertag")) or "Unnamed Player"
            player_item = QTreeWidgetItem((gamertag, "Player", ""))
            player_item.setData(0, Qt.ItemDataRole.UserRole, ("player", player_id))
            self.character_tree.addTopLevelItem(player_item)
            for character in sorted(chars_by_player.get(player_id, []), key=lambda row: _clean(row.get("name")).casefold()):
                character_id = _clean(character.get("character_id"))
                char_item = QTreeWidgetItem(
                    (
                        _clean(character.get("name")) or "Unnamed Character",
                        _clean(character.get("eso_class")) or "Class not set",
                        "Character",
                    )
                )
                char_item.setData(0, Qt.ItemDataRole.UserRole, ("character", character_id))
                player_item.addChild(char_item)
                for build in sorted(builds_by_char.get(character_id, []), key=lambda row: _clean(row.get("name")).casefold()):
                    payload = build.get("payload") if isinstance(build.get("payload"), dict) else {}
                    build_item = QTreeWidgetItem(
                        (
                            _clean(build.get("name")) or "Default",
                            _clean(payload.get("Role")) or "Role not set",
                            "Build",
                        )
                    )
                    build_item.setData(0, Qt.ItemDataRole.UserRole, ("build", _clean(build.get("build_id"))))
                    char_item.addChild(build_item)
        self.character_tree.expandToDepth(1)
        if self.character_tree.topLevelItemCount():
            self.character_tree.setCurrentItem(self.character_tree.topLevelItem(0))

    def _show_character_detail(self, item, _previous=None) -> None:
        if item is None:
            self.character_detail_body.setText("Select a player, character, or build.")
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, tuple) or len(data) != 2:
            self.character_detail_body.setText(item.text(0))
            return
        kind, identity = data
        catalog = self.build_library.canonical.catalog_service
        if kind == "player":
            player = catalog.get_player(identity) or {}
            characters = catalog.characters_for_player(identity)
            self.character_detail.set_title(_clean(player.get("gamertag")) or "Player")
            self.character_detail_body.setText(f"Characters: {len(characters)}\nCanonical player id: {identity}")
        elif kind == "character":
            character = catalog.get_character(identity) or {}
            player = catalog.player_for_character(identity) or {}
            builds = catalog.builds_for_character(identity)
            self.character_detail.set_title(_clean(character.get("name")) or "Character")
            self.character_detail_body.setText(
                f"Player: {_clean(player.get('gamertag')) or 'Unknown'}\n"
                f"Class: {_clean(character.get('eso_class')) or 'Not set'}\n"
                f"Race: {_clean(character.get('race')) or 'Not set'}\n"
                f"Saved builds: {len(builds)}"
            )
        else:
            build = catalog.get_build(identity) or {}
            payload = build.get("payload") if isinstance(build.get("payload"), dict) else {}
            character = catalog.get_character(_clean(build.get("character_id"))) or {}
            self.character_detail.set_title(_clean(build.get("name")) or "Build")
            self.character_detail_body.setText(
                f"Character: {_clean(character.get('name')) or 'Unknown'}\n"
                f"Role: {_clean(payload.get('Role')) or 'Not set'}\n"
                f"Build id: {identity}"
            )

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------

    def _refresh_teams(self) -> None:
        current = self.team_combo.currentText()
        teams = self.roster_service.list_team_names()
        self.team_combo.blockSignals(True)
        self.team_combo.clear()
        self.team_combo.addItems(teams)
        if current:
            self.team_combo.setCurrentText(current)
        self.team_combo.blockSignals(False)
        self._refresh_team_detail()

    def _create_team(self) -> None:
        name = _clean(self.new_team_name.text())
        if not name:
            self.status.warning("Enter a team name first.")
            return
        canonical = self.roster_service.ensure_team_name(name)
        self.new_team_name.clear()
        self._refresh_teams()
        self.team_combo.setCurrentText(canonical)
        self.status.success(f"Team ready: {canonical}.")

    def _team_members(self, team_name: str) -> list[RosterMember]:
        wanted = _clean(team_name).casefold()
        if not wanted:
            return []
        return [
            member
            for member in self.members
            if wanted in {piece.strip().casefold() for piece in _clean(member.Team).split(",") if piece.strip()}
        ]

    def _refresh_team_detail(self, *_args) -> None:
        if not hasattr(self, "team_members_table"):
            return
        team = _clean(self.team_combo.currentText())
        members = self._team_members(team)
        self.team_members_table.setRowCount(0)
        for member in members:
            row = self.team_members_table.rowCount()
            self.team_members_table.insertRow(row)
            values = (
                member.PlayerName,
                member.CharacterName,
                member.EsoClass,
                member.PrimaryRole,
                member.Status,
                member.Team,
            )
            for column, value in enumerate(values):
                self.team_members_table.setItem(row, column, _set_readonly(QTableWidgetItem(_clean(value))))
        schedule = self.roster_service.get_team_schedule(team)
        self.team_days.setText(schedule.RaidDays if schedule else "")
        self.team_time.setText(schedule.RaidTime if schedule else "")
        self.team_timezone.setText(schedule.TimeZone if schedule else "")
        self.team_focus.setText(schedule.CurrentFocus if schedule else "")
        self.team_discord.setText(schedule.DiscordUrl if schedule else "")
        self.team_schedule_summary.setText(schedule.display_text if schedule else "No recurring schedule saved yet.")
        tanks = sum(1 for item in members if "tank" in _clean(item.PrimaryRole).casefold())
        healers = sum(1 for item in members if "heal" in _clean(item.PrimaryRole).casefold())
        damage = max(0, len(members) - tanks - healers)
        self.team_stats_label.setText(
            f"Members  {len(members)}\nTanks    {tanks}\nHealers  {healers}\nDamage   {damage}\n\n"
            f"Focus\n{_clean(schedule.CurrentFocus) if schedule else 'Not set'}"
        )

    def _save_team_schedule(self) -> None:
        team = _clean(self.team_combo.currentText())
        if not team:
            self.status.warning("Create or select a team first.")
            return
        self.roster_service.set_team_schedule(
            TeamSchedule(
                TeamName=team,
                RaidDays=_clean(self.team_days.text()),
                RaidTime=_clean(self.team_time.text()),
                TimeZone=_clean(self.team_timezone.text()),
                CurrentFocus=_clean(self.team_focus.text()),
                DiscordUrl=_clean(self.team_discord.text()),
            )
        )
        self._refresh_team_detail()
        self.status.success(f"Saved {team} schedule/defaults.")

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def _availability_combo(self, value: str) -> QComboBox:
        combo = QComboBox()
        for label, key in _AVAILABILITY_LABELS:
            combo.addItem(label, key)
        index = combo.findData(_clean(value).casefold())
        combo.setCurrentIndex(index if index >= 0 else 0)
        return combo

    def _refresh_availability(self) -> None:
        self.availability_table.setRowCount(0)
        for member in self.members:
            if member.Id is None:
                continue
            record = self.workspace_state.availability_for(member.Id)
            row = self.availability_table.rowCount()
            self.availability_table.insertRow(row)
            player = _set_readonly(QTableWidgetItem(member.PlayerName))
            player.setData(Qt.ItemDataRole.UserRole, int(member.Id))
            self.availability_table.setItem(row, 0, player)
            self.availability_table.setItem(row, 1, _set_readonly(QTableWidgetItem(member.CharacterName)))
            for offset, (_, field) in enumerate(_DAY_FIELDS, start=2):
                self.availability_table.setCellWidget(row, offset, self._availability_combo(getattr(record, field)))
            self.availability_table.setItem(row, 9, QTableWidgetItem(record.preferred_times))
            self.availability_table.setItem(row, 10, QTableWidgetItem(record.notes))

    def _save_availability(self) -> None:
        for row in range(self.availability_table.rowCount()):
            player = self.availability_table.item(row, 0)
            member_id = player.data(Qt.ItemDataRole.UserRole) if player is not None else None
            if member_id is None:
                continue
            values: dict[str, str] = {}
            for offset, (_, field) in enumerate(_DAY_FIELDS, start=2):
                widget = self.availability_table.cellWidget(row, offset)
                values[field] = _clean(widget.currentData() if isinstance(widget, QComboBox) else "unknown")
            preferred = self.availability_table.item(row, 9)
            notes = self.availability_table.item(row, 10)
            self.workspace_state.set_availability(
                MemberAvailability(
                    roster_member_id=int(member_id),
                    preferred_times=_clean(preferred.text() if preferred else ""),
                    notes=_clean(notes.text() if notes else ""),
                    **values,
                )
            )
        self._refresh_metrics()
        self.status.success("Saved roster availability.")

    # ------------------------------------------------------------------
    # Recruitment
    # ------------------------------------------------------------------

    def _refresh_recruitment(self) -> None:
        candidates = self.workspace_state.list_recruits()
        self.recruit_table.setRowCount(0)
        for candidate in candidates:
            row = self.recruit_table.rowCount()
            self.recruit_table.insertRow(row)
            values = (
                candidate.player_name,
                candidate.character_name,
                candidate.desired_role,
                candidate.eso_class,
                candidate.target_team,
                candidate.availability,
                candidate.status.title(),
                candidate.notes,
            )
            for column, value in enumerate(values):
                item = _set_readonly(QTableWidgetItem(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, candidate.id)
                self.recruit_table.setItem(row, column, item)

    def _selected_recruit_id(self) -> int | None:
        row = self.recruit_table.currentRow()
        if row < 0:
            return None
        item = self.recruit_table.item(row, 0)
        value = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return int(value) if value is not None else None

    def _load_selected_recruit(self) -> None:
        candidate_id = self._selected_recruit_id()
        if candidate_id is None:
            return
        candidate = next((item for item in self.workspace_state.list_recruits(include_archived=True) if item.id == candidate_id), None)
        if candidate is None:
            return
        self.recruit_id = candidate.id
        self.recruit_player.setText(candidate.player_name)
        self.recruit_character.setText(candidate.character_name)
        self.recruit_role.setCurrentText(candidate.desired_role)
        self.recruit_class.setCurrentText(candidate.eso_class)
        self.recruit_team.setCurrentText(candidate.target_team)
        self.recruit_availability.setText(candidate.availability)
        index = self.recruit_status.findData(candidate.status)
        self.recruit_status.setCurrentIndex(index if index >= 0 else 0)
        self.recruit_notes.setPlainText(candidate.notes)

    def _clear_recruit_editor(self) -> None:
        self.recruit_id = None
        self.recruit_player.clear()
        self.recruit_character.clear()
        self.recruit_role.setCurrentIndex(0)
        self.recruit_class.setCurrentIndex(0)
        self.recruit_team.setCurrentIndex(0 if self.recruit_team.count() else -1)
        self.recruit_availability.clear()
        self.recruit_status.setCurrentIndex(0)
        self.recruit_notes.clear()

    def _save_recruit(self) -> None:
        player = _clean(self.recruit_player.text())
        if not player:
            self.status.warning("Candidate player name is required.")
            return
        candidate_id = self.workspace_state.save_recruit(
            RecruitmentCandidate(
                id=self.recruit_id,
                player_name=player,
                character_name=_clean(self.recruit_character.text()),
                desired_role=_clean(self.recruit_role.currentText()),
                eso_class=_clean(self.recruit_class.currentText()),
                target_team=_clean(self.recruit_team.currentText()),
                availability=_clean(self.recruit_availability.text()),
                status=_clean(self.recruit_status.currentData()),
                notes=_clean(self.recruit_notes.toPlainText()),
            )
        )
        self.recruit_id = candidate_id
        self._refresh_recruitment()
        self._refresh_metrics()
        self.status.success(f"Saved recruitment candidate {player}.")

    def _archive_recruit(self) -> None:
        candidate_id = self.recruit_id or self._selected_recruit_id()
        if candidate_id is None:
            self.status.warning("Select a recruitment candidate first.")
            return
        candidate = next((item for item in self.workspace_state.list_recruits(include_archived=True) if item.id == candidate_id), None)
        if candidate is None:
            return
        self.workspace_state.archive(
            entity_type="recruit",
            entity_key=str(candidate_id),
            display_name=candidate.player_name,
            reason=f"Recruitment: {candidate.status}",
            related_team=candidate.target_team,
            payload=candidate.__dict__,
        )
        self.workspace_state.set_recruit_status(candidate_id, "archived")
        self._clear_recruit_editor()
        self._refresh_recruitment()
        self._refresh_archive()
        self._refresh_metrics()
        self.status.success(f"Archived recruitment candidate {candidate.player_name}.")

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    def _refresh_archive(self) -> None:
        records = self.workspace_state.list_archive()
        self.archive_table.setRowCount(0)
        for record in records:
            row = self.archive_table.rowCount()
            self.archive_table.insertRow(row)
            values = (
                record.display_name,
                record.entity_type.title(),
                record.reason,
                record.related_team,
                record.archived_at,
                record.entity_key,
            )
            for column, value in enumerate(values):
                self.archive_table.setItem(row, column, _set_readonly(QTableWidgetItem(_clean(value))))


__all__ = ["RaidRosterWorkspacePage"]
