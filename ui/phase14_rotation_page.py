from __future__ import annotations

"""Phase 14 Rotation Builder.

This page deliberately owns its widgets and signals. It uses the established rotation
services directly and does not import, instantiate, decorate, or monkey-patch the
legacy Rotation Dashboard.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.build_context_variant_service import resolve_build_context
from services.build_rotation_artifact_service import (
    BuildRotationArtifactService,
    jsonable,
    resolve_canonical_build_id,
)
from services.build_service import BuildService
from services.encounter_boss_guide import EncounterBossGuideService
from services.phase14_rotation_runtime_service import Phase14RotationRuntimeService
from services.rotation_encounter_demand_policy_registry_service import (
    RotationEncounterDemandPolicyRegistryService,
)
from services.rotation_pdf_export_service import (
    RotationPdfExportContext,
    RotationPdfExportService,
)
from services.rotation_sustain_service import RotationSustainService
from services.rotation_timeline_projection_service import RotationTimelineProjectionService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.components.rotation_timeline_widget import RotationTimelineWidget
from ui.foundry_page import FoundryPage
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport
from ui.rotation_timeline_dashboard_support import RotationTimelineIconResolver
from ui.ux_icons import icon_label, set_button_icon


_INTENTS = {
    "Safe Progression": {
        "weaving": "Usually",
        "bar_swapping": "Prefer fewer swaps",
        "heavy_attacks": "Prefer safe windows",
        "reserve": 25,
        "description": "Consistent, forgiving, reliable performance.",
        "icon": "shield",
    },
    "Balanced": {
        "weaving": "Usually",
        "bar_swapping": "Comfortable",
        "heavy_attacks": "Use when needed",
        "reserve": 20,
        "description": "A balance of safety, sustain, and output.",
        "icon": "scales",
    },
    "Maximum Output": {
        "weaving": "Reliable",
        "bar_swapping": "Comfortable",
        "heavy_attacks": "Avoid unless mandatory",
        "reserve": 10,
        "description": "Aggressive settings for experienced execution.",
        "icon": "optimization",
    },
}


def _clean(value: object) -> str:
    return str(value or "").strip()


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setProperty("muted", True)
    return label


class RotationBuilderPage(FoundryPage):
    """Owned Phase 14 command-center front end for the existing Rotation engine."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.build_service = BuildService(get_data_dir() / "builds.json")
        self.rotation_generation = RotationGenerationSupport()
        self.rotation_runtime = Phase14RotationRuntimeService(
            generation=self.rotation_generation
        )
        self.rotation_sustain = RotationSustainService(get_data_dir() / "eso.db")
        self.rotation_artifacts = BuildRotationArtifactService(
            get_data_dir() / "build_rotations.json"
        )
        self.timeline_projector = RotationTimelineProjectionService()
        self.timeline_icon_resolver = RotationTimelineIconResolver()
        self.rotation_pdf_exporter = RotationPdfExportService()
        self.timeline_projection = None
        self.last_generation_result = None
        self.encounter_service = EncounterBossGuideService(get_data_dir() / "eso.db")
        self.encounter_demand_registry = RotationEncounterDemandPolicyRegistryService()
        self.roster = self.build_service.load()
        self.rotation_plan: RotationPlan | None = None
        self._encounter_rows = tuple()
        self._intent_name = "Balanced"

        self._build_controls()
        self._build_ui()
        self.refresh_saved_builds()
        self._refresh_encounters()
        self._apply_intent("Balanced")

    def _build_controls(self) -> None:
        self.character_combo = QComboBox()
        self.build_combo = QComboBox()
        self.team_combo = QComboBox()
        self.content_combo = QComboBox()
        self.boss_combo = QComboBox()
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["Normal", "Veteran", "Hard Mode"])

        self.rotation_type_combo = QComboBox()
        self.rotation_type_combo.addItem("Semi-static", "Semi-static")
        self.execute_spin = QSpinBox()
        self.execute_spin.setRange(0, 100)
        self.execute_spin.setValue(25)
        self.execute_spin.setSuffix("%")

        self.weaving_combo = QComboBox()
        self.weaving_combo.addItems(["Reliable", "Usually", "Inconsistent", "Do not rely on it"])
        self.bar_swap_combo = QComboBox()
        self.bar_swap_combo.addItems(["Prefer fewer swaps", "Comfortable"])
        self.heavy_attack_combo = QComboBox()
        self.heavy_attack_combo.addItems(
            ["Avoid unless mandatory", "Use when needed", "Prefer safe windows"]
        )
        self.resource_combo = QComboBox()
        self.resource_combo.addItem("Automatic", "")
        self.resource_combo.addItem("Magicka", ResourceType.MAGICKA.value)
        self.resource_combo.addItem("Stamina", ResourceType.STAMINA.value)
        self.minimum_reserve_spin = QSpinBox()
        self.minimum_reserve_spin.setRange(0, 100)
        self.minimum_reserve_spin.setSuffix("%")
        self.minimum_reserve_spin.setValue(20)

        self.ultimate_combo = QComboBox()
        self.ultimate_combo.addItem("Do not schedule Ultimate", "")

        self.character_combo.currentIndexChanged.connect(self._character_changed)
        self.build_combo.currentIndexChanged.connect(self._build_changed)
        self.team_combo.currentIndexChanged.connect(self._build_changed)
        self.content_combo.currentIndexChanged.connect(self._content_changed)
        self.boss_combo.currentIndexChanged.connect(self._build_changed)

        for combo in (
            self.weaving_combo,
            self.bar_swap_combo,
            self.heavy_attack_combo,
        ):
            combo.currentTextChanged.connect(self._refresh_setting_summary)
        self.minimum_reserve_spin.valueChanged.connect(self._refresh_setting_summary)

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Rotation Builder",
            subtitle="Build smarter. Play longer. Survive the hard parts.",
            department="RAID ENGINE • ROTATIONS",
            icon="rotations",
        )
        self.set_header(self.header)

        context = FoundryCard("Rotation Context", "rotations")
        context_row = QHBoxLayout()
        context_row.setContentsMargins(0, 0, 0, 0)
        context_row.setSpacing(7)
        context_controls = (
            ("CHARACTER", "user", self.character_combo, 2, 185),
            ("BUILD", "builds", self.build_combo, 2, 210),
            ("TEAM", "roster", self.team_combo, 1, 165),
            ("TRIAL", "trial", self.content_combo, 1, 175),
            ("BOSS", "boss", self.boss_combo, 1, 175),
            ("DIFFICULTY", "crossed-swords", self.difficulty_combo, 1, 135),
        )
        for title, icon_name, control, stretch, maximum_width in context_controls:
            control.setMinimumWidth(0)
            control.setMaximumWidth(maximum_width)
            control.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            if isinstance(control, QComboBox):
                control.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
                control.setMinimumContentsLength(8)
            field = self._field(title, control, icon_name)
            field.setMinimumWidth(0)
            context_row.addWidget(field, stretch)
        context.addLayout(context_row)
        self.workspace_layout.addWidget(context)

        command_row = QHBoxLayout()
        command_row.setContentsMargins(0, 0, 0, 0)
        command_row.setSpacing(8)
        command_row.addWidget(self._build_intent_card(), 3)
        command_row.addWidget(self._build_obligations_card(), 2)
        self.workspace_layout.addLayout(command_row)

        self.result_tabs = QTabWidget()
        self.result_tabs.setDocumentMode(True)
        self.result_tabs.setMovable(False)
        self.result_tabs.setUsesScrollButtons(False)
        self.result_tabs.setProperty("workspaceTabs", True)
        self.result_tabs.tabBar().hide()

        self.timeline_table = QTableWidget(0, 6)
        self.timeline_table.setHorizontalHeaderLabels(
            ["Time", "Bar", "Action", "Type", "Target", "Sequence"]
        )
        self.timeline_table.verticalHeader().setVisible(False)
        self.timeline_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.timeline_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.timeline_table.horizontalHeader().setStretchLastSection(True)
        self.timeline_table.setMinimumHeight(330)
        timeline_host = QWidget()
        timeline_layout = QVBoxLayout(timeline_host)
        timeline_layout.setContentsMargins(6, 6, 6, 6)

        timeline_controls = QHBoxLayout()
        timeline_controls.setContentsMargins(0, 0, 0, 0)
        timeline_controls.setSpacing(6)
        self.timeline_visual_button = QPushButton("Timeline")
        self.timeline_visual_button.setCheckable(True)
        self.timeline_visual_button.setChecked(True)
        self.timeline_visual_button.setProperty("primary", True)
        self.timeline_details_button = QPushButton("Details")
        self.timeline_details_button.setCheckable(True)
        self.timeline_visual_button.clicked.connect(self._show_visual_timeline)
        self.timeline_details_button.clicked.connect(self._show_timeline_details)
        timeline_controls.addWidget(self.timeline_visual_button)
        timeline_controls.addWidget(self.timeline_details_button)
        timeline_controls.addStretch(1)
        timeline_layout.addLayout(timeline_controls)

        self.timeline_widget = RotationTimelineWidget()
        timeline_layout.addWidget(self.timeline_widget)
        self.timeline_table.hide()

        self.timeline_hint = _muted(
            "Nothing is fabricated before the engine returns an authoritative schedule."
        )
        timeline_layout.addWidget(self.timeline_table)
        timeline_layout.addWidget(self.timeline_hint)
        self.result_tabs.addTab(timeline_host, "Timeline")

        uptime_host = QWidget()
        uptime_layout = QHBoxLayout(uptime_host)
        uptime_layout.setContentsMargins(6, 6, 6, 6)
        sustain_card = FoundryCard("Sustain Snapshot", "drop")
        self.sustain_label = QLabel("Awaiting a generated rotation.")
        self.sustain_label.setWordWrap(True)
        self.sustain_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sustain_card.addWidget(self.sustain_label)
        uptime_layout.addWidget(sustain_card, 1)
        build_card = FoundryCard("Build Context", "builds")
        self.build_summary = QLabel("No saved build selected.")
        self.build_summary.setWordWrap(True)
        build_card.addWidget(self.build_summary)
        self.front_skills = QLabel("Front: —")
        self.front_skills.setWordWrap(True)
        build_card.addWidget(self.front_skills)
        self.back_skills = QLabel("Back: —")
        self.back_skills.setWordWrap(True)
        build_card.addWidget(self.back_skills)
        uptime_layout.addWidget(build_card, 1)
        self.result_tabs.addTab(uptime_host, "Uptime & Resources")

        explanation_host = QWidget()
        explanation_layout = QVBoxLayout(explanation_host)
        explanation_layout.setContentsMargins(6, 6, 6, 6)
        evidence_card = FoundryCard("Engine Evidence", "binoculars")
        self.evidence_label = QLabel(
            "Assumptions and unresolved engine facts will appear after generation."
        )
        self.evidence_label.setWordWrap(True)
        self.evidence_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        evidence_card.addWidget(self.evidence_label)
        explanation_layout.addWidget(evidence_card)
        notes_card = FoundryCard("Personal Notes", "feather")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText(
            "Execution reminders only. Notes do not alter engine evidence."
        )
        self.notes_edit.setMaximumHeight(110)
        notes_card.addWidget(self.notes_edit)
        explanation_layout.addWidget(notes_card)
        self.result_tabs.addTab(explanation_host, "Explanations")

        compare_host = QWidget()
        compare_layout = QVBoxLayout(compare_host)
        compare_layout.setContentsMargins(6, 6, 6, 6)
        compare_card = FoundryCard("Current vs Saved", "scales")
        self.compare_label = QLabel(
            "Generate a rotation to compare it with the last rotation saved to this Build."
        )
        self.compare_label.setWordWrap(True)
        self.compare_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        compare_card.addWidget(self.compare_label)
        compare_layout.addWidget(compare_card)
        compare_layout.addStretch(1)
        self.result_tabs.addTab(compare_host, "Compare")

        save_host = QWidget()
        save_layout = QVBoxLayout(save_host)
        save_layout.setContentsMargins(6, 6, 6, 6)
        save_card = FoundryCard("Save & Export", "download")
        save_card.addWidget(
            _muted(
                "Save the completed authoritative plan to this exact Build, or export the "
                "same materialized timeline as a phone-readable PDF."
            )
        )
        save_actions = QHBoxLayout()
        save_actions.setContentsMargins(0, 0, 0, 0)
        save_actions.setSpacing(8)
        self.save_rotation_button = QPushButton("Save Rotation to Build")
        self.save_rotation_button.setProperty("primary", True)
        self.save_rotation_button.setEnabled(False)
        self.save_rotation_button.clicked.connect(self.save_rotation_to_build)
        self.export_pdf_button = QPushButton("Export PDF")
        self.export_pdf_button.setEnabled(False)
        self.export_pdf_button.clicked.connect(self.export_rotation_pdf)
        save_actions.addWidget(self.save_rotation_button)
        save_actions.addWidget(self.export_pdf_button)
        save_actions.addStretch(1)
        save_card.addLayout(save_actions)
        save_layout.addWidget(save_card)
        save_layout.addStretch(1)
        self.result_tabs.addTab(save_host, "Save & Export")

        self.result_shell = QFrame()
        self.result_shell.setProperty("rotationResultsShell", True)
        result_shell_layout = QVBoxLayout(self.result_shell)
        result_shell_layout.setContentsMargins(6, 6, 6, 6)
        result_shell_layout.setSpacing(6)

        result_nav = QHBoxLayout()
        result_nav.setContentsMargins(0, 0, 0, 0)
        result_nav.setSpacing(5)
        self.result_nav_buttons: list[QPushButton] = []
        result_nav_items = (
            ("Timeline", "hourglass"),
            ("Uptime & Resources", "filter"),
            ("Explanations", "binoculars"),
            ("Compare", "scales"),
            ("Save / Export", "download"),
        )
        for index, (title, icon_name) in enumerate(result_nav_items):
            button = QPushButton(title)
            button.setCheckable(True)
            button.setProperty("rotationResultNav", True)
            button.setMinimumHeight(50)
            set_button_icon(button, icon_name, size=22)
            button.clicked.connect(
                lambda _checked=False, target=index: self._show_result_tab(target)
            )
            result_nav.addWidget(button, 1)
            self.result_nav_buttons.append(button)
        result_shell_layout.addLayout(result_nav)

        self.results_locked_label = QLabel("ⓘ  Generate a rotation to unlock results.")
        self.results_locked_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_locked_label.setProperty("rotationResultsLocked", True)
        self.results_locked_label.setMinimumHeight(56)
        result_shell_layout.addWidget(self.results_locked_label)

        self.result_tabs.hide()
        result_shell_layout.addWidget(self.result_tabs)
        self.workspace_layout.addWidget(self.result_shell)

        self._set_results_unlocked(False)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    def _build_intent_card(self) -> FoundryCard:
        card = FoundryCard("Rotation Intent", "rotations")
        card.addWidget(
            _muted(
                "Choose a focus. FoundryDock configures sensible defaults, which you can adjust."
            )
        )

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.intent_buttons: dict[str, QToolButton] = {}
        for name, values in _INTENTS.items():
            button = QToolButton()
            button.setText(f"{name}\n{values['description']}")
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setCheckable(True)
            button.setMinimumHeight(104)
            button.setMaximumHeight(112)
            button.setProperty("rotationIntentChoice", True)
            set_button_icon(button, values["icon"], size=28)
            button.clicked.connect(
                lambda checked=False, intent=name: self._apply_intent(intent) if checked else None
            )
            self.intent_buttons[name] = button
            buttons.addWidget(button, 1)
        card.addLayout(buttons)

        heading = QHBoxLayout()
        heading.setContentsMargins(0, 4, 0, 2)
        label = QLabel("Generated Settings")
        label.setProperty("phase14SectionHeading", True)
        heading.addWidget(label)
        heading.addStretch(1)
        self.customized_label = QLabel("Preset defaults")
        self.customized_label.setProperty("cardBadge", True)
        heading.addWidget(self.customized_label)
        card.addLayout(heading)

        self.setting_labels = {
            "Weaving": QLabel(),
            "Bar swapping": QLabel(),
            "Heavy attacks": QLabel(),
            "Resource reserve": QLabel(),
        }
        icons = {
            "Weaving": "cog",
            "Bar swapping": "swapping",
            "Heavy attacks": "sword",
            "Resource reserve": "drop",
        }
        for name, value in self.setting_labels.items():
            row = QFrame()
            row.setProperty("rotationSummaryRow", True)
            row.setMinimumHeight(48)
            row.setMaximumHeight(54)
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 5, 12, 5)
            layout.setSpacing(9)
            layout.addWidget(icon_label(icons[name], 22))
            title = QLabel(name)
            title.setProperty("rotationSettingTitle", True)
            layout.addWidget(title)
            layout.addStretch(1)
            layout.addWidget(value)
            card.addWidget(row)

        self.advanced_panel = QFrame()
        self.advanced_panel.setProperty("foundryCard", True)
        advanced = QGridLayout(self.advanced_panel)
        advanced.setContentsMargins(10, 8, 10, 8)
        advanced.setSpacing(7)
        advanced.addWidget(self._field("WEAVING", self.weaving_combo, "cog"), 0, 0)
        advanced.addWidget(self._field("BAR SWAPPING", self.bar_swap_combo, "swapping"), 0, 1)
        advanced.addWidget(self._field("HEAVY ATTACKS", self.heavy_attack_combo, "sword"), 1, 0)
        advanced.addWidget(self._field("PRIMARY RESOURCE", self.resource_combo, "drop"), 1, 1)
        advanced.addWidget(self._field("MINIMUM RESERVE", self.minimum_reserve_spin, "drop"), 2, 0)
        advanced.addWidget(self._field("ROTATION TYPE", self.rotation_type_combo, "rotations"), 2, 1)
        advanced.addWidget(self._field("EXECUTE STARTS", self.execute_spin, "sword"), 3, 0)
        advanced.addWidget(self._field("ULTIMATE", self.ultimate_combo, "optimization"), 3, 1)
        self.advanced_panel.hide()

        advanced_button = QPushButton(
            "Advanced execution & sustain\nCustom rules, conditionals, and resource management."
        )
        advanced_button.setMinimumHeight(54)
        set_button_icon(advanced_button, "uptime", size=19)
        advanced_button.clicked.connect(
            lambda: self.advanced_panel.setVisible(not self.advanced_panel.isVisible())
        )
        card.addWidget(advanced_button)
        card.addWidget(self.advanced_panel)
        return card

    def _build_obligations_card(self) -> FoundryCard:
        card = FoundryCard("Inputs & Obligations", "field-office")
        card.addWidget(
            _muted(
                "Detected from your build, team setup, and encounter. Missing evidence stays missing."
            )
        )

        self.obligation_counts: dict[str, QLabel] = {}
        self.priority_table = QTableWidget(0, 4)
        self.priority_table.setHorizontalHeaderLabels(["Bar", "Slot", "Ability", "Priority"])
        self.priority_table.verticalHeader().setVisible(False)
        self.priority_table.horizontalHeader().setStretchLastSection(True)
        self.priority_table.setMinimumHeight(190)

        priority_host = QWidget()
        priority_layout = QVBoxLayout(priority_host)
        priority_layout.setContentsMargins(8, 4, 8, 8)
        priority_layout.addWidget(self.priority_table)
        priority_host.hide()

        build_skills = self._obligation_row(
            "Build skills",
            "Saved bars, passives, and priorities.",
            "0",
            priority_host,
        )
        card.addWidget(build_skills)

        card.addWidget(
            self._obligation_row(
                "Gear procs",
                "Resolved from the selected saved build.",
                "AUTO",
                None,
            )
        )
        card.addWidget(
            self._obligation_row(
                "Team duties",
                "Assignment evidence when available.",
                "AUTO",
                None,
            )
        )
        pressure_host = QWidget()
        pressure_layout = QVBoxLayout(pressure_host)
        pressure_layout.setContentsMargins(8, 4, 8, 8)
        self.pressure_detail_label = QLabel(
            "Select a reviewed encounter to inspect its Rotation demand policy."
        )
        self.pressure_detail_label.setWordWrap(True)
        self.pressure_detail_label.setProperty("muted", True)
        pressure_layout.addWidget(self.pressure_detail_label)
        pressure_host.hide()
        card.addWidget(
            self._obligation_row(
                "Pressure windows",
                "Reviewed clock and health-threshold demand policies.",
                "0",
                pressure_host,
            )
        )
        card.addWidget(
            self._obligation_row(
                "Advanced rules",
                "Conditionals remain fail-closed until canonical.",
                "—",
                None,
            )
        )
        card.addStretch(1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 8, 0, 0)
        action_row.setSpacing(8)

        self.generate_button = QPushButton("Generate Rotation")
        self.generate_button.setProperty("primary", True)
        self.generate_button.setMinimumHeight(40)
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self.generate_rotation)
        action_row.addWidget(self.generate_button, 2)

        self.clear_button = QPushButton("Clear Results")
        self.clear_button.setMinimumHeight(40)
        self.clear_button.clicked.connect(self.clear_result)
        action_row.addWidget(self.clear_button, 1)

        card.addLayout(action_row)

        self.result_summary = QLabel("Generate a rotation to populate the result workspace.")
        self.result_summary.setProperty("resultSummary", True)
        self.result_summary.setWordWrap(True)
        card.addWidget(self.result_summary)
        return card

    def _obligation_row(
        self,
        title: str,
        description: str,
        count_text: str,
        detail: QWidget | None,
    ) -> QWidget:
        host = QWidget()
        outer = QVBoxLayout(host)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        button = QPushButton()
        button.setProperty("rotationObligationRow", True)
        button.setMinimumHeight(54)
        button.setMaximumHeight(58)
        row = QHBoxLayout(button)
        row.setContentsMargins(11, 6, 10, 6)
        row.setSpacing(8)

        icon_names = {
            "Build skills": "book-open-text",
            "Gear procs": "cog",
            "Team duties": "roster",
            "Pressure windows": "warning",
            "Advanced rules": "uptime",
        }
        row.addWidget(icon_label(icon_names[title], 23))
        title_label = QLabel(title)
        title_label.setMinimumWidth(112)
        title_label.setProperty("rotationObligationTitle", True)
        row.addWidget(title_label)
        description_label = _muted(description)
        description_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        row.addWidget(description_label, 1)
        count = QLabel(count_text)
        count.setProperty("cardBadge", True)
        count.setMinimumWidth(34)
        self.obligation_counts[title] = count
        row.addWidget(count)
        row.addWidget(QLabel("›"))
        outer.addWidget(button)

        if detail is None:
            button.setEnabled(False)
        else:
            outer.addWidget(detail)
            button.clicked.connect(lambda _checked=False: detail.setVisible(not detail.isVisible()))
        return host

    @staticmethod
    def _field(title: str, widget: QWidget, icon_name: str = "") -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        heading = QHBoxLayout()
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(5)
        if icon_name:
            heading.addWidget(icon_label(icon_name, 14))
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        heading.addWidget(label)
        heading.addStretch(1)
        layout.addLayout(heading)
        widget.setMinimumHeight(32)
        widget.setMaximumHeight(32)
        layout.addWidget(widget)
        return host

    @staticmethod
    def _character_name(build) -> str:
        return _clean(
            getattr(build, "CharacterName", "")
            or getattr(build, "Name", "")
            or getattr(build, "Gamertag", "")
            or "Unnamed Character"
        )

    @staticmethod
    def _build_name(build) -> str:
        return _clean(getattr(build, "BuildName", "") or "Current Build")

    @staticmethod
    def _ordinary_skills(values) -> list[str]:
        return [_clean(value) for value in list(values or [])[:5] if _clean(value)]

    @staticmethod
    def _ultimate(values) -> str:
        values = list(values or [])
        return _clean(values[5]) if len(values) > 5 else ""

    def _base_build(self):
        index = self.build_combo.currentData()
        if not isinstance(index, int) or not 0 <= index < len(self.roster.Members):
            return None
        return self.roster.Members[index]

    def _selected_build(self):
        base = self._base_build()
        if base is None:
            return None
        return resolve_build_context(
            base,
            team_name=_clean(self.team_combo.currentData()),
            boss_name=_clean(self.boss_combo.currentText()),
        )

    def refresh_saved_builds(self) -> None:
        selected_character = _clean(self.character_combo.currentData())
        selected_build = _clean(self.build_combo.currentText())
        self.roster = self.build_service.load()

        self.character_combo.blockSignals(True)
        self.character_combo.clear()
        seen: set[str] = set()
        for build in self.roster.Members:
            name = self._character_name(build)
            if name.casefold() in seen:
                continue
            seen.add(name.casefold())
            self.character_combo.addItem(name, name)
        self.character_combo.blockSignals(False)

        index = self.character_combo.findData(selected_character)
        if index < 0 and self.character_combo.count():
            index = 0
        if index >= 0:
            self.character_combo.setCurrentIndex(index)

        self._character_changed()
        if selected_build:
            build_index = self.build_combo.findText(selected_build)
            if build_index >= 0:
                self.build_combo.setCurrentIndex(build_index)
        self._build_changed()

    def _character_changed(self, *_args) -> None:
        character = _clean(self.character_combo.currentData())
        self.build_combo.blockSignals(True)
        self.build_combo.clear()
        for index, build in enumerate(self.roster.Members):
            if self._character_name(build) == character:
                self.build_combo.addItem(self._build_name(build), index)
        self.build_combo.blockSignals(False)
        if self.build_combo.count():
            self.build_combo.setCurrentIndex(0)
        self._refresh_team_choices()
        self._build_changed()

    def _refresh_team_choices(self) -> None:
        previous = _clean(self.team_combo.currentData())
        base = self._base_build()
        teams: list[str] = []
        if base is not None:
            for variant in tuple(getattr(base, "ContextVariants", ()) or ()):
                team = _clean(getattr(variant, "TeamName", ""))
                if team and team.casefold() not in {value.casefold() for value in teams}:
                    teams.append(team)

        self.team_combo.blockSignals(True)
        self.team_combo.clear()
        self.team_combo.addItem("No team context", "")
        for team in sorted(teams, key=str.casefold):
            self.team_combo.addItem(team, team)
        if previous:
            index = self.team_combo.findData(previous)
            if index >= 0:
                self.team_combo.setCurrentIndex(index)
        elif len(teams) == 1:
            self.team_combo.setCurrentIndex(1)
        self.team_combo.blockSignals(False)

    def _refresh_encounters(self) -> None:
        self._encounter_rows = tuple(self.encounter_service.encounter_summaries())
        previous = self.content_combo.currentData()
        self.content_combo.blockSignals(True)
        self.content_combo.clear()
        self.content_combo.addItem("All Content", None)
        seen: set[str] = set()
        for row in self._encounter_rows:
            content_id = _clean(row.content_id)
            if not content_id or content_id in seen:
                continue
            seen.add(content_id)
            self.content_combo.addItem(_clean(row.content_name) or content_id, content_id)
        self.content_combo.blockSignals(False)
        if previous is not None:
            index = self.content_combo.findData(previous)
            if index >= 0:
                self.content_combo.setCurrentIndex(index)
        self._content_changed()

    def _content_changed(self, *_args) -> None:
        content_id = self.content_combo.currentData()
        previous = self.boss_combo.currentData()
        self.boss_combo.blockSignals(True)
        self.boss_combo.clear()
        rows = [
            row
            for row in self._encounter_rows
            if content_id is None or row.content_id == content_id
        ]
        for row in rows:
            encounter_id = _clean(row.encounter_id)
            if encounter_id:
                self.boss_combo.addItem(_clean(row.name) or encounter_id, encounter_id)
        if previous is not None:
            index = self.boss_combo.findData(previous)
            if index >= 0:
                self.boss_combo.setCurrentIndex(index)
        if self.boss_combo.count() and self.boss_combo.currentIndex() < 0:
            self.boss_combo.setCurrentIndex(0)
        self.boss_combo.blockSignals(False)
        self._build_changed()

    def _build_changed(self, *_args) -> None:
        self.clear_result()
        self._refresh_team_choices()
        build = self._selected_build()
        self.priority_table.setRowCount(0)

        self.ultimate_combo.blockSignals(True)
        self.ultimate_combo.clear()
        self.ultimate_combo.addItem("Do not schedule Ultimate", "")

        if build is None:
            self.ultimate_combo.blockSignals(False)
            self.build_summary.setText("No saved build selected.")
            self.front_skills.setText("Front: —")
            self.back_skills.setText("Back: —")
            self.generate_button.setEnabled(False)
            self.obligation_counts["Build skills"].setText("0")
            self._refresh_pressure_obligations()
            return

        front = self._ordinary_skills(getattr(build, "FrontBarSkills", []))
        back = self._ordinary_skills(getattr(build, "BackBarSkills", []))
        for bar_name, values in (
            ("Front", list(getattr(build, "FrontBarSkills", []) or [])[:5]),
            ("Back", list(getattr(build, "BackBarSkills", []) or [])[:5]),
        ):
            for slot, skill in enumerate(values, start=1):
                skill = _clean(skill)
                if not skill:
                    continue
                row = self.priority_table.rowCount()
                self.priority_table.insertRow(row)
                for column, value in enumerate((bar_name, str(slot), skill, "100")):
                    item = QTableWidgetItem(value)
                    if column < 3:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.priority_table.setItem(row, column, item)

        front_ultimate = self._ultimate(getattr(build, "FrontBarSkills", []))
        back_ultimate = self._ultimate(getattr(build, "BackBarSkills", []))
        if front_ultimate:
            self.ultimate_combo.addItem(f"Front · {front_ultimate}", "front")
        if back_ultimate:
            self.ultimate_combo.addItem(f"Back · {back_ultimate}", "back")
        self.ultimate_combo.blockSignals(False)

        role = _clean(getattr(build, "Role", "")) or "Unspecified role"
        eso_class = _clean(getattr(build, "EsoClass", "")) or "Unspecified class"
        race = _clean(getattr(build, "Race", "")) or "Unspecified race"
        food = _clean(getattr(build, "Food", "")) or "Not selected"
        potion = _clean(getattr(build, "Potion", "")) or "Not selected"
        self.build_summary.setText(
            f"{self._character_name(build)} · {self._build_name(build)}\n"
            f"{eso_class} · {race} · {role}\nFood: {food}\nPotion: {potion}"
        )
        self.front_skills.setText("Front: " + (" · ".join(front) if front else "No ordinary skills"))
        self.back_skills.setText("Back: " + (" · ".join(back) if back else "No ordinary skills"))
        self.obligation_counts["Build skills"].setText(str(len(front) + len(back)))
        self._refresh_pressure_obligations()
        self.generate_button.setEnabled(bool(front or back))
        self.status.info(
            f"Loaded {self._character_name(build)} · {self._build_name(build)}."
        )

    def _refresh_pressure_obligations(self) -> None:
        if not hasattr(self, "obligation_counts"):
            return
        encounter_id = _clean(self.boss_combo.currentData())
        if not encounter_id:
            self.obligation_counts["Pressure windows"].setText("0")
            if hasattr(self, "pressure_detail_label"):
                self.pressure_detail_label.setText(
                    "Select a reviewed encounter to inspect its Rotation demand policy."
                )
            return

        try:
            entry = self.encounter_demand_registry.entry_for(encounter_id)
        except (OSError, ValueError) as exc:
            self.obligation_counts["Pressure windows"].setText("!")
            self.pressure_detail_label.setText(
                "Encounter demand policy could not be read: " + str(exc)
            )
            return

        if entry is None:
            self.obligation_counts["Pressure windows"].setText("—")
            self.pressure_detail_label.setText(
                "No reviewed Rotation demand policy is stored for this encounter. "
                "Nothing is inferred from boss prose or display names."
            )
            return

        clock = tuple(entry.clock_policies)
        threshold = tuple(entry.threshold_policies)
        blockers = tuple(entry.review_blockers)
        self.obligation_counts["Pressure windows"].setText(
            str(len(clock) + len(threshold))
        )

        lines = []
        for policy in clock:
            lines.append(
                f"Clock · {policy.fact_key} · {policy.kind.value.replace('_', ' ').title()}"
            )
        for policy in threshold:
            lines.append(
                f"Health {policy.threshold_fraction * 100:g}% · {policy.fact_key} · "
                f"{policy.kind.value.replace('_', ' ').title()}"
            )
        for blocker in blockers:
            lines.append(f"Needs review · {blocker.summary}")
        self.pressure_detail_label.setText(
            "\n".join(lines)
            if lines
            else "This encounter was explicitly reviewed with no Rotation demand policies."
        )

    @staticmethod
    def _artifact_metrics(artifact: dict | None) -> dict[str, int | float]:
        actions = list((artifact or {}).get("actions") or [])
        kinds = [
            _clean(action.get("kind")).casefold()
            for action in actions
            if isinstance(action, dict)
        ]
        return {
            "actions": len(actions),
            "heavy": sum(kind == "heavy_attack" for kind in kinds),
            "swaps": sum(kind == "bar_swap" for kind in kinds),
            "unresolved": len(list((artifact or {}).get("unresolved") or [])),
            "duration": float((artifact or {}).get("duration_seconds") or 0.0),
        }

    def _refresh_compare(self) -> None:
        if not hasattr(self, "compare_label"):
            return
        if self.rotation_plan is None:
            self.compare_label.setText(
                "Generate a rotation to compare it with the last rotation saved to this Build."
            )
            return

        base_build = self._base_build()
        build_id = (
            resolve_canonical_build_id(
                self.build_service.canonical.catalog_service,
                base_build,
            )
            if base_build is not None
            else None
        )
        saved = self.rotation_artifacts.get_rotation(build_id or "")
        current = jsonable(self.rotation_plan)
        current_metrics = self._artifact_metrics(current)

        if not saved:
            self.compare_label.setText(
                "CURRENT GENERATED\n"
                f"{current_metrics['duration']:g}s · {current_metrics['actions']} actions · "
                f"{current_metrics['heavy']} Heavy Attacks · {current_metrics['swaps']} bar swaps · "
                f"{current_metrics['unresolved']} unresolved\n\n"
                "No previously saved rotation exists for this Build."
            )
            return

        saved_metrics = self._artifact_metrics(saved)
        self.compare_label.setText(
            "CURRENT GENERATED\n"
            f"{current_metrics['duration']:g}s · {current_metrics['actions']} actions · "
            f"{current_metrics['heavy']} Heavy Attacks · {current_metrics['swaps']} bar swaps · "
            f"{current_metrics['unresolved']} unresolved\n\n"
            "LAST SAVED\n"
            f"{saved_metrics['duration']:g}s · {saved_metrics['actions']} actions · "
            f"{saved_metrics['heavy']} Heavy Attacks · {saved_metrics['swaps']} bar swaps · "
            f"{saved_metrics['unresolved']} unresolved"
        )

    def _apply_intent(self, name: str) -> None:
        values = _INTENTS[name]
        self._intent_name = name
        self.weaving_combo.setCurrentText(values["weaving"])
        self.bar_swap_combo.setCurrentText(values["bar_swapping"])
        self.heavy_attack_combo.setCurrentText(values["heavy_attacks"])
        self.minimum_reserve_spin.setValue(int(values["reserve"]))
        for button_name, button in self.intent_buttons.items():
            button.blockSignals(True)
            button.setChecked(button_name == name)
            button.blockSignals(False)
        self._refresh_setting_summary()

    def _refresh_setting_summary(self, *_args) -> None:
        if not hasattr(self, "setting_labels"):
            return
        self.setting_labels["Weaving"].setText(self.weaving_combo.currentText())
        self.setting_labels["Bar swapping"].setText(self.bar_swap_combo.currentText())
        self.setting_labels["Heavy attacks"].setText(self.heavy_attack_combo.currentText())
        self.setting_labels["Resource reserve"].setText(
            f"{self.minimum_reserve_spin.value()}%"
        )
        values = _INTENTS.get(self._intent_name)
        customized = bool(
            values
            and (
                self.weaving_combo.currentText() != values["weaving"]
                or self.bar_swap_combo.currentText() != values["bar_swapping"]
                or self.heavy_attack_combo.currentText() != values["heavy_attacks"]
                or self.minimum_reserve_spin.value() != int(values["reserve"])
            )
        )
        self.customized_label.setText("Customized" if customized else "Preset defaults")

    def ability_priorities(self) -> tuple[AbilityPriorityEntry, ...]:
        entries: list[AbilityPriorityEntry] = []
        for row in range(self.priority_table.rowCount()):
            bar = _clean(self.priority_table.item(row, 0).text()).casefold()
            slot = int(_clean(self.priority_table.item(row, 1).text()))
            skill = _clean(self.priority_table.item(row, 2).text())
            priority = int(_clean(self.priority_table.item(row, 3).text()))
            entries.append(
                AbilityPriorityEntry(
                    bar=bar,
                    slot=slot,
                    skill_name=skill,
                    priority=priority,
                )
            )
        return tuple(entries)

    def _explicit_resource(self) -> ResourceType | None:
        explicit = _clean(self.resource_combo.currentData())
        return ResourceType(explicit) if explicit else None

    def _selected_resource(self, build) -> ResourceType:
        explicit = self._explicit_resource()
        if explicit is not None:
            return explicit
        role = _clean(getattr(build, "Role", "")).casefold()
        if role == "dd":
            front_weapon = _clean(
                getattr(getattr(build, "FrontBarWeapon", None), "WeaponType", "")
            )
            if any(
                token in front_weapon.casefold()
                for token in ("bow", "two-handed", "sword", "axe", "mace", "dagger")
            ):
                return ResourceType.STAMINA
        return ResourceType.MAGICKA

    def generate_rotation(self) -> None:
        build = self._selected_build()
        if build is None:
            self.status.warning("Select a saved build before generating a rotation.")
            return

        weave = self.weaving_combo.currentText() != "Do not rely on it"
        try:
            priorities = self.ability_priorities()
        except (AttributeError, TypeError, ValueError) as exc:
            self.status.warning(f"Ability priority is invalid: {exc}")
            return

        request = RotationGenerationRequest(
            duration_seconds=60.0,
            rotation_type=_clean(self.rotation_type_combo.currentData()) or "Semi-static",
            potion=_clean(getattr(build, "Potion", "")),
            potion_on_cooldown=False,
            weave_light_attacks=weave,
            ultimate_bar=_clean(self.ultimate_combo.currentData()),
            starting_ultimate=0.0,
            use_scheduled_combat_attacks_for_ultimate=weave,
            ability_priorities=priorities,
        )

        try:
            runtime = self.rotation_runtime.generate(
                build=build,
                request=request,
                heavy_behavior=self.heavy_attack_combo.currentText(),
                reserve_fraction=float(self.minimum_reserve_spin.value()) / 100.0,
                explicit_resource=self._explicit_resource(),
            )
            result = runtime.generation
        except Exception as exc:
            self.clear_result()
            self.status.error(f"Rotation generation failed: {exc}")
            return

        self.last_generation_result = result
        self.rotation_plan = result.plan
        self._render_plan(result.plan)
        self._render_evidence(result.plan)
        self._refresh_visual_timeline(result.plan, result.duration_evidence)
        self._evaluate_sustain(
            build,
            result.plan,
            resource=runtime.resource,
            recovery_projection=runtime.recovery_projection,
        )
        self.save_rotation_button.setEnabled(bool(result.plan.actions))
        self.export_pdf_button.setEnabled(self.timeline_projection is not None)
        heavy_count = sum(
            1 for action in result.plan.actions
            if action.kind is RotationActionKind.HEAVY_ATTACK
        )
        self.result_summary.setText(
            f"{result.plan.duration_seconds:g}s • {len(result.plan.actions)} actions • "
            f"{heavy_count} Heavy Attacks • {len(result.plan.unresolved)} unresolved"
        )
        self._refresh_compare()
        self._set_results_unlocked(True)
        self.status.success(
            f"Generated {len(result.plan.actions)} actions over {result.plan.duration_seconds:g}s."
        )

    def _render_plan(self, plan: RotationPlan) -> None:
        self.timeline_table.setRowCount(0)
        for action in plan.actions:
            row = self.timeline_table.rowCount()
            self.timeline_table.insertRow(row)
            values = (
                f"{action.time_seconds:05.1f}s",
                (action.bar or "—").title(),
                action.name or self._action_label(action.kind),
                action.kind.value.replace("_", " ").title(),
                action.target_key or "—",
                str(action.sequence),
            )
            for column, value in enumerate(values):
                self.timeline_table.setItem(row, column, QTableWidgetItem(value))
        self.timeline_hint.setText(
            f"Authoritative engine schedule · {len(plan.actions)} actions · {plan.duration_seconds:g}s"
        )

    @staticmethod
    def _action_label(kind: RotationActionKind) -> str:
        labels = {
            RotationActionKind.LIGHT_ATTACK: "Light Attack",
            RotationActionKind.HEAVY_ATTACK: "Heavy Attack",
            RotationActionKind.BAR_SWAP: "Bar Swap",
            RotationActionKind.BLOCK: "Block",
            RotationActionKind.DODGE: "Dodge",
            RotationActionKind.WAIT: "Wait",
        }
        return labels.get(kind, kind.value.replace("_", " ").title())

    def _render_evidence(self, plan: RotationPlan) -> None:
        sections: list[str] = []
        if plan.assumptions:
            sections.append(
                "ASSUMPTIONS\n" + "\n".join(f"• {item}" for item in plan.assumptions)
            )
        if plan.unresolved:
            sections.append(
                "UNRESOLVED\n" + "\n".join(f"• {item}" for item in plan.unresolved)
            )
        self.evidence_label.setText(
            "\n\n".join(sections)
            or "No assumptions or unresolved evidence were reported."
        )

    def _evaluate_sustain(
        self,
        build,
        plan: RotationPlan,
        *,
        resource: ResourceType,
        recovery_projection=None,
    ) -> None:
        try:
            projection = (
                recovery_projection
                if recovery_projection is not None
                else self.rotation_sustain.evaluate(
                    build=build,
                    plan=plan,
                    resource=resource,
                )
            )
        except Exception as exc:
            self.sustain_label.setText(
                "Schedule generated. Sustain could not be evaluated.\n"
                f"{exc}"
            )
            return

        values = [value for _, value in projection.series]
        start = values[0] if values else None
        minimum = min(values) if values else None
        end = values[-1] if values else None
        lines = [
            projection.resource.value.title(),
            f"Start: {start:g}" if start is not None else "Start: —",
            f"Minimum: {minimum:g}" if minimum is not None else "Minimum: —",
            f"End: {end:g}" if end is not None else "End: —",
        ]
        if projection.unresolved:
            lines.extend(["", "Needs review:"])
            lines.extend(f"• {item}" for item in projection.unresolved[:6])
        self.sustain_label.setText("\n".join(lines))

    def _show_result_tab(self, index: int) -> None:
        if not 0 <= index < self.result_tabs.count():
            return
        self.result_tabs.setCurrentIndex(index)
        for button_index, button in enumerate(self.result_nav_buttons):
            button.blockSignals(True)
            button.setChecked(button_index == index)
            button.blockSignals(False)

    def _set_results_unlocked(self, unlocked: bool) -> None:
        if not hasattr(self, "result_nav_buttons"):
            return
        for button in self.result_nav_buttons:
            button.setEnabled(unlocked)
        self.results_locked_label.setVisible(not unlocked)
        self.result_tabs.setVisible(unlocked)
        if unlocked:
            self._show_result_tab(0)

    def _show_visual_timeline(self) -> None:
        self.timeline_visual_button.setChecked(True)
        self.timeline_details_button.setChecked(False)
        self.timeline_widget.show()
        self.timeline_table.hide()

    def _show_timeline_details(self) -> None:
        self.timeline_visual_button.setChecked(False)
        self.timeline_details_button.setChecked(True)
        self.timeline_widget.hide()
        self.timeline_table.show()

    def _refresh_visual_timeline(self, plan: RotationPlan, duration_evidence) -> None:
        try:
            projection = self.timeline_projector.project(
                plan,
                duration_evidence=duration_evidence,
                icon_path_resolver=self.timeline_icon_resolver.resolve,
            )
        except Exception as exc:
            self.timeline_projection = None
            self.timeline_widget.clear_projection()
            self.timeline_hint.setText(
                "The authoritative plan is available, but visual timeline projection failed: "
                + str(exc)
            )
            return

        self.timeline_projection = projection
        self.timeline_widget.set_projection(projection)
        self._show_visual_timeline()

    def _rotation_artifact(self) -> dict:
        plan = self.rotation_plan
        if plan is None or not plan.actions:
            raise ValueError("Generate a completed rotation before saving it to the build.")

        build = self._selected_build()
        payload = jsonable(plan)
        payload["artifact_schema_version"] = 1
        payload["role"] = _clean(getattr(build, "Role", "")) if build is not None else ""
        payload["rotation_type"] = _clean(self.rotation_type_combo.currentData()) or "Semi-static"
        payload["encounter_id"] = _clean(self.boss_combo.currentData())
        payload["setup"] = {
            "intent": self._intent_name,
            "team": _clean(self.team_combo.currentData()),
            "trial_id": _clean(self.content_combo.currentData()),
            "boss": _clean(self.boss_combo.currentText()),
            "difficulty": _clean(self.difficulty_combo.currentText()),
            "execute_percent": int(self.execute_spin.value()),
            "weaving": _clean(self.weaving_combo.currentText()),
            "bar_swapping": _clean(self.bar_swap_combo.currentText()),
            "heavy_attacks": _clean(self.heavy_attack_combo.currentText()),
            "recovery_resource": (
                self._explicit_resource().value
                if self._explicit_resource() is not None
                else "automatic"
            ),
            "recovery_trigger_fraction": float(self.minimum_reserve_spin.value()) / 100.0,
            "ultimate_bar": _clean(self.ultimate_combo.currentData()),
            "potion": _clean(getattr(build, "Potion", "")) if build is not None else "",
            "potion_on_cooldown": False,
            "notes": self.notes_edit.toPlainText().strip(),
        }
        return payload

    def save_rotation_to_build(self) -> None:
        base_build = self._base_build()
        if base_build is None:
            self.status.warning("Select a saved build before saving a rotation.")
            return
        if self.rotation_plan is None or not self.rotation_plan.actions:
            self.status.warning("Generate a completed rotation before saving it.")
            return

        build_id = resolve_canonical_build_id(
            self.build_service.canonical.catalog_service,
            base_build,
        )
        if not build_id:
            self.status.warning(
                "This build could not be resolved to one canonical Build identity; "
                "the rotation was not saved."
            )
            return

        try:
            self.rotation_artifacts.save_rotation(
                build_id=build_id,
                artifact=self._rotation_artifact(),
            )
        except (OSError, ValueError) as exc:
            self.status.error(f"Save rotation to build failed: {exc}")
            return

        self._refresh_compare()
        self.status.success(
            f"Saved rotation to {self._character_name(base_build)} · "
            f"{self._build_name(base_build)}."
        )

    @staticmethod
    def _safe_filename(value: str) -> str:
        import re

        cleaned = re.sub(
            r"[^A-Za-z0-9._-]+",
            "_",
            str(value or "").strip(),
        ).strip("_.")
        return cleaned or "rotation"

    def export_rotation_pdf(self) -> None:
        plan = self.rotation_plan
        projection = self.timeline_projection
        if plan is None or projection is None:
            self.status.warning(
                "Generate a rotation with a materialized timeline before exporting."
            )
            return

        build = self._selected_build()
        default_name = (
            f"{self._safe_filename(plan.character_name)}_"
            f"{self._safe_filename(plan.build_name)}_rotation.pdf"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Rotation PDF",
            default_name,
            "PDF Files (*.pdf)",
        )
        if not filename:
            return

        context = RotationPdfExportContext(
            role=_clean(getattr(build, "Role", "")) or "Unspecified",
            eso_class=_clean(getattr(build, "EsoClass", "")) or "Unspecified",
            race=_clean(getattr(build, "Race", "")) or "Unspecified",
            rotation_mode=_clean(self.rotation_type_combo.currentData()) or "Semi-static",
            target_type="Encounter" if _clean(self.boss_combo.currentData()) else "General",
            sustain_summary=self.sustain_label.text(),
            sustain_detail=(
                f"Intent: {self._intent_name}; "
                f"Heavy attacks: {self.heavy_attack_combo.currentText()}; "
                f"Reserve: {self.minimum_reserve_spin.value()}%"
            ),
            notes=self.notes_edit.toPlainText().strip(),
        )
        try:
            output = self.rotation_pdf_exporter.export(
                plan=plan,
                projection=projection,
                path=Path(filename),
                context=context,
                include_details=True,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            self.status.warning(f"Rotation PDF export failed: {exc}")
            return

        self.status.success(f"Rotation PDF exported: {output}")

    def clear_result(self) -> None:
        self.rotation_plan = None
        self.last_generation_result = None
        self.timeline_projection = None
        if hasattr(self, "timeline_widget"):
            self.timeline_widget.clear_projection()
        if hasattr(self, "save_rotation_button"):
            self.save_rotation_button.setEnabled(False)
        if hasattr(self, "export_pdf_button"):
            self.export_pdf_button.setEnabled(False)
        if hasattr(self, "timeline_table"):
            self.timeline_table.setRowCount(0)
        if hasattr(self, "timeline_hint"):
            self.timeline_hint.setText(
                "Nothing is fabricated before the engine returns an authoritative schedule."
            )
        if hasattr(self, "evidence_label"):
            self.evidence_label.setText(
                "Assumptions and unresolved engine facts will appear after generation."
            )
        if hasattr(self, "sustain_label"):
            self.sustain_label.setText("Awaiting a generated rotation.")
        if hasattr(self, "result_summary"):
            self.result_summary.setText(
                "Generate a rotation to populate the result workspace."
            )
        if hasattr(self, "compare_label"):
            self.compare_label.setText(
                "Generate a rotation to compare it with the last rotation saved to this Build."
            )
        if hasattr(self, "result_nav_buttons"):
            self._set_results_unlocked(False)


__all__ = ["RotationBuilderPage"]
