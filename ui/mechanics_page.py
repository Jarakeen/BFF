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

from services.accessibility_preferences import (
    AccessibilityPreferences,
    COLOR_VISION_FRIENDLY,
    COLOR_VISION_STANDARD,
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
        self.accessibility_preferences = AccessibilityPreferences()
        self._color_vision_mode = self.accessibility_preferences.color_vision_mode()
        self._status_badges: dict[str, QLabel] = {}
        self._build_ui()
        self.refresh_context()
        self._apply_color_vision_mode(self._color_vision_mode)

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
            title="Mechanics",
            subtitle="Study the encounter. Document the details. Execute the plan.",
            department="Raid Engine • Mechanics",
        )
        self.set_header(self.header)

        self.trial_combo = QComboBox()
        self.trial_combo.addItem("Current Expedition")
        self.boss_combo = QComboBox()
        self.boss_combo.addItem("Current Objective")
        self.color_vision_combo = QComboBox()
        self.color_vision_combo.addItem("Standard", COLOR_VISION_STANDARD)
        self.color_vision_combo.addItem("Colorblind Friendly", COLOR_VISION_FRIENDLY)
        initial_mode_index = self.color_vision_combo.findData(self._color_vision_mode)
        self.color_vision_combo.setCurrentIndex(initial_mode_index if initial_mode_index >= 0 else 0)
        self.color_vision_combo.currentIndexChanged.connect(self._color_vision_changed)

        self.view_all_button = QPushButton("▤  View All Bosses")
        self.header.add_context_widget(self._context_field("TRIAL", self.trial_combo))
        self.header.add_context_widget(self._context_field("BOSS", self.boss_combo))
        self.header.add_context_widget(self._context_field("COLOR VISION", self.color_vision_combo))
        self.header.add_context_widget(self.view_all_button)

        workspace = QWidget()
        workspace.setObjectName("mechanicsWorkspace")
        self.mechanics_workspace = workspace
        root = QVBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        root.addWidget(self._accessibility_key())

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
        self.tabs.addTab(self._mechanics_tab(), "MECHANICS")
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
        self.status.info("Mechanics ready. Encounter data cards are waiting for content.")
        self.set_status(self.status)

    def _accessibility_key(self) -> QWidget:
        card = FoundryCard("Status Key", "◈")
        row = QHBoxLayout()
        row.setSpacing(10)
        for role in ("success", "danger", "warning", "neutral"):
            badge = QLabel()
            badge.setProperty("mechanicsStatus", role)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setMinimumHeight(30)
            badge.setMinimumWidth(150)
            self._status_badges[role] = badge
            row.addWidget(badge)
        row.addStretch(1)
        card.addLayout(row)
        self.color_vision_note = QLabel()
        self.color_vision_note.setWordWrap(True)
        self.color_vision_note.setProperty("muted", True)
        card.addWidget(self.color_vision_note)
        return card

    def _mechanics_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        card = FoundryCard("Encounter Mechanics", "☠")
        self.mechanics_table = QTableWidget(0, 5)
        self.mechanics_table.setHorizontalHeaderLabels(("Mechanic", "Type", "You", "Group", "Notes"))
        self.mechanics_table.setAlternatingRowColors(True)
        self.mechanics_table.verticalHeader().setVisible(False)
        self.mechanics_table.setMinimumHeight(300)
        self.mechanics_table.setProperty("mechanicsTable", True)
        card.addWidget(self.mechanics_table)
        card.addWidget(
            self._placeholder(
                "Mechanic status uses icon + shape + text. Color is supplemental, so the table remains readable in grayscale."
            )
        )
        layout.addWidget(card)
        return tab

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

    def _color_vision_changed(self, _index: int) -> None:
        mode = str(self.color_vision_combo.currentData() or COLOR_VISION_STANDARD)
        self._color_vision_mode = self.accessibility_preferences.set_color_vision_mode(mode)
        self._apply_color_vision_mode(self._color_vision_mode)
        if hasattr(self, "status"):
            label = "Colorblind Friendly" if self._color_vision_mode == COLOR_VISION_FRIENDLY else "Standard"
            self.status.success(f"Mechanics color vision mode: {label}.")

    def _set_status_badge_text(self, mode: str) -> None:
        if mode == COLOR_VISION_FRIENDLY:
            labels = {
                "success": "◇  ✓  SAFE / SUCCESS",
                "danger": "⬡  ✕  FAILED / DANGER",
                "warning": "○  !  ATTENTION / WARNING",
                "neutral": "□  —  NOT APPLICABLE",
            }
            note = (
                "Colorblind Friendly mode uses blue, orange, yellow, purple, and cyan accents with distinct shapes and icons. "
                "No mechanic state should rely on color alone."
            )
        else:
            labels = {
                "success": "✓  SAFE / SUCCESS",
                "danger": "✕  FAILED / DANGER",
                "warning": "!  ATTENTION / WARNING",
                "neutral": "○  NOT APPLICABLE",
            }
            note = (
                "Standard mode keeps the familiar red/green status colors while retaining icons and text so status is still readable without color."
            )
        for role, text in labels.items():
            self._status_badges[role].setText(text)
        self.color_vision_note.setText(note)

    def _apply_color_vision_mode(self, mode: str) -> None:
        mode = mode if mode in {COLOR_VISION_STANDARD, COLOR_VISION_FRIENDLY} else COLOR_VISION_STANDARD
        self._color_vision_mode = mode
        self._set_status_badge_text(mode)

        if mode == COLOR_VISION_FRIENDLY:
            success = "#3C9DFF"
            danger = "#E97917"
            warning = "#F2C94C"
            neutral = "#A7A7A7"
            mode_accent = "#2BBBCB"
        else:
            success = "#6FAE45"
            danger = "#D84A3A"
            warning = "#E0A61A"
            neutral = "#A7A7A7"
            mode_accent = "#C8A46A"

        self.mechanics_workspace.setProperty("colorVisionMode", mode)
        self.mechanics_workspace.setStyleSheet(
            f"""
            QWidget#mechanicsWorkspace {{
                background-color: #101315;
                color: #E5E1D8;
            }}
            QWidget#mechanicsWorkspace QTableWidget {{
                background-color: #111416;
                alternate-background-color: #171B1E;
                gridline-color: #4B4A46;
                color: #E5E1D8;
                selection-background-color: #30373B;
                selection-color: #FFFFFF;
            }}
            QWidget#mechanicsWorkspace QHeaderView::section {{
                background-color: #171A1C;
                color: #D8D2C6;
                border: 0px;
                border-right: 1px solid #4B4A46;
                border-bottom: 1px solid #5B554C;
                padding: 6px;
            }}
            QWidget#mechanicsWorkspace QTabWidget::pane {{
                border: 1px solid #5B554C;
                background-color: #111416;
            }}
            QWidget#mechanicsWorkspace QTabBar::tab:selected {{
                border-bottom: 2px solid {mode_accent};
            }}
            QLabel[mechanicsStatus="success"] {{
                color: {success};
                border: 1px solid {success};
                border-radius: 12px;
                padding: 4px 9px;
                font-weight: 700;
            }}
            QLabel[mechanicsStatus="danger"] {{
                color: {danger};
                border: 1px solid {danger};
                border-radius: 3px;
                padding: 4px 9px;
                font-weight: 700;
            }}
            QLabel[mechanicsStatus="warning"] {{
                color: {warning};
                border: 1px dashed {warning};
                border-radius: 12px;
                padding: 4px 9px;
                font-weight: 700;
            }}
            QLabel[mechanicsStatus="neutral"] {{
                color: {neutral};
                border: 1px solid #666666;
                padding: 4px 9px;
                font-weight: 700;
            }}
            """
        )

    def _reload_color_vision_preference(self) -> None:
        mode = self.accessibility_preferences.color_vision_mode()
        self.color_vision_combo.blockSignals(True)
        index = self.color_vision_combo.findData(mode)
        self.color_vision_combo.setCurrentIndex(index if index >= 0 else 0)
        self.color_vision_combo.blockSignals(False)
        self._apply_color_vision_mode(mode)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._reload_color_vision_preference()

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