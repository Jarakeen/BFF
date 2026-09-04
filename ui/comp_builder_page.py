from __future__ import annotations

from collections import Counter

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.eso_database import EsoDatabase
from services.generated_roster_plan_service import (
    GeneratedRosterPlanService,
    GeneratedRosterPlanSlot,
)
from services.team_composition_catalog import (
    CompositionSlot,
    TeamCompositionCatalog,
    TeamCompositionTemplate,
    find_composition_template,
    flexible_raid_slots,
)
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


ESO_CLASSES = (
    "Any class",
    "Arcanist",
    "Dragonknight",
    "Necromancer",
    "Nightblade",
    "Sorcerer",
    "Templar",
    "Warden",
)

GOAL_TRIALS = {
    "Swashbuckler Supreme": "Dreadsail Reef",
    "Godslayer": "Sunspire",
    "Gryphon Heart": "Cloudrest",
    "Hurricane Herald": "Dreadsail Reef",
    "Planebreaker": "Rockgrove",
    "Custom Goal": "Custom Trial",
}


class CompBuilderPage(FoundryPage):
    """Define a raid composition before players and builds are assigned."""

    rosterPlanSent = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        data_dir = get_data_dir()
        self.catalog = TeamCompositionCatalog(data_dir / "team_compositions.json")
        self.snapshot = self.catalog.load()
        self.plan_service = GeneratedRosterPlanService(EsoDatabase(data_dir / "eso.db"))
        self.current_template: TeamCompositionTemplate | None = None
        self.current_slots: tuple[CompositionSlot, ...] = ()
        self._build_ui()
        self._load_for_goal()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Comp Builder",
            subtitle="Define the raid composition first. Assign people and optimize builds afterward.",
            department="RAID ENGINE • COMP BUILDER",
        )
        self.set_header(self.header)

        self.goal_combo = QComboBox()
        self.goal_combo.addItems(tuple(GOAL_TRIALS))
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(("Veteran Hardmode", "Veteran", "Normal"))
        self.update_combo = QComboBox()
        self.update_combo.addItem(self.snapshot.game_update or "Unresolved")
        self.update_combo.setEnabled(False)
        self.header.add_context_widget(self._context_field("GOAL", self.goal_combo))
        self.header.add_context_widget(self._context_field("DIFFICULTY", self.difficulty_combo))
        self.header.add_context_widget(self._context_field("GAME UPDATE", self.update_combo))

        workspace = QWidget()
        root = QVBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)

        self.matrix_card = FoundryCard("Composition Matrix", "◈")
        matrix_actions = QWidget()
        matrix_actions_layout = QHBoxLayout(matrix_actions)
        matrix_actions_layout.setContentsMargins(0, 0, 0, 0)
        matrix_actions_layout.setSpacing(6)
        self.recommended_button = QPushButton("Load Recommended")
        self.reset_button = QPushButton("Reset Flexible")
        matrix_actions_layout.addWidget(self.recommended_button)
        matrix_actions_layout.addWidget(self.reset_button)
        self.matrix_card.set_header_action(matrix_actions)

        self.matrix_table = QTableWidget(0, 6)
        self.matrix_table.setHorizontalHeaderLabels(
            (
                "SLOT",
                "ROLE",
                "PREFERRED CLASS",
                "ALTERNATIVES",
                "RESPONSIBILITIES",
                "PROVIDERS",
            )
        )
        self.matrix_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.matrix_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.matrix_table.setAlternatingRowColors(True)
        self.matrix_table.verticalHeader().setVisible(False)
        self.matrix_table.horizontalHeader().setStretchLastSection(True)
        self.matrix_table.setMinimumHeight(500)
        self.matrix_card.addWidget(self.matrix_table)
        top.addWidget(self.matrix_card, 7)

        side = QVBoxLayout()
        side.setSpacing(10)

        context_card = FoundryCard("Composition Details", "✦")
        self.trial_label = QLabel()
        self.trial_label.setWordWrap(True)
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        context_card.addWidget(self.trial_label)
        context_card.addWidget(self.summary_label)
        side.addWidget(context_card)

        evidence_card = FoundryCard("Evidence & Provenance", "⌁")
        self.evidence_text = QTextEdit()
        self.evidence_text.setReadOnly(True)
        self.evidence_text.setMinimumHeight(220)
        evidence_card.addWidget(self.evidence_text)
        side.addWidget(evidence_card, 1)

        top.addLayout(side, 3)
        root.addLayout(top, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        coverage_card = FoundryCard("Coverage Summary", "⚑")
        self.coverage_label = QLabel()
        self.coverage_label.setWordWrap(True)
        coverage_card.addWidget(self.coverage_label)
        bottom.addWidget(coverage_card, 2)

        actions_card = FoundryCard("Roster Handoff", "➜")
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("PLAN NAME"))
        self.plan_name_input = QLineEdit()
        name_row.addWidget(self.plan_name_input, 1)
        actions_card.addLayout(name_row)
        note = QLabel(
            "This sends composition requirements to Roster. It does not invent players or complete builds."
        )
        note.setWordWrap(True)
        actions_card.addWidget(note)
        self.send_button = QPushButton("Send Composition to Roster")
        self.send_button.setProperty("primary", True)
        actions_card.addWidget(self.send_button)
        bottom.addWidget(actions_card, 2)

        root.addLayout(bottom)
        self.add_workspace(workspace)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

        self.goal_combo.currentTextChanged.connect(self._load_for_goal)
        self.difficulty_combo.currentTextChanged.connect(self._load_for_goal)
        self.recommended_button.clicked.connect(self._load_recommended)
        self.reset_button.clicked.connect(self._load_flexible)
        self.send_button.clicked.connect(self._send_to_roster)

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

    def _matching_template(self) -> TeamCompositionTemplate | None:
        return find_composition_template(
            self.snapshot,
            goal=self.goal_combo.currentText(),
            difficulty=self.difficulty_combo.currentText(),
        )

    def _load_for_goal(self, *_args) -> None:
        template = self._matching_template()
        if template is None:
            self._load_flexible(show_status=False)
            self.status.info(
                f"No published {self.goal_combo.currentText()} composition is in the "
                "current catalog yet. Loaded an editable 2/2/8 skeleton instead."
            )
            return
        self._apply_template(template)
        self.status.success(
            f"Loaded {template.name} from {template.catalog_version}."
        )

    def _load_recommended(self, *_args) -> None:
        template = self._matching_template()
        if template is None:
            self.status.warning(
                f"No evidence-backed {self.goal_combo.currentText()} composition is published yet. "
                "The flexible matrix remains editable."
            )
            return
        self._apply_template(template)
        self.status.success(f"Restored recommended composition: {template.name}.")

    def _load_flexible(self, *_args, show_status: bool = True) -> None:
        self.current_template = None
        self.current_slots = flexible_raid_slots(12)
        self._render_slots(self.current_slots)
        goal = self.goal_combo.currentText().strip() or "Custom Goal"
        self.plan_name_input.setText(f"{goal} Composition")
        self.trial_label.setText(
            f"TRIAL\n{GOAL_TRIALS.get(goal, 'Custom Trial')}\n\nGOAL\n{goal}"
        )
        self.summary_label.setText(
            "Manual composition\n2 Tanks • 2 Healers • 8 Damage Dealers\n\n"
            "No external class recommendation is being asserted for this matrix."
        )
        self.evidence_text.setPlainText(
            "No published composition evidence is attached to this manual matrix.\n\n"
            "Choose classes and responsibilities deliberately. BFF will preserve this as a roster-plan requirement, not a complete build."
        )
        self._refresh_coverage()
        self.recommended_button.setEnabled(self._matching_template() is not None)
        if show_status:
            self.status.info("Reset to a flexible 2/2/8 composition.")

    def _apply_template(self, template: TeamCompositionTemplate) -> None:
        self.current_template = template
        self.current_slots = template.slots
        self._render_slots(template.slots)
        self.plan_name_input.setText(f"{template.goal} Composition")
        self.trial_label.setText(
            f"TRIAL\n{template.trial_name or GOAL_TRIALS.get(template.goal, 'Unresolved')}\n\n"
            f"GOAL\n{template.goal}\n\nDIFFICULTY\n{template.difficulty or 'Unresolved'}"
        )
        self.summary_label.setText(
            f"{len(template.slots)} raid chairs\n"
            f"Catalog: {template.catalog_version}\n"
            f"Game update: {template.game_update}\n\n"
            "This is composition evidence, not a complete build prescription."
        )
        evidence: list[str] = []
        for source in template.sources:
            evidence.append(source.name)
            if source.url:
                evidence.append(source.url)
            if source.retrieved_at:
                evidence.append(f"Retrieved: {source.retrieved_at}")
            if source.note:
                evidence.append(source.note)
            evidence.append("")
        self.evidence_text.setPlainText("\n".join(evidence).strip() or "No source metadata recorded.")
        self.recommended_button.setEnabled(True)
        self._refresh_coverage()

    def _render_slots(self, slots: tuple[CompositionSlot, ...]) -> None:
        self.matrix_table.setRowCount(len(slots))
        for row, slot in enumerate(slots):
            self.matrix_table.setItem(row, 0, QTableWidgetItem(slot.slot_name))
            self.matrix_table.setItem(row, 1, QTableWidgetItem(slot.role))

            class_combo = QComboBox()
            class_combo.addItems(ESO_CLASSES)
            preferred = slot.preferred_class or "Any class"
            index = class_combo.findText(preferred)
            class_combo.setCurrentIndex(index if index >= 0 else 0)
            class_combo.currentTextChanged.connect(self._refresh_coverage)
            self.matrix_table.setCellWidget(row, 2, class_combo)

            self.matrix_table.setItem(
                row,
                3,
                QTableWidgetItem(", ".join(slot.alternative_classes) or "Flexible"),
            )
            self.matrix_table.setItem(
                row,
                4,
                QTableWidgetItem(" • ".join(slot.responsibilities) or "Open responsibility"),
            )
            self.matrix_table.setItem(
                row,
                5,
                QTableWidgetItem(" • ".join(slot.provider_requirements) or "—"),
            )

    def _selected_class(self, row: int) -> str:
        combo = self.matrix_table.cellWidget(row, 2)
        return combo.currentText().strip() if isinstance(combo, QComboBox) else "Any class"

    def _refresh_coverage(self, *_args) -> None:
        classes = Counter(
            selected
            for row in range(self.matrix_table.rowCount())
            if (selected := self._selected_class(row)) and selected != "Any class"
        )
        class_summary = (
            " • ".join(f"{name} ×{count}" for name, count in sorted(classes.items()))
            if classes
            else "No class requirements selected"
        )

        providers: list[str] = []
        for row in range(self.matrix_table.rowCount()):
            item = self.matrix_table.item(row, 5)
            if item is None:
                continue
            text = item.text().strip()
            if text and text != "—":
                providers.append(text)
        provider_summary = "\n".join(f"• {value}" for value in providers) if providers else "• No explicit providers recorded"
        self.coverage_label.setText(
            f"CLASS MIX\n{class_summary}\n\nDECLARED PROVIDER RESPONSIBILITIES\n{provider_summary}"
        )

    def _send_to_roster(self, *_args) -> None:
        goal = self.goal_combo.currentText().strip() or "Custom Goal"
        plan_name = self.plan_name_input.text().strip() or f"{goal} Composition"
        slots: list[GeneratedRosterPlanSlot] = []
        for row in range(self.matrix_table.rowCount()):
            slot_name = self.matrix_table.item(row, 0).text()
            eso_class = self._selected_class(row)
            alternatives = self.matrix_table.item(row, 3).text()
            responsibilities = self.matrix_table.item(row, 4).text()
            providers = self.matrix_table.item(row, 5).text()
            detail = (
                f"Composition requirement. Alternatives: {alternatives}. "
                f"Responsibilities: {responsibilities}. Providers: {providers}."
            )
            concrete = eso_class != "Any class"
            slots.append(
                GeneratedRosterPlanSlot(
                    slot_name=slot_name,
                    kind="prescribed_recruit" if concrete else "open_recruit",
                    player_name="Recruitment Needed",
                    character_name="",
                    eso_class=eso_class,
                    build_name="Composition requirement",
                    gear_summary="",
                    unresolved=detail,
                )
            )

        plan = self.plan_service.save_plan(
            name=plan_name,
            goal=goal,
            difficulty=self.difficulty_combo.currentText(),
            slots=tuple(slots),
        )
        self.status.success(
            f"Sent {plan.name} to Roster with {len(plan.slots)} composition chair(s)."
        )
        self.rosterPlanSent.emit(plan.name)
