# ==================================================
# Black Feather Foundry
# ui/mechanics_page.py
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.encounter_boss_guide import EncounterBossGuideService
from services.expedition_service import ExpeditionService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.components.foundry_timeline import FoundryTimeline
from ui.foundry_page import FoundryPage
from ui.mechanics_timeline import phase_event, unresolved_event


class MechanicsPage(FoundryPage):
    """Boss Guide / Mechanics page for the Raid Engine."""

    def __init__(
        self,
        expedition: ExpeditionService,
        guide_service: EncounterBossGuideService | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.expedition = expedition
        self.guide_service = guide_service
        self._guide_summaries = ()
        self._build_ui()
        self._connect_guide_signals()
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

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Boss Guide",
            subtitle="Study the encounter. Document the details. Execute the plan.",
            department="Raid Engine • Mechanics",
        )
        self.set_header(self.header)

        self.trial_combo = QComboBox()
        self.boss_combo = QComboBox()
        self.view_all_button = QPushButton("▤  View All Bosses")
        self.header.add_context_widget(self._context_field("CONTENT", self.trial_combo))
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
            "Select a persisted encounter to inspect source-backed boss-guide data."
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
        self.fact_values: dict[str, QLabel] = {}
        for title in (
            "Location",
            "Normal Health",
            "Veteran Health",
            "Hard Mode Health",
            "Source Revision",
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(title))
            row.addStretch(1)
            value = QLabel("—")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.fact_values[title] = value
            row.addWidget(value)
            facts.addLayout(row)
        hero_row.addWidget(facts, 2)

        quick = FoundryCard("Coverage Notes", "✎").make_parchment().set_watermark("feather", 0.12)
        self.coverage_notes: list[QLabel] = []
        for _ in range(4):
            label = QLabel("• —")
            label.setWordWrap(True)
            self.coverage_notes.append(label)
            quick.addWidget(label)
        hero_row.addWidget(quick, 2)
        root.addLayout(hero_row)

        main_row = QHBoxLayout()
        main_row.setSpacing(8)
        center_column = QVBoxLayout()
        center_column.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._abilities_tab(), "ABILITIES")
        self.tabs.addTab(self._thresholds_tab(), "THRESHOLDS")
        self.tabs.addTab(
            self._empty_tab("Reviewed strategy notes and recommended handling are not wired yet."),
            "STRATEGY",
        )
        self.tabs.addTab(self._notes_tab(), "NOTES")
        self.tabs.addTab(self._timer_tab(), "TIMER")
        center_column.addWidget(self.tabs, 1)

        lower = QHBoxLayout()
        lower.setSpacing(8)
        strategy = FoundryCard("Strategy Overview", "⚑").set_watermark("compass", 0.04)
        strategy.addWidget(
            self._placeholder(
                "Strategy remains separate from structural boss data. Reviewed handling will appear here when canonical strategy evidence is available."
            )
        )
        lower.addWidget(strategy, 3)

        assignment = FoundryCard("Assignment Summary", "♟").set_watermark("compass", 0.035)
        assignment.addWidget(
            self._placeholder(
                "Provider and roster assignments remain separate from the boss-guide reader."
            )
        )
        lower.addWidget(assignment, 2)

        callouts = FoundryCard("Important Call Outs", "!").make_parchment().set_watermark("feather", 0.09)
        callouts.addWidget(
            self._placeholder(
                "Reviewed callouts will appear here when encounter handling data is explicitly available."
            )
        )
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
        reminders.addWidget(
            self._placeholder(
                "Player reminders stay unresolved until reviewed encounter handling is available."
            )
        )
        right.addWidget(reminders)

        history = FoundryCard("Historical Notes", "⌁").make_parchment().set_watermark("feather", 0.08)
        history.addWidget(
            self._placeholder("Pull history and progression notes remain user-entered data.")
        )
        right.addWidget(history)

        main_row.addLayout(right, 2)
        root.addLayout(main_row, 1)
        self.add_workspace(workspace)

        self.status = FoundryStatusBar()
        self.status.info("Boss Guide ready. Select a persisted encounter.")
        self.set_status(self.status)

    def _abilities_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        abilities = FoundryCard("Named Abilities", "⚔")
        self.abilities_table = QTableWidget(0, 6)
        self.abilities_table.setHorizontalHeaderLabels(
            ("Ability", "Interrupt", "Description", "Source", "Revision", "Notes")
        )
        self.abilities_table.setAlternatingRowColors(True)
        self.abilities_table.verticalHeader().setVisible(False)
        self.abilities_table.setMinimumHeight(300)
        self.abilities_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.abilities_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        abilities.addWidget(self.abilities_table)
        layout.addWidget(abilities, 5)

        phases = FoundryCard("Encounter Timeline", "⌛").set_watermark("compass", 0.055)
        self.timeline = FoundryTimeline([unresolved_event()])
        phases.addWidget(self.timeline)
        layout.addWidget(phases, 2)
        return tab

    def _thresholds_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        self.phase_table = QTableWidget(0, 3)
        self.phase_table.setHorizontalHeaderLabels(("Threshold", "Phase", "Description"))
        self.phase_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.phase_table.verticalHeader().setVisible(False)
        header = self.phase_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.phase_table)
        return tab

    def _timer_tab(self) -> QWidget:
        return self._empty_tab(
            "Exact timestamps and repeating cadence will appear here only when source-backed timing evidence is available."
        )

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

    def _connect_guide_signals(self) -> None:
        self.trial_combo.currentIndexChanged.connect(self._content_changed)
        self.boss_combo.currentIndexChanged.connect(self._boss_changed)
        self.view_all_button.clicked.connect(self._show_all_bosses)

    def _load_guide_index(self) -> None:
        if self.guide_service is None:
            return
        self._guide_summaries = self.guide_service.encounter_summaries()
        current_content = self.trial_combo.currentData()

        self.trial_combo.blockSignals(True)
        self.trial_combo.clear()
        self.trial_combo.addItem("All Content", None)
        seen: set[str] = set()
        for row in self._guide_summaries:
            if row.content_id in seen:
                continue
            seen.add(row.content_id)
            self.trial_combo.addItem(row.content_name or row.content_id, row.content_id)
        self.trial_combo.blockSignals(False)

        if current_content is not None:
            index = self.trial_combo.findData(current_content)
            if index >= 0:
                self.trial_combo.setCurrentIndex(index)
        self._populate_boss_combo()

    def _populate_boss_combo(self, preferred_encounter_id: str | None = None) -> None:
        if self.guide_service is None:
            return
        content_id = self.trial_combo.currentData()
        rows = [
            row
            for row in self._guide_summaries
            if content_id is None or row.content_id == content_id
        ]
        current = preferred_encounter_id or self.boss_combo.currentData()

        self.boss_combo.blockSignals(True)
        self.boss_combo.clear()
        for row in rows:
            self.boss_combo.addItem(row.name, row.encounter_id)
        self.boss_combo.blockSignals(False)

        if current is not None:
            index = self.boss_combo.findData(current)
            if index >= 0:
                self.boss_combo.setCurrentIndex(index)
        if self.boss_combo.count() > 0 and self.boss_combo.currentIndex() < 0:
            self.boss_combo.setCurrentIndex(0)
        self._boss_changed(self.boss_combo.currentIndex())

    def _content_changed(self, _index: int) -> None:
        self._populate_boss_combo()

    def _boss_changed(self, _index: int) -> None:
        if self.guide_service is None:
            return
        encounter_id = self.boss_combo.currentData()
        if not encounter_id:
            self._clear_guide()
            return
        self._render_guide(self.guide_service.get(str(encounter_id)))

    def _show_all_bosses(self) -> None:
        if self.guide_service is None:
            return
        self.trial_combo.setCurrentIndex(0)

    def _render_guide(self, guide) -> None:
        self.boss_name.setText(guide.name)
        self.boss_subtitle.setText(guide.content_name or guide.content_id)
        self.boss_description.setText(
            guide.summary
            or "Source-backed structural encounter record. Narrative summary is unresolved."
        )

        health = dict(guide.health)
        self.fact_values["Location"].setText(guide.location or "Unresolved")
        self.fact_values["Normal Health"].setText(health.get("normal") or "Unresolved")
        self.fact_values["Veteran Health"].setText(health.get("veteran") or "Unresolved")
        self.fact_values["Hard Mode Health"].setText(health.get("hardmode") or "Unresolved")
        self.fact_values["Source Revision"].setText(guide.source_revision_id or "Unresolved")

        phase_note = (
            f"{len(guide.phases)} explicit phase record(s)."
            if guide.phases
            else "No explicit phase/timing record is persisted yet."
        )
        health_note = (
            f"Known health: {', '.join(key for key, _ in guide.health)}."
            if guide.health
            else "Health row persisted; numeric values unresolved."
        )
        notes = (
            f"{len(guide.abilities)} named ability record(s).",
            health_note,
            phase_note,
            "Strategy, assignments, and exact timing remain separate evidence domains.",
        )
        for label, text in zip(self.coverage_notes, notes):
            label.setText(f"• {text}")

        self.abilities_table.setRowCount(len(guide.abilities))
        for row_index, ability in enumerate(guide.abilities):
            interrupt = (
                "Yes"
                if ability.interruptible is True
                else "No"
                if ability.interruptible is False
                else "Unresolved"
            )
            values = (
                ability.name,
                interrupt,
                ability.description or "—",
                ability.source_section or "—",
                ability.source_revision_id or "—",
                ability.interrupt_note or "—",
            )
            for column, value in enumerate(values):
                self.abilities_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.abilities_table.resizeRowsToContents()

        self.phase_table.setRowCount(len(guide.phases))
        for row_index, phase in enumerate(guide.phases):
            values = (phase.threshold or "Unresolved", phase.label or "Phase", phase.description or "—")
            for column, value in enumerate(values):
                self.phase_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.phase_table.resizeRowsToContents()

        if guide.phases:
            self.timeline.set_events(
                [
                    phase_event(
                        marker=phase.threshold or "?",
                        label=phase.label or "Phase",
                        detail=phase.description or "Explicit persisted phase record.",
                    )
                    for phase in guide.phases
                ]
            )
        else:
            self.timeline.set_events([unresolved_event()])

        self.status.success(
            f"Loaded {guide.name}: {len(guide.abilities)} named ability record(s), "
            f"{len(guide.phases)} explicit phase record(s)."
        )

    def _clear_guide(self) -> None:
        self.boss_name.setText("No Encounter Selected")
        self.boss_subtitle.setText("No persisted encounter selected")
        self.boss_description.setText("Select an encounter to inspect source-backed data.")
        for value in self.fact_values.values():
            value.setText("—")
        for label in self.coverage_notes:
            label.setText("• —")
        self.abilities_table.setRowCount(0)
        self.phase_table.setRowCount(0)
        self.timeline.set_events([unresolved_event(label="No encounter selected")])

    def refresh_context(self) -> None:
        current = self.expedition.expedition
        if self.guide_service is None:
            trial = current.Expedition or "No Active Expedition"
            difficulty = current.Difficulty or ""
            boss = current.Objective or "No Encounter Selected"
            trial_text = f"{trial}{f' ({difficulty})' if difficulty else ''}"
            self.trial_combo.clear()
            self.trial_combo.addItem(trial_text)
            self.boss_combo.clear()
            self.boss_combo.addItem(boss)
            self.boss_name.setText(boss)
            self.boss_subtitle.setText(trial_text)
            return

        self._load_guide_index()

        objective = str(current.Objective or "").strip().casefold()
        if objective:
            match = next(
                (row for row in self._guide_summaries if row.name.casefold() == objective),
                None,
            )
            if match is not None:
                content_index = self.trial_combo.findData(match.content_id)
                if content_index >= 0:
                    self.trial_combo.setCurrentIndex(content_index)
                self._populate_boss_combo(match.encounter_id)
                return

        if self.boss_combo.count() > 0:
            self._boss_changed(self.boss_combo.currentIndex())
