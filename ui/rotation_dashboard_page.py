from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
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
from minmax.rotation_plan import RotationPlan
from services.build_service import BuildService
from services.rotation_sustain_service import RotationSustainProjection, RotationSustainService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationSupport,
)


class SustainGraph(QWidget):
    """Compact 60-second sustain graph that renders only supplied evidence."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: tuple[tuple[float, float], ...] = ()
        self.setMinimumHeight(210)
        self.setToolTip("60-second resource projection from evaluated rotation evidence.")

    def set_points(self, points) -> None:
        cleaned: list[tuple[float, float]] = []
        for time_seconds, value in points or ():
            time_value = max(0.0, min(60.0, float(time_seconds)))
            cleaned.append((time_value, float(value)))
        self._points = tuple(sorted(cleaned))
        self.update()

    def clear_points(self) -> None:
        self._points = ()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        palette = self.palette()
        text_color = palette.color(self.foregroundRole())
        muted = QColor(text_color)
        muted.setAlpha(120)
        grid_color = QColor(text_color)
        grid_color.setAlpha(45)
        line_color = QColor(184, 154, 91)

        rect = QRectF(self.rect()).adjusted(44, 14, -14, -30)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        painter.setPen(QPen(grid_color, 1))
        for second in (0, 15, 30, 45, 60):
            x = rect.left() + rect.width() * (second / 60.0)
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            painter.setPen(muted)
            painter.drawText(QRectF(x - 18, rect.bottom() + 5, 36, 18), Qt.AlignmentFlag.AlignCenter, f"{second}s")
            painter.setPen(QPen(grid_color, 1))

        for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = rect.bottom() - rect.height() * fraction
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

        if not self._points:
            painter.setPen(muted)
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                "Awaiting evaluated 60s sustain evidence",
            )
            return

        values = [value for _, value in self._points]
        low = min(values)
        high = max(values)
        if high <= low:
            high = low + 1.0

        path = QPainterPath()
        for index, (time_seconds, value) in enumerate(self._points):
            x = rect.left() + rect.width() * (time_seconds / 60.0)
            y = rect.bottom() - rect.height() * ((value - low) / (high - low))
            point = QPointF(x, y)
            if index == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)

        painter.setPen(QPen(line_color, 2))
        painter.drawPath(path)
        painter.setPen(muted)
        painter.drawText(QRectF(0, rect.top() - 2, 40, 18), Qt.AlignmentFlag.AlignRight, f"{high:g}")
        painter.drawText(QRectF(0, rect.bottom() - 14, 40, 18), Qt.AlignmentFlag.AlignRight, f"{low:g}")


class RotationDashboardPage(FoundryPage):
    """Phase 13 rotation workspace for one saved character/build.

    Saved-build facts can be configured here immediately. Generated timing and
    sustain evidence is rendered only after the rotation engine supplies it.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.build_service = BuildService(get_data_dir() / "builds.json")
        self.roster = self.build_service.load()
        self.rotation_generation = RotationGenerationSupport()
        self.rotation_sustain = RotationSustainService()
        self.rotation_plan: RotationPlan | None = None
        self._build_ui()
        self._load_characters()
        self._refresh_build_context()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Rotation Dashboard",
            subtitle="Generate, inspect, and tune a saved build's combat sequence.",
            department="Raid Engine • Rotations",
        )
        self.set_header(self.header)

        self.character_combo = QComboBox()
        self.character_combo.setMinimumWidth(180)
        self.build_combo = QComboBox()
        self.build_combo.setMinimumWidth(210)
        self.header.add_context_widget(self._context_field("CHARACTER", self.character_combo))
        self.header.add_context_widget(self._context_field("BUILD", self.build_combo))

        self.character_combo.currentIndexChanged.connect(self._character_changed)
        self.build_combo.currentIndexChanged.connect(self._refresh_build_context)

        workspace = QWidget()
        grid = QGridLayout(workspace)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)

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
            "No generated rotation plan yet. Timings stay unresolved until the Phase 13 planner supplies a RotationPlan."
        )
        self.timeline_hint.setWordWrap(True)
        self.timeline_hint.setProperty("muted", True)
        timeline_card.addWidget(self.timeline_hint)
        grid.addWidget(timeline_card, 0, 0)

        priority_card = FoundryCard("Ability Priority List", "☷").set_watermark("compass", 0.035)
        self.priority_table = QTableWidget(0, 4)
        self.priority_table.setHorizontalHeaderLabels(["Bar", "Slot", "Ability", "Priority"])
        self.priority_table.verticalHeader().setVisible(False)
        self.priority_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.priority_table.horizontalHeader().setStretchLastSection(True)
        self.priority_table.setMinimumHeight(300)
        priority_card.addWidget(self.priority_table)
        grid.addWidget(priority_card, 0, 1)

        sustain_card = FoundryCard("Sustain over 60s", "◈").set_watermark("compass", 0.04)
        self.sustain_graph = SustainGraph()
        sustain_card.addWidget(self.sustain_graph)
        self.resource_summary = QLabel()
        self.resource_summary.setWordWrap(True)
        sustain_card.addWidget(self.resource_summary)
        self.resource_detail = QLabel(
            "Minimum resource, reserve protection, potion timing, and ultimate alignment populate from evaluated rotation evidence."
        )
        self.resource_detail.setWordWrap(True)
        self.resource_detail.setProperty("muted", True)
        sustain_card.addWidget(self.resource_detail)
        grid.addWidget(sustain_card, 1, 0)

        settings_card = FoundryCard("Rotation Setup", "◆").set_watermark("compass", 0.035)
        settings_grid = QGridLayout()
        settings_grid.setContentsMargins(0, 0, 0, 0)
        settings_grid.setHorizontalSpacing(8)
        settings_grid.setVerticalSpacing(6)

        self.execute_spin = QSpinBox()
        self.execute_spin.setRange(0, 100)
        self.execute_spin.setValue(25)
        self.execute_spin.setSuffix("%")

        self.rotation_type_combo = QComboBox()
        self.rotation_type_combo.addItems(["Static", "Semi-static", "Dynamic"])
        self.rotation_type_combo.setCurrentText("Semi-static")
        self.rotation_type_combo.currentTextChanged.connect(self._refresh_generate_button)

        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(["Single Target", "AoE"])

        self.potion_combo = QComboBox()
        self.potion_combo.setEditable(True)
        self.potion_combo.setMinimumContentsLength(18)

        self.potion_on_cooldown = QCheckBox("Use potion on cooldown")
        self.potion_on_cooldown.setChecked(True)

        settings_grid.addWidget(self._field_label("EXECUTE STARTS"), 0, 0)
        settings_grid.addWidget(self.execute_spin, 1, 0)
        settings_grid.addWidget(self._field_label("ROTATION TYPE"), 0, 1)
        settings_grid.addWidget(self.rotation_type_combo, 1, 1)
        settings_grid.addWidget(self._field_label("TARGET TYPE"), 2, 0)
        settings_grid.addWidget(self.target_type_combo, 3, 0)
        settings_grid.addWidget(self._field_label("POTION"), 2, 1)
        settings_grid.addWidget(self.potion_combo, 3, 1)
        settings_grid.addWidget(self.potion_on_cooldown, 4, 0, 1, 2)
        settings_card.addLayout(settings_grid)
        grid.addWidget(settings_card, 1, 1)

        notes_card = FoundryCard("Rotation Notes", "✎").set_watermark("feather", 0.05)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText(
            "Personal reminders, weave notes, execute changes, mechanic swaps, recovery rules..."
        )
        self.notes_edit.setMaximumHeight(95)
        notes_card.addWidget(self.notes_edit)
        grid.addWidget(notes_card, 2, 0)

        right_lower = QWidget()
        right_lower_layout = QGridLayout(right_lower)
        right_lower_layout.setContentsMargins(0, 0, 0, 0)
        right_lower_layout.setHorizontalSpacing(8)
        right_lower_layout.setVerticalSpacing(8)

        consumables_card = FoundryCard("Food & Potions", "✦").set_watermark("feather", 0.035)
        consumables_card.setMaximumHeight(150)
        self.food_value = self._value_label()
        self.potion_value = self._value_label()
        consumables_card.addWidget(self._labelled_value("FOOD", self.food_value))
        consumables_card.addWidget(self._labelled_value("SAVED POTION", self.potion_value))
        right_lower_layout.addWidget(consumables_card, 0, 0)

        summary_card = FoundryCard("Build Summary", "◆").set_watermark("compass", 0.04)
        self.build_summary = QLabel()
        self.build_summary.setWordWrap(True)
        summary_card.addWidget(self.build_summary)
        self.optimization_scope = QLabel(
            "Optimization scope: Rotation generation starts with the currently saved build as-is. "
            "Gear, skill morphs, Champion Points, Mundus, food, and potion changes are separate opt-in optimization dimensions."
        )
        self.optimization_scope.setWordWrap(True)
        self.optimization_scope.setProperty("muted", True)
        summary_card.addWidget(self.optimization_scope)
        self.optimization_motto = QLabel(
            "We make you better, because you're perfect just the way you are."
        )
        self.optimization_motto.setWordWrap(True)
        self.optimization_motto.setProperty("muted", True)
        summary_card.addWidget(self.optimization_motto)
        right_lower_layout.addWidget(summary_card, 1, 0)
        grid.addWidget(right_lower, 2, 1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        self.generate_button = QPushButton("Generate Rotation")
        self.generate_button.setProperty("primary", True)
        self.generate_button.setEnabled(False)
        self.generate_button.setToolTip(
            "Generate the first deterministic 60-second semi-static schedule from the selected saved build."
        )
        self.generate_button.clicked.connect(self.generate_rotation)
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
    def _field_label(title: str) -> QLabel:
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        return label

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

    def _refresh_generate_button(self) -> None:
        build = self._selected_build()
        supported_mode = self.rotation_type_combo.currentText() == "Semi-static"
        has_ordinary_skill = False
        if build is not None:
            has_ordinary_skill = bool(
                self._clean_skills(list(getattr(build, "FrontBarSkills", []) or [])[:5])
                or self._clean_skills(list(getattr(build, "BackBarSkills", []) or [])[:5])
            )
        self.generate_button.setEnabled(bool(build is not None and supported_mode and has_ordinary_skill))

    def _refresh_build_context(self) -> None:
        build = self._selected_build()
        self.priority_table.setRowCount(0)

        if build is None:
            self.food_value.setText("—")
            self.potion_value.setText("—")
            self.potion_combo.clear()
            self.build_summary.setText("No saved build selected.")
            self.resource_summary.setText("Rotation evidence: unavailable")
            self.sustain_graph.clear_points()
            self.generate_button.setEnabled(False)
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

        food = str(getattr(build, "Food", "") or "Not selected")
        potion = str(getattr(build, "Potion", "") or "Not selected")
        self.food_value.setText(food)
        self.potion_value.setText(potion)
        self.potion_combo.blockSignals(True)
        self.potion_combo.clear()
        if potion != "Not selected":
            self.potion_combo.addItem(potion)
        self.potion_combo.addItem("None")
        if potion != "Not selected":
            self.potion_combo.setCurrentText(potion)
        self.potion_combo.blockSignals(False)

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
            "60s resource curve: unresolved\n"
            "Ultimate timing: unresolved"
        )
        self.sustain_graph.clear_points()
        self._refresh_generate_button()
        if self.rotation_plan is None:
            self.status.info(f"Loaded saved build: {character} • {build_name}.")

    def generate_rotation(self) -> None:
        """Generate and evaluate the first authoritative semi-static schedule."""
        build = self._selected_build()
        if build is None:
            self.status.warning("Select a saved build before generating a rotation.")
            return

        settings = self.rotation_settings()
        request = RotationGenerationRequest(
            duration_seconds=60.0,
            rotation_type=str(settings["rotation_type"]),
            potion=str(settings["potion"]),
            potion_on_cooldown=bool(settings["potion_on_cooldown"]),
            weave_light_attacks=True,
        )

        try:
            plan = self.rotation_generation.generate(build=build, request=request)
        except ValueError as exc:
            self.status.warning(str(exc))
            return

        self.set_rotation_plan(plan)

        try:
            projection = self.rotation_sustain.evaluate(
                build=build,
                plan=plan,
                resource=ResourceType.MAGICKA,
            )
        except (OSError, ValueError) as exc:
            self.sustain_graph.clear_points()
            self.resource_summary.setText(
                "Rotation schedule loaded. Magicka sustain evaluation could not be completed."
            )
            self.resource_detail.setText(str(exc))
            self.status.warning(f"Rotation generated; sustain evaluation unavailable: {exc}")
            return

        self.set_sustain_projection(projection)

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
            "Rotation schedule loaded. Evaluating 60s Magicka sustain through the Phase 4 resource engine."
        )
        if plan.unresolved:
            self.status.warning(
                f"Rotation plan loaded with {len(plan.unresolved)} unresolved item(s)."
            )
        else:
            self.status.success("Rotation plan loaded with no schedule-level unresolved items.")

    def set_sustain_projection(self, projection: RotationSustainProjection) -> None:
        """Render the authoritative Phase 4 sustain result for the generated plan."""
        self.set_sustain_series(projection.series)
        sustain = projection.run.sustain
        state = "SUSTAINS" if sustain.sustains else "FAILS"
        self.resource_summary.setText(
            f"Magicka sustain: {state}\n"
            f"Start: {sustain.starting_amount:,} • Minimum: {sustain.minimum_amount:,} • "
            f"End: {sustain.ending_amount:,}\n"
            f"Cost attempted: {sustain.total_cost_attempted:,} • Cost paid: {sustain.total_cost_paid:,}"
        )

        details = [
            f"Resolved cost events: {len(projection.run.action_cost_events)}",
            f"Recovery ticks: {len(projection.run.recovery_ticks)}",
            f"Unresolved evidence: {len(projection.unresolved)}",
        ]
        if sustain.first_failure is not None:
            failure = sustain.first_failure
            details.append(
                f"First failure: {failure.time_seconds:g}s • {failure.source} • "
                f"shortfall {failure.shortfall:,}"
            )
        elif projection.unresolved:
            details.append("Some temporal/runtime mechanics remain explicitly unresolved.")
        else:
            details.append("No sustain-level unresolved evidence reported.")
        self.resource_detail.setText("\n".join(details))

        if not sustain.sustains:
            self.status.warning(
                "Rotation generated; the modeled 60-second Magicka timeline does not sustain."
            )
        elif projection.unresolved:
            self.status.warning(
                f"Rotation generated and sustains with {len(projection.unresolved)} unresolved item(s)."
            )
        else:
            self.status.success("Rotation generated and sustains with no unresolved sustain evidence.")

    def set_sustain_series(self, points) -> None:
        """Render evaluated resource evidence as (time_seconds, resource_value) pairs."""
        self.sustain_graph.set_points(points)

    def rotation_settings(self) -> dict[str, object]:
        """Return the current user-selected generation controls without guessing semantics."""
        return {
            "execute_percent": int(self.execute_spin.value()),
            "rotation_type": self.rotation_type_combo.currentText(),
            "target_type": self.target_type_combo.currentText(),
            "potion": self.potion_combo.currentText().strip(),
            "potion_on_cooldown": self.potion_on_cooldown.isChecked(),
        }

    def clear_rotation_plan(self, *, refresh: bool = True) -> None:
        self.rotation_plan = None
        if hasattr(self, "timeline_table"):
            self.timeline_table.setRowCount(0)
            self.timeline_hint.setText(
                "No generated rotation plan yet. Timings stay unresolved until the Phase 13 planner supplies a RotationPlan."
            )
        if hasattr(self, "sustain_graph"):
            self.sustain_graph.clear_points()
        if refresh and hasattr(self, "build_summary"):
            self._refresh_build_context()
