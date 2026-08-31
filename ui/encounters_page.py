# ==================================================
# Black Feather Foundry
#
# File:
# ui/encounters_page.py
#
# Purpose:
# Raid Engine encounter planning workspace.
#
# Mirrors the positioning / assignments wireframe while
# leaving unwired data regions as explicit placeholders.
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
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
        root.setSpacing(12)

        # Page-level tabs, matching the wireframe language.
        self.section_tabs = QTabWidget()
        self.section_tabs.addTab(self._overview_tab(), "OVERVIEW")
        self.section_tabs.addTab(self._assignments_tab(), "ASSIGNMENTS")
        self.section_tabs.addTab(self._empty_section("Mechanics-specific encounter planning will appear here."), "MECHANICS")
        self.section_tabs.addTab(self._empty_section("Loot, rewards, and achievement targets will appear here."), "LOOT & REWARDS")
        self.section_tabs.addTab(self._empty_section("Encounter notes will appear here."), "NOTES")
        self.section_tabs.setCurrentIndex(1)
        root.addWidget(self.section_tabs, 1)

        self.add_workspace(workspace)

        self.status = FoundryStatusBar()
        self.status.info("Encounter workspace ready. Placeholder cards can be filled as encounter data is wired.")
        self.set_status(self.status)

    def _overview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        summary = FoundryCard("Encounter Overview")
        summary.addWidget(self._placeholder("Trial summary, selected boss, progression state, and encounter notes."))
        layout.addWidget(summary, 2)

        progression = FoundryCard("Progression")
        progression.addWidget(self._placeholder("Best pull\nPull count\nCurrent phase\nRecent result"))
        layout.addWidget(progression, 1)

        raid_notes = FoundryCard("Raid Lead Notes")
        raid_notes.setProperty("parchment", True)
        raid_notes.addWidget(self._placeholder("High-level direction for tonight's work."))
        layout.addWidget(raid_notes, 1)
        return tab

    def _assignments_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        upper = QHBoxLayout()
        upper.setSpacing(12)

        # Left: boss / phase selector + positioning map.
        left = QVBoxLayout()
        left.setSpacing(12)

        controls = FoundryCard("Select Boss")
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

        positioning = FoundryCard("Positioning")
        map_placeholder = QLabel(
            "POSITIONING MAP\n\n"
            "          MT        BOSS        OT\n\n"
            "        H1       DPS STACK       H2\n\n"
            "      PORTAL 1   PORTAL 3   PORTAL 2\n\n"
            "Safe zones, movement arrows, and role markers will render here."
        )
        map_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        map_placeholder.setMinimumHeight(300)
        map_placeholder.setProperty("positioningMap", True)
        positioning.addWidget(map_placeholder)
        phase_row.addWidget(positioning, 1)
        controls.addLayout(phase_row)
        left.addWidget(controls, 3)

        assignments = FoundryCard("Player Assignments (Phase 1)")
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

        # Middle: phase timeline + event details.
        middle = QVBoxLayout()
        middle.setSpacing(12)

        timeline = FoundryCard("Phase Timeline Overview")
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

        event = FoundryCard("Event Details")
        event.addWidget(self._placeholder("Selected event details, assignment ownership, and handling notes will appear here."))
        event.addWidget(QPushButton("＋  Add Custom Event"))
        middle.addWidget(event, 2)
        upper.addLayout(middle, 3)

        # Right: mechanic reference + details + quick notes.
        right = QVBoxLayout()
        right.setSpacing(12)

        mechanics = FoundryCard("Mechanics Reference")
        mechanic_search = QLineEdit()
        mechanic_search.setPlaceholderText("Search mechanics…")
        mechanics.addWidget(mechanic_search)
        mechanic_list = QListWidget()
        mechanic_list.addItems(("Portal Spawn", "Heavy Attack", "Orbs", "Portal Adds", "Chains", "Execute"))
        mechanics.addWidget(mechanic_list)
        right.addWidget(mechanics, 2)

        detail = FoundryCard("Mechanic Details")
        detail.addWidget(self._placeholder(
            "Select a mechanic to show type, phase, priority, failure risk, handling notes, and responsible roles."
        ))
        right.addWidget(detail, 3)

        notes = FoundryCard("Quick Notes")
        notes.setProperty("parchment", True)
        notes.addWidget(self._placeholder("• Callout conventions\n• Phase reminders\n• Adjustment notes"))
        notes.set_header_action(QPushButton("＋ Add Note"))
        right.addWidget(notes, 2)

        upper.addLayout(right, 3)
        root.addLayout(upper, 1)
        return tab

    def _empty_section(self, text: str) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        card = FoundryCard("Workspace")
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
