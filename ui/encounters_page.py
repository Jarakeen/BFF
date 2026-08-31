# ==================================================
# Black Feather Foundry
#
# File:
# ui/encounters_page.py
#
# Purpose:
# Raid Engine encounter planning workspace.
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from services.expedition_service import ExpeditionService
from ui.components.encounter_board import EncounterBoard
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


class EncountersPage(FoundryPage):
    """Encounter positioning, timelines, mechanics, and assignments."""

    def __init__(self, expedition: ExpeditionService, parent=None):
        super().__init__(parent)
        self.expedition = expedition
        self._build_ui()
        self.refresh_context()

    @staticmethod
    def _placeholder(text: str, *, centered: bool = False) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setProperty("muted", True)
        if centered:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    @staticmethod
    def _context_box(title: str, value: QLabel) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        caption = QLabel(title)
        caption.setProperty("sidebarHeading", True)
        layout.addWidget(caption)
        layout.addWidget(value)
        return box

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Encounters",
            subtitle="Position the team. Track the phase. Keep the plan legible.",
            department="Raid Engine • Encounters",
            icon="trial",
        )
        self.set_header(self.header)

        self.active_trial = QLabel("No Active Expedition")
        self.group_size = QLabel("— / —")
        directive = QLabel("Tonight's Directive\nExecution matters. Stay calm. Stay together.")
        directive.setWordWrap(True)
        directive.setProperty("parchment", True)

        self.header.add_context_widget(self._context_box("ACTIVE TRIAL", self.active_trial))
        self.header.add_context_widget(self._context_box("GROUP SIZE", self.group_size))
        self.header.add_context_widget(directive)

        workspace = QWidget()
        root = QVBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.section_tabs = QTabWidget()
        self.section_tabs.addTab(self._overview_tab(), "OVERVIEW")
        self.section_tabs.addTab(self._assignments_tab(), "ASSIGNMENTS")
        self.section_tabs.addTab(self._mechanics_tab(), "MECHANICS")
        self.section_tabs.addTab(self._empty_section("Loot, rewards, and achievement targets will appear here."), "LOOT & REWARDS")
        self.section_tabs.addTab(self._empty_section("Encounter notes will appear here."), "NOTES")
        self.section_tabs.setCurrentIndex(1)
        root.addWidget(self.section_tabs, 1)

        self.add_workspace(workspace)

        self.status = FoundryStatusBar()
        self.status.info("Encounter workspace ready. Mechanics includes the interactive positioning board.")
        self.set_status(self.status)

    def _overview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        summary = FoundryCard("Encounter Overview", "trial").set_watermark("compass", 0.04)
        summary.addWidget(self._placeholder("Trial summary, selected boss, progression state, and encounter notes."))
        layout.addWidget(summary, 2)

        progression = FoundryCard("Progression", "progression")
        progression.addWidget(self._placeholder("Best pull\nPull count\nCurrent phase\nRecent result"))
        layout.addWidget(progression, 1)

        raid_notes = FoundryCard("Raid Lead Notes", "feather").make_parchment().set_watermark("feather", 0.10)
        raid_notes.addWidget(self._placeholder("High-level direction for tonight's work."))
        layout.addWidget(raid_notes, 1)
        return tab

    def _assignments_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        upper = QHBoxLayout()
        upper.setSpacing(8)

        left = QVBoxLayout()
        left.setSpacing(8)

        controls = FoundryCard("Select Boss", "boss")
        boss_row = QHBoxLayout()
        self.boss_combo = QComboBox()
        self.boss_combo.addItem("Current Objective")
        boss_row.addWidget(self.boss_combo, 1)
        boss_row.addWidget(QPushButton("‹"))
        boss_row.addWidget(QPushButton("›"))
        controls.addLayout(boss_row)

        phase_row = QHBoxLayout()
        phase_list = QListWidget()
        phase_list.addItems(("Phase 1   0:00 – 2:10", "Phase 2   2:10 – 4:20", "Phase 3   4:20 – 6:10", "Execute   6:10+"))
        phase_list.setMaximumWidth(180)
        phase_row.addWidget(phase_list)

        self.positioning_card = FoundryCard("Positioning", "treasure-map").set_watermark("compass", 0.035)
        self.positioning_preview = QLabel()
        self.positioning_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.positioning_preview.setMinimumHeight(300)
        self.positioning_preview.setProperty("positioningMap", True)
        self.positioning_preview.setText(
            "No positioning capture yet.\n\n"
            "Build the encounter on the Mechanics tab, then use Capture Positioning."
        )
        self.positioning_card.addWidget(self.positioning_preview)
        open_board = QPushButton("Open Mechanics Map")
        open_board.clicked.connect(lambda: self.section_tabs.setCurrentIndex(2))
        self.positioning_card.set_header_action(open_board)
        phase_row.addWidget(self.positioning_card, 1)
        controls.addLayout(phase_row)
        left.addWidget(controls, 3)

        assignments = FoundryCard("Player Assignments (Phase 1)", "assignment")
        filter_row = QHBoxLayout()
        for text in ("All Players", "Tanks", "Healers", "DPS", "Special"):
            button = QPushButton(text)
            button.setCheckable(True)
            filter_row.addWidget(button)
        search = QLineEdit()
        search.setPlaceholderText("Search player or assignment…")
        filter_row.addWidget(search, 1)
        assignments.addLayout(filter_row)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(("Player", "Role", "Primary Assignment", "Secondary Assignment(s)", "Notes"))
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setMinimumHeight(230)
        assignments.addWidget(table)
        left.addWidget(assignments, 2)
        upper.addLayout(left, 6)

        middle = QVBoxLayout()
        middle.setSpacing(8)

        timeline = FoundryCard("Phase Timeline Overview", "stopwatch")
        timeline.addWidget(self._placeholder(
            "0:00   Pull\n"
            "0:20   Portal Spawn\n"
            "0:45   Heavy Attack\n"
            "1:10   Orbs\n"
            "1:30   Portal Adds\n"
            "1:55   Chains\n"
            "2:10   Phase Transition\n"
            "4:20   Phase 3 Begins\n"
            "6:10   Execute"
        ))
        middle.addWidget(timeline, 3)

        event = FoundryCard("Event Details", "mechanics")
        event.addWidget(self._placeholder("Selected event details, assignment ownership, and handling notes will appear here."))
        event.addWidget(QPushButton("Add Custom Event"))
        middle.addWidget(event, 2)
        upper.addLayout(middle, 3)

        right = QVBoxLayout()
        right.setSpacing(8)

        mechanics = FoundryCard("Mechanics Reference", "open-book")
        mechanic_search = QLineEdit()
        mechanic_search.setPlaceholderText("Search mechanics…")
        mechanics.addWidget(mechanic_search)
        mechanic_list = QListWidget()
        mechanic_list.addItems(("Portal Spawn", "Heavy Attack", "Orbs", "Portal Adds", "Chains", "Execute"))
        mechanics.addWidget(mechanic_list)
        right.addWidget(mechanics, 2)

        detail = FoundryCard("Mechanic Details", "crossed-swords")
        detail.addWidget(self._placeholder(
            "Select a mechanic to show type, phase, priority, failure risk, handling notes, and responsible roles."
        ))
        right.addWidget(detail, 3)

        notes = FoundryCard("Quick Notes", "feather").make_parchment().set_watermark("feather", 0.12)
        notes.addWidget(self._placeholder("• Callout conventions\n• Phase reminders\n• Adjustment notes"))
        notes.set_header_action(QPushButton("Add Note"))
        right.addWidget(notes, 2)

        upper.addLayout(right, 3)
        root.addLayout(upper, 1)
        return tab

    def _mechanics_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        intro = FoundryCard("Mechanics Map", "crossed-swords").set_watermark("compass", 0.025)
        intro.addWidget(QLabel(
            "Build a clean tactical picture of the fight. Drag the boss, role markers, portals, AOEs, and stack points into place. "
            "Use 2 Bosses for paired encounters such as twins."
        ))
        root.addWidget(intro)

        board_card = FoundryCard("Interactive Positioning Board", "treasure-map")
        self.encounter_board = EncounterBoard()
        self.encounter_board.snapshotSaved.connect(self._positioning_snapshot_saved)
        board_card.addWidget(self.encounter_board)
        root.addWidget(board_card, 1)

        self._load_positioning_preview(self.encounter_board.snapshot_path)
        return tab

    def _positioning_snapshot_saved(self, path: str):
        self._load_positioning_preview(Path(path))
        if hasattr(self, "status"):
            self.status.success("Positioning captured. Assignments preview updated.")

    def _load_positioning_preview(self, path: Path):
        if not hasattr(self, "positioning_preview"):
            return
        if not path.exists():
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(
            760,
            360,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.positioning_preview.setPixmap(scaled)
        self.positioning_preview.setToolTip("Latest captured positioning from the Mechanics tactical board")

    def _empty_section(self, text: str) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        card = FoundryCard("Workspace", "notebook").set_watermark("compass", 0.035)
        card.addWidget(self._placeholder(text, centered=True))
        layout.addWidget(card, 1)
        return tab

    def refresh_context(self):
        current = self.expedition.expedition
        trial = current.Expedition or "No Active Expedition"
        difficulty = current.Difficulty or ""
        boss = current.Objective or "No Encounter Selected"

        self.active_trial.setText(f"{trial}{f' ({difficulty})' if difficulty else ''}")
        self.group_size.setText("— / —")
        if hasattr(self, "boss_combo"):
            self.boss_combo.setItemText(0, boss)
