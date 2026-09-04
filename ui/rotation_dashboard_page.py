from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from minmax.rotation_plan import RotationPlan
from services.build_service import BuildService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


class RotationDashboardPage(FoundryPage):
    """Phase 13 rotation workspace for one saved character/build.

    The dashboard deliberately distinguishes saved-build facts from generated
    rotation evidence. Until a RotationPlan is supplied, timing/resource panels
    stay unresolved instead of manufacturing a plausible-looking parse.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.build_service = BuildService(get_data_dir() / "builds.json")
        self.roster = self.build_service.load()
        self.rotation_plan: RotationPlan | None = None
        self._build_ui()
        self._load_characters()
        self._refresh_build_context()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Rotation Dashboard",
            subtitle="Plan, inspect, and validate a saved build's combat sequence.",
            department="Raid Engine • Rotations",
        )
        self.set_header(self.header)

        self.character_combo = QComboBox()
        self.character_combo.setMinimumWidth(180)
        self.build_combo = QComboBox()
        self.build_combo.setMinimumWidth(210)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Semi-static", "Priority", "Encounter-aware"])
        self.mode_combo.setCurrentIndex(0)
        self.mode_combo.setEnabled(False)
        self.mode_combo.setToolTip("Additional rotation modes will unlock as Phase 13 scheduling is wired into this page.")

        self.header.add_context_widget(self._context_field("CHARACTER", self.character_combo))
        self.header.add_context_widget(self._context_field("BUILD", self.build_combo))
        self.header.add_context_widget(self._context_field("MODE", self.mode_combo))

        self.character_combo.currentIndexChanged.connect(self._character_changed)
        self.build_combo.currentIndexChanged.connect(self._refresh_build_context)

        workspace = QWidget()
        grid = QGridLayout(workspace)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)

        # Main timeline. No synthetic timings are displayed before a plan exists.
        timeline_card = FoundryCard("Rotation Timeline", "◇").set_watermark("compass", 0.035)
        self.timeline_table = QTableWidget(0, 5)
        self.timeline_table.setHorizontalHeaderLabels(["Time", "Bar", "Action", "Type", "State"])
        self.timeline_table.verticalHeader().setVisible(False)
        self.timeline_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.timeline_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.timeline_table.horizontalHeader().setStretchLastSection(True)
        self.timeline_table.setMinimumHeight(300)
        timeline_card.addWidget(self.timeline_table)
        self.timeline_hint = QLabel(
            "No generated rotation plan yet. Slotted abilities appear at right; timings remain unresolved until the Phase 13 planner supplies a RotationPlan."
        )
        self.timeline_hint.setWordWrap(True)
        self.timeline_hint.setProperty("muted", True)
        timeline_card.addWidget(self.timeline_hint)
        grid.addWidget(timeline_card, 0, 0)

        priority_card = FoundryCard("Ability Priority", "☷").set_watermark("compass", 0.035)
        self.priority_table = QTableWidget(0, 4)
        self.priority_table.setHorizontalHeaderLabels(["Bar", "Slot", "Ability", "Priority"])
        self.priority_table.verticalHeader().setVisible(False)
        self.priority_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.priority_table.horizontalHeader().setStretchLastSection(True)
        self.priority_table.setMinimumHeight(300)
        priority_card.addWidget(self.priority_table)
        grid.addWidget(priority_card, 0, 1)

        resource_card = FoundryCard("Resources & Ultimate", "◈").set_watermark("compass", 0.04)
        self.resource_summary = QLabel()
        self.resource_summary.setWordWrap(True)
        resource_card.addWidget(self.resource_summary)
        self.resource_detail = QLabel(
            "Sustain window, minimum resource, reserve protection, potion timing, and ultimate alignment will populate from evaluated rotation evidence."
        )
        self.resource_detail.setWordWrap(True)
        self.resource_detail.setProperty("muted", True)
        resource_card.addWidget(self.resource_detail)
        grid.addWidget(resource_card, 1, 0)

        consumables_card = FoundryCard("Food & Potions", "✦").make_parchment().set_watermark("feather", 0.08)
        self.food_value = self._value_label()
        self.potion_value = self._value_label()
        self.consumable_note = QLabel(
            "Uses the selected saved build. Rotation-specific suggestions will appear here only when optimization has evidence to support them."
        )
        self.consumable_note.setWordWrap(True)
        consumables_card.addWidget(self._labelled_value("FOOD", self.food_value))
        consumables_card.addWidget(self._labelled_value("POTION", self.potion_value))
        consumables_card.addWidget(self.consumable_note)
        grid.addWidget(consumables_card, 1, 1)

        notes_card = FoundryCard("Rotation Notes", "✎").make_parchment().set_watermark("feather", 0.08)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText(
            "Personal reminders, weave notes, execute changes, mechanic swaps, recovery rules..."
        )
        self.notes_edit.setMaximumHeight(105)
        notes_card.addWidget(self.notes_edit)
        grid.addWidget(notes_card, 2, 0)

        summary_card = FoundryCard("Build Summary", "◆").set_watermark("compass", 0.04)
        self.build_summary = QLabel()
        self.build_summary.setWordWrap(True)
        summary_card.addWidget(self.build_summary)
        grid.addWidget(summary_card, 2, 1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        self.generate_button = QPushButton("Generate Rotation")
        self.generate_button.setProperty("primary", True)
        self.generate_button.setEnabled(False)
        self.generate_button.setToolTip(
            "The dashboard is ready; generator wiring will enable this when the Phase 13 planner owns a real saved-build schedule."
        )
        self.clear_plan_button = QPushButton("Clear Plan")
        self.clear_plan_button.clicked.connect(self.clear_rotation_plan)
        action_row.addWidget(self.generate_button)
        action_row.addWidget(self.clear_plan_button)
        action_row.addStretch()
        grid.addLayout(action_row, 3, 0, 1, 2)

        self.add_workspace(workspace)
        self.status = FoundryStatusBar()
        self.set_status(self.status)

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

    @staticmethod
    def _value_label() -> QLabel:
        label = QLabel("—")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setWordWrap(True)
        return label

    @staticmethod
    def _labelled_value(title: str, value: QLabel) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        heading = QLabel(title)
        heading.setProperty("sidebarHeading", True)
        layout.addWidget(heading)
        layout.addWidget(value)
        return box

    @staticmethod
    def _character_name(build) -> str:
        return str(
            getattr(build, "CharacterName", "")
            or getattr(build, "Name", "")
            or getattr(build, "Gamertag", "")
            or "Unnamed Character"
        ).strip()

    @staticmethod
    def _build_name(build) -> str:
        return str(getattr(build, "BuildName", "") or "Current Build").strip()

    def _load_characters(self) -> None:
        self.character_combo.blockSignals(True)
        self.character_combo.clear()
        seen: set[str] = set()
        for build in self.roster.Members:
            name = self._character_name(build)
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            self.character_combo.addItem(name, name)
        self.character_combo.blockSignals(False)
        self._character_changed()

    def _character_changed(self) -> None:
        character = str(self.character_combo.currentData() or "")
        self.build_combo.blockSignals(True)
        self.build_combo.clear()
        for index, build in enumerate(self.roster.Members):
            if self._character_name(build) != character:
                continue
            self.build_combo.addItem(self._build_name(build), index)
        self.build_combo.blockSignals(False)
        self.clear_rotation_plan(refresh=False)
        self._refresh_build_context()

    def _selected_build(self):
        index = self.build_combo.currentData()
        if not isinstance(index, int) or not (0 <= index < len(self.roster.Members)):
            return None
        return self.roster.Members[index]

    @staticmethod
    def _clean_skills(values) -> list[tuple[int, str]]:
        return [
            (slot, str(name).strip())
            for slot, name in enumerate(list(values or []), start=1)
            if str(name or "").strip()
        ]

    def _refresh_build_context(self) -> None:
        build = self._selected_build()
        self.priority_table.setRowCount(0)

        if build is None:
            self.food_value.setText("—")
            self.potion_value.setText("—")
            self.build_summary.setText("No saved build selected.")
            self.resource_summary.setText("Rotation evidence: unavailable")
            self.status.warning("No saved build is available for the selected character.")
            return

        for bar_name, skills in (
            ("Front", getattr(build, "FrontBarSkills", [])),
            ("Back", getattr(build, "BackBarSkills", [])),
        ):
            for slot, skill in self._clean_skills(skills):
                row = self.priority_table.rowCount()
                self.priority_table.insertRow(row)
                values = (bar_name, str(slot), skill, "Unranked")
                for column, value in enumerate(values):
                    self.priority_table.setItem(row, column, QTableWidgetItem(value))

        self.food_value.setText(str(getattr(build, "Food", "") or "Not selected"))
        self.potion_value.setText(str(getattr(build, "Potion", "") or "Not selected"))

        character = self._character_name(build)
        build_name = self._build_name(build)
        role = str(getattr(build, "Role", "") or "Unspecified")
        eso_class = str(getattr(build, "EsoClass", "") or "Unspecified")
        race = str(getattr(build, "Race", "") or "Unspecified")
        mundus = str(getattr(build, "Mundus", "") or "Unspecified")
        front_count = len(self._clean_skills(getattr(build, "FrontBarSkills", [])))
        back_count = len(self._clean_skills(getattr(build, "BackBarSkills", [])))

        self.build_summary.setText(
            f"{character} • {build_name}\n"
            f"{eso_class} • {race} • {role}\n"
            f"Mundus: {mundus}\n"
            f"Slotted abilities: {front_count} front / {back_count} back"
        )
        self.resource_summary.setText(
            "Rotation evidence: awaiting generated plan\n"
            "Resource budget: unresolved\n"
            "Ultimate timing: unresolved"
        )
        if self.rotation_plan is None:
            self.status.info(f"Loaded saved build: {character} • {build_name}.")

    def set_rotation_plan(self, plan: RotationPlan) -> None:
        """Render one authoritative Phase 13 plan without reinterpreting it."""
        self.rotation_plan = plan
        self.timeline_table.setRowCount(0)
        for action in plan.actions:
            row = self.timeline_table.rowCount()
            self.timeline_table.insertRow(row)
            values = (
                f"{action.time_seconds:.1f}s",
                (action.bar or "—").title(),
                action.name or action.kind.value.replace("_", " ").title(),
                action.kind.value.replace("_", " ").title(),
                "Scheduled",
            )
            for column, value in enumerate(values):
                self.timeline_table.setItem(row, column, QTableWidgetItem(value))

        self.timeline_hint.setText(
            f"{len(plan.actions)} scheduled action(s) across {plan.duration_seconds:g}s. "
            f"Unresolved: {len(plan.unresolved)}. Assumptions: {len(plan.assumptions)}."
        )
        self.resource_summary.setText(
            "Rotation schedule loaded. Resource and ultimate consequence panels remain unresolved until evaluated evidence is supplied."
        )
        if plan.unresolved:
            self.status.warning(
                f"Rotation plan loaded with {len(plan.unresolved)} unresolved item(s)."
            )
        else:
            self.status.success("Rotation plan loaded with no schedule-level unresolved items.")

    def clear_rotation_plan(self, *, refresh: bool = True) -> None:
        self.rotation_plan = None
        if hasattr(self, "timeline_table"):
            self.timeline_table.setRowCount(0)
            self.timeline_hint.setText(
                "No generated rotation plan yet. Slotted abilities appear at right; timings remain unresolved until the Phase 13 planner supplies a RotationPlan."
            )
        if refresh and hasattr(self, "build_summary"):
            self._refresh_build_context()
