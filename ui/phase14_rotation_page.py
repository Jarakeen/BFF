from __future__ import annotations

"""Phase 14 Rotation Builder.

A deliberately owned UI boundary over the existing rotation engine. This page does
not import, instantiate, decorate, or monkey-patch the legacy Rotation Dashboard.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.build_service import BuildService
from services.rotation_sustain_service import RotationSustainService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationSupport,
)


def _clean(value: object) -> str:
    return str(value or "").strip()


class RotationBuilderPage(FoundryPage):
    """Stable Phase 14 front end for the canonical rotation services."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.build_service = BuildService(get_data_dir() / "builds.json")
        self.rotation_generation = RotationGenerationSupport()
        self.rotation_sustain = RotationSustainService(get_data_dir() / "eso.db")
        self.roster = self.build_service.load()
        self.rotation_plan: RotationPlan | None = None

        self._build_ui()
        self.refresh_saved_builds()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Rotation Builder",
            subtitle="Build the schedule first. Add cleverness only when the evidence earns it.",
            department="RAID ENGINE • ROTATION",
            icon="rotation",
        )
        self.set_header(self.header)

        self.character_combo = QComboBox()
        self.character_combo.setMinimumWidth(190)
        self.character_combo.currentIndexChanged.connect(self._character_changed)
        self.header.add_context_widget(self._context_field("CHARACTER", self.character_combo))

        self.build_combo = QComboBox()
        self.build_combo.setMinimumWidth(220)
        self.build_combo.currentIndexChanged.connect(self._build_changed)
        self.header.add_context_widget(self._context_field("BUILD", self.build_combo))

        refresh = QPushButton("Refresh Builds")
        refresh.clicked.connect(self.refresh_saved_builds)
        self.header.add_context_widget(refresh)

        top = QGridLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setHorizontalSpacing(8)
        top.setVerticalSpacing(8)
        top.setColumnStretch(0, 3)
        top.setColumnStretch(1, 2)

        build_card = FoundryCard("Build Context", "builds")
        self.build_summary = QLabel("No saved build selected.")
        self.build_summary.setWordWrap(True)
        build_card.addWidget(self.build_summary)

        self.front_skills = QLabel("Front: —")
        self.front_skills.setWordWrap(True)
        self.front_skills.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        build_card.addWidget(self.front_skills)

        self.back_skills = QLabel("Back: —")
        self.back_skills.setWordWrap(True)
        self.back_skills.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        build_card.addWidget(self.back_skills)
        top.addWidget(build_card, 0, 0)

        generation_card = FoundryCard("Generation", "cog")
        generation_grid = QGridLayout()
        generation_grid.setContentsMargins(0, 0, 0, 0)
        generation_grid.setHorizontalSpacing(8)
        generation_grid.setVerticalSpacing(6)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(15, 300)
        self.duration_spin.setValue(60)
        self.duration_spin.setSuffix(" s")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Semi-static", "Semi-static")
        self.mode_combo.setToolTip(
            "Phase 14 starts with the engine's currently supported deterministic semi-static planner."
        )

        self.resource_combo = QComboBox()
        self.resource_combo.addItem("Magicka", ResourceType.MAGICKA.value)
        self.resource_combo.addItem("Stamina", ResourceType.STAMINA.value)

        self.weave_check = QCheckBox("Light-attack weave")
        self.weave_check.setChecked(True)
        self.weave_check.setToolTip(
            "Schedules the engine's LA + skill weave model. It does not insert a separate one-second LA gap."
        )

        self.ultimate_combo = QComboBox()
        self.ultimate_combo.addItem("Do not schedule Ultimate", "")

        generation_grid.addWidget(self._field_label("DURATION"), 0, 0)
        generation_grid.addWidget(self._field_label("PLANNER"), 0, 1)
        generation_grid.addWidget(self.duration_spin, 1, 0)
        generation_grid.addWidget(self.mode_combo, 1, 1)
        generation_grid.addWidget(self._field_label("SUSTAIN"), 2, 0)
        generation_grid.addWidget(self._field_label("ULTIMATE"), 2, 1)
        generation_grid.addWidget(self.resource_combo, 3, 0)
        generation_grid.addWidget(self.ultimate_combo, 3, 1)
        generation_grid.addWidget(self.weave_check, 4, 0, 1, 2)
        generation_card.addLayout(generation_grid)

        self.generate_button = QPushButton("Generate Rotation")
        self.generate_button.setProperty("primary", True)
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self.generate_rotation)
        generation_card.addWidget(self.generate_button)
        top.addWidget(generation_card, 0, 1)

        self.workspace_layout.addLayout(top)

        timeline_card = FoundryCard("Rotation Timeline", "hourglass")
        self.timeline_table = QTableWidget(0, 6)
        self.timeline_table.setHorizontalHeaderLabels(
            ["Time", "Bar", "Action", "Type", "Target", "Sequence"]
        )
        self.timeline_table.verticalHeader().setVisible(False)
        self.timeline_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.timeline_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.timeline_table.horizontalHeader().setStretchLastSection(True)
        self.timeline_table.setMinimumHeight(330)
        timeline_card.addWidget(self.timeline_table)
        self.timeline_hint = QLabel(
            "Select a saved build and generate. Nothing is fabricated before the engine returns a plan."
        )
        self.timeline_hint.setWordWrap(True)
        self.timeline_hint.setProperty("muted", True)
        timeline_card.addWidget(self.timeline_hint)
        self.workspace_layout.addWidget(timeline_card)

        lower = QHBoxLayout()
        lower.setContentsMargins(0, 0, 0, 0)
        lower.setSpacing(8)

        evidence_card = FoundryCard("Engine Evidence", "binoculars")
        self.evidence_label = QLabel(
            "Assumptions and unresolved engine facts will appear after generation."
        )
        self.evidence_label.setWordWrap(True)
        self.evidence_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        evidence_card.addWidget(self.evidence_label)
        lower.addWidget(evidence_card, 3)

        sustain_card = FoundryCard("Sustain Snapshot", "drop")
        self.sustain_label = QLabel("Awaiting a generated rotation.")
        self.sustain_label.setWordWrap(True)
        self.sustain_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sustain_card.addWidget(self.sustain_label)
        lower.addWidget(sustain_card, 2)

        notes_card = FoundryCard("Personal Notes", "feather")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText(
            "Execution reminders only. Notes do not alter engine evidence."
        )
        self.notes_edit.setMaximumHeight(120)
        notes_card.addWidget(self.notes_edit)
        lower.addWidget(notes_card, 2)

        self.workspace_layout.addLayout(lower)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    @staticmethod
    def _context_field(title: str, widget: QWidget) -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return host

    @staticmethod
    def _field_label(title: str) -> QLabel:
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        return label

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
        return [
            _clean(value)
            for value in list(values or [])[:5]
            if _clean(value)
        ]

    @staticmethod
    def _ultimate(values) -> str:
        skills = list(values or [])
        return _clean(skills[5]) if len(skills) > 5 else ""

    def refresh_saved_builds(self) -> None:
        selected_character = _clean(self.character_combo.currentData())
        selected_build = _clean(self.build_combo.currentText())

        self.roster = self.build_service.load()
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

        if not self.roster.Members:
            self.status.warning("No saved builds are available for Rotation Builder.")

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
        self._build_changed()

    def _selected_build(self):
        index = self.build_combo.currentData()
        if not isinstance(index, int):
            return None
        if not 0 <= index < len(self.roster.Members):
            return None
        return self.roster.Members[index]

    def _build_changed(self, *_args) -> None:
        self.clear_result()
        build = self._selected_build()
        self.ultimate_combo.blockSignals(True)
        self.ultimate_combo.clear()
        self.ultimate_combo.addItem("Do not schedule Ultimate", "")

        if build is None:
            self.ultimate_combo.blockSignals(False)
            self.build_summary.setText("No saved build selected.")
            self.front_skills.setText("Front: —")
            self.back_skills.setText("Back: —")
            self.generate_button.setEnabled(False)
            return

        front = self._ordinary_skills(getattr(build, "FrontBarSkills", []))
        back = self._ordinary_skills(getattr(build, "BackBarSkills", []))
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
            f"{eso_class} · {race} · {role}\n"
            f"Food: {food}\nPotion: {potion}"
        )
        self.front_skills.setText("Front: " + (" · ".join(front) if front else "No ordinary skills"))
        self.back_skills.setText("Back: " + (" · ".join(back) if back else "No ordinary skills"))
        self.generate_button.setEnabled(bool(front or back))
        self.status.info(
            f"Loaded {self._character_name(build)} · {self._build_name(build)}."
        )

    def generate_rotation(self) -> None:
        build = self._selected_build()
        if build is None:
            self.status.warning("Select a saved build before generating a rotation.")
            return

        request = RotationGenerationRequest(
            duration_seconds=float(self.duration_spin.value()),
            rotation_type=str(self.mode_combo.currentData() or "Semi-static"),
            potion=_clean(getattr(build, "Potion", "")),
            potion_on_cooldown=False,
            weave_light_attacks=self.weave_check.isChecked(),
            ultimate_bar=_clean(self.ultimate_combo.currentData()),
            starting_ultimate=0.0,
            use_scheduled_combat_attacks_for_ultimate=self.weave_check.isChecked(),
        )

        try:
            result = self.rotation_generation.generate_with_evidence(
                build=build,
                request=request,
            )
        except Exception as exc:
            self.clear_result()
            self.status.error(f"Rotation generation failed: {exc}")
            return

        self.rotation_plan = result.plan
        self._render_plan(result.plan)
        self._render_evidence(result.plan)
        self._evaluate_sustain(build, result.plan)
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
            "\n\n".join(sections) or "No assumptions or unresolved evidence were reported."
        )

    def _evaluate_sustain(self, build, plan: RotationPlan) -> None:
        try:
            resource = ResourceType(str(self.resource_combo.currentData()))
            projection = self.rotation_sustain.evaluate(
                build=build,
                plan=plan,
                resource=resource,
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
        resource_name = projection.resource.value.title()

        lines = [
            resource_name,
            f"Start: {start:g}" if start is not None else "Start: —",
            f"Minimum: {minimum:g}" if minimum is not None else "Minimum: —",
            f"End: {end:g}" if end is not None else "End: —",
        ]
        if projection.unresolved:
            lines.append("")
            lines.append("Needs review:")
            lines.extend(f"• {item}" for item in projection.unresolved[:6])
        self.sustain_label.setText("\n".join(lines))

    def clear_result(self) -> None:
        self.rotation_plan = None
        if hasattr(self, "timeline_table"):
            self.timeline_table.setRowCount(0)
        if hasattr(self, "timeline_hint"):
            self.timeline_hint.setText(
                "Select a saved build and generate. Nothing is fabricated before the engine returns a plan."
            )
        if hasattr(self, "evidence_label"):
            self.evidence_label.setText(
                "Assumptions and unresolved engine facts will appear after generation."
            )
        if hasattr(self, "sustain_label"):
            self.sustain_label.setText("Awaiting a generated rotation.")


__all__ = ["RotationBuilderPage"]
