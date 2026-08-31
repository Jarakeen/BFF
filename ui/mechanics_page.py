# ==================================================
# Black Feather Foundry
# ui/mechanics_page.py
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
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


class MechanicsPage(FoundryPage):
    """Boss Guide / Mechanics page for the Raid Engine."""

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
    def _context_field(title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Boss Guide",
            subtitle="Study the encounter. Document the details. Execute the plan.",
            department="Raid Engine • Mechanics",
        )
        self.set_header(self.header)

        self.trial_combo = QComboBox()
        self.trial_combo.addItem("Current Expedition")
        self.boss_combo = QComboBox()
        self.boss_combo.addItem("Current Objective")
        self.view_all_button = QPushButton("▤  View All Bosses")
        self.header.add_context_widget(self._context_field("TRIAL", self.trial_combo))
        self.header.add_context_widget(self._context_field("BOSS", self.boss_combo))
        self.header.add_context_widget(self.view_all_button)

        workspace = QWidget()
        root = QVBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        hero_row = QHBoxLayout()
        hero_row.setSpacing(8)

        boss_card = FoundryCard("Encounter", "♜").set_watermark("compass", 0.045)
        boss_card.setProperty("bossHeroCard", True)
        boss_body = QHBoxLayout()
        artwork = QLabel("BOSS ARTWORK")
        artwork.setMinimumSize(280, 170)
        artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        artwork.setProperty("bossArtworkPlaceholder", True)
        boss_body.addWidget(artwork, 2)

        identity = QVBoxLayout()
        self.boss_name = QLabel("No Encounter Selected")
        self.boss_name.setProperty("heroTitle", True)
        self.boss_subtitle = QLabel("Encounter details will appear here.")
        self.boss_subtitle.setProperty("heroSubtitle", True)
        self.boss_description = QLabel(
            "Boss description, encounter identity, and summary text will be populated when encounter data is connected."
        )
        self.boss_description.setWordWrap(True)
        identity.addWidget(self.boss_name)
        identity.addWidget(self.boss_subtitle)
        identity.addSpacing(6)
        identity.addWidget(self.boss_description)
        identity.addStretch(1)
        boss_body.addLayout(identity, 3)
        boss_card.addLayout(boss_body)
        hero_row.addWidget(boss_card, 5)

        facts = FoundryCard("Encounter Facts", "☷").set_watermark("compass", 0.045)
        for title in ("Role", "Location", "Recommended", "Enrage", "Hard Mode"):
            row = QHBoxLayout()
            row.addWidget(QLabel(title))
            row.addStretch(1)
            row.addWidget(QLabel("—"))
            facts.addLayout(row)
        hero_row.addWidget(facts, 2)

        quick = FoundryCard("Quick Notes", "✎").make_parchment().set_watermark("feather", 0.12)
        for note in (
            "• Portal control is critical.",
            "• Heavy damage in execute.",
            "• Call mechanics early.",
            "• Watch positioning.",
        ):
            quick.addWidget(QLabel(note))
        hero_row.addWidget(quick, 2)
        root.addLayout(hero_row)

        main_row = QHBoxLayout()
        main_row.setSpacing(8)
        center_column = QVBoxLayout()
        center_column.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._abilities_tab(), "ABILITIES")
        self.tabs.addTab(self._empty_tab("Threshold-specific mechanics and phase changes will appear here."), "THRESHOLDS")
        self.tabs.addTab(self._empty_tab("Strategy notes and recommended handling will appear here."), "STRATEGY")
        self.tabs.addTab(self._notes_tab(), "NOTES")
        self.tabs.addTab(self._empty_tab("Encounter timer events will appear here."), "TIMER")
        center_column.addWidget(self.tabs, 1)

        lower = QHBoxLayout()
        lower.setSpacing(8)
        strategy = FoundryCard("Strategy Overview", "⚑").set_watermark("compass", 0.04)
        strategy.addWidget(self._placeholder("Strategy overview placeholder.\n\nKEY FOCUS\nSurvive  •  Mechanics  •  Execute  •  Teamwork"))
        lower.addWidget(strategy, 3)

        assignment = FoundryCard("Assignment Summary", "♟").set_watermark("compass", 0.035)
        assignment.addWidget(self._placeholder("Main Tank\t—\nOff Tank\t—\nHealers\t—\nPortal Team\t—\nSpecial Assignments\t—"))
        lower.addWidget(assignment, 2)

        callouts = FoundryCard("Important Call Outs", "!").make_parchment().set_watermark("feather", 0.09)
        callouts.addWidget(self._placeholder("• Mechanic incoming!\n• Move / stack / spread.\n• Execute callout.\n• Custom raid-lead callouts."))
        lower.addWidget(callouts, 2)
        center_column.addLayout(lower)
        main_row.addLayout(center_column, 7)

        right = QVBoxLayout()
        right.setSpacing(8)
        timer = FoundryCard("Encounter Timer", "◷").set_watermark("compass", 0.045)
        timer_value = QLabel("00:00")
        timer_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timer_value.setProperty("timerValue", True)
        timer.addWidget(timer_value)
        timer_buttons = QHBoxLayout()
        timer_buttons.addWidget(QPushButton("Start"))
        timer_buttons.addWidget(QPushButton("Reset"))
        timer.addLayout(timer_buttons)
        right.addWidget(timer)

        notes = FoundryCard("My Notes", "✎").make_parchment().set_watermark("feather", 0.10)
        notes_box = QPlainTextEdit()
        notes_box.setPlaceholderText("Take notes here during the run…")
        notes_box.setMinimumHeight(180)
        notes.addWidget(notes_box)
        right.addWidget(notes, 1)

        reminders = FoundryCard("Key Reminders", "!").make_parchment().set_watermark("compass", 0.08)
        reminders.addWidget(self._placeholder("• Important threshold reminders\n• Positioning notes\n• Tank/healer warnings\n• Execute reminders"))
        right.addWidget(reminders)

        history = FoundryCard("Historical Notes", "⌁").make_parchment().set_watermark("feather", 0.08)
        history.addWidget(self._placeholder("• Pull history\n• Best attempt\n• Repeat failure points\n• Successful adjustments"))
        right.addWidget(history)

        main_row.addLayout(right, 2)
        root.addLayout(main_row, 1)
        self.add_workspace(workspace)

        self.status = FoundryStatusBar()
        self.status.info("Boss Guide ready. Encounter data cards are waiting for content.")
        self.set_status(self.status)

    def _abilities_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        abilities = FoundryCard("Abilities", "⚔")
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(("Ability", "Type", "Description", "Damage", "Target", "Notes"))
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(300)
        abilities.addWidget(table)
        layout.addWidget(abilities, 5)

        phases = FoundryCard("Phase & Thresholds", "⌛").set_watermark("compass", 0.055)
        phases.addWidget(self._placeholder("100%   Phase 1\n\n75%    Mechanic Threshold\n\n50%    Phase Change\n\n25%    Execute\n\n0%     Defeat"))
        layout.addWidget(phases, 2)
        return tab

    def _notes_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        edit = QPlainTextEdit()
        edit.setProperty("parchment", True)
        edit.setPlaceholderText("Encounter notes…")
        layout.addWidget(edit)
        return tab

    def _empty_tab(self, text: str) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._placeholder(text, centered=True), 1)
        return tab

    def refresh_context(self):
        current = self.expedition.expedition
        trial = current.Expedition or "No Active Expedition"
        difficulty = current.Difficulty or ""
        boss = current.Objective or "No Encounter Selected"
        trial_text = f"{trial}{f' ({difficulty})' if difficulty else ''}"
        self.trial_combo.setItemText(0, trial_text)
        self.boss_combo.setItemText(0, boss)
        self.boss_name.setText(boss)
        self.boss_subtitle.setText(trial_text)
