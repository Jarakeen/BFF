from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from minmax.optimization_mode import OptimizationMode, policy_for_mode
from minmax.recruitment import RecruitmentPlanner
from models.build_model import BuildRoster
from services.build_service import BuildService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


class OptimizationPage(FoundryPage):
    """Raid Engine team-building and optimization workspace."""

    _MODE_ORDER = (
        OptimizationMode.AUDIT,
        OptimizationMode.BUILD,
        OptimizationMode.RECRUIT,
        OptimizationMode.COMPARE,
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.build_service = BuildService(get_data_dir() / "builds.json")
        self.recruitment_planner = RecruitmentPlanner()
        self.roster = BuildRoster()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Team Optimization",
            subtitle="Build the best team for your goal. Optimize roles, builds, gear, and coverage.",
            department="Raid Engine • Team Builder",
        )
        self.set_header(self.header)

        self.goal_combo = QComboBox()
        self.goal_combo.addItems([
            "Swashbuckler Supreme",
            "Godslayer",
            "Gryphon Heart",
            "Hurricane Herald",
            "Planebreaker",
            "Custom Goal",
        ])
        self.header.add_context_widget(self._context_field("GOAL", self.goal_combo))

        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["Veteran Hardmode", "Veteran", "Normal"])
        self.header.add_context_widget(self._context_field("DIFFICULTY", self.difficulty_combo))

        self.group_size_combo = QComboBox()
        self.group_size_combo.addItems(["12 Players", "4 Players"])
        self.group_size_combo.currentTextChanged.connect(self._generate_preview)
        self.header.add_context_widget(self._context_field("GROUP SIZE", self.group_size_combo))

        self.team_source_combo = QComboBox()
        self.team_source_combo.addItems([
            "Saved Players Only",
            "Hybrid: Players + Recruitment",
            "Recruitment Plan Only",
        ])
        self.team_source_combo.setCurrentText("Hybrid: Players + Recruitment")
        self.team_source_combo.currentTextChanged.connect(self._team_source_changed)
        self.header.add_context_widget(self._context_field("TEAM SOURCE", self.team_source_combo))

        self.workspace = QWidget()
        self.layout = QVBoxLayout(self.workspace)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        self.add_workspace(self.workspace)

        self._build_mode_tabs()
        self._build_constraints()
        self._build_main_row()
        self._build_recommendations_row()

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

    def _build_mode_tabs(self) -> None:
        self.mode_tabs = QTabBar()
        self.mode_tabs.setExpanding(False)
        self.mode_tabs.setDrawBase(True)
        self.mode_tabs.setUsesScrollButtons(False)
        for mode in self._MODE_ORDER:
            self.mode_tabs.addTab(policy_for_mode(mode).title)
        self.mode_tabs.setCurrentIndex(self._MODE_ORDER.index(OptimizationMode.BUILD))
        self.mode_tabs.currentChanged.connect(self._optimization_mode_changed)
        self.layout.addWidget(self.mode_tabs)

    def _current_mode(self) -> OptimizationMode:
        index = self.mode_tabs.currentIndex()
        if 0 <= index < len(self._MODE_ORDER):
            return self._MODE_ORDER[index]
        return OptimizationMode.BUILD

    def _effective_source_mode(self) -> str:
        mode = self._current_mode()
        if mode is OptimizationMode.AUDIT:
            return "Saved Players Only"
        if mode is OptimizationMode.RECRUIT:
            return "Recruitment Plan Only"
        return self.team_source_combo.currentText()

    def _optimization_mode_changed(self, _index: int) -> None:
        mode = self._current_mode()
        policy = policy_for_mode(mode)
        comparing = policy.uses_two_teams

        self.team_source_combo.setEnabled(
            mode in (OptimizationMode.BUILD, OptimizationMode.COMPARE)
        )
        if hasattr(self, "team_tabs"):
            self.team_tabs.setTabEnabled(1, comparing)
            if not comparing:
                self.team_tabs.setCurrentIndex(0)
        if hasattr(self, "generate_button"):
            self.generate_button.setText(policy.action_label)

        if hasattr(self, "team_table"):
            self._populate_team_editor(self.team_table, autofill=True)
            self._populate_team_editor(self.team_b_table, autofill=True)
            self._update_team_analysis()

    def _build_constraints(self):
        card = FoundryCard("Constraints")
        row = QHBoxLayout()
        row.setSpacing(18)
        for text, checked in (
            ("Lock Players", False),
            ("Lock Roles", False),
            ("Lock Classes", False),
            ("Keep Current Builds", True),
            ("Allow Role Swap", True),
            ("Allow Gear Changes", True),
        ):
            box = QCheckBox(text)
            box.setChecked(checked)
            row.addWidget(box)
        row.addStretch(1)
        self.generate_button = QPushButton("Generate Best Team")
        self.generate_button.setProperty("primary", True)
        self.generate_button.clicked.connect(self._generate_preview)
        row.addWidget(self.generate_button)
        card.addLayout(row)
        self.layout.addWidget(card)

    def _build_main_row(self):
        row = QHBoxLayout()
        row.setSpacing(10)

        self.available_card = FoundryCard("Available Players")
        self.available_search = QLineEdit()
        self.available_search.setPlaceholderText("Search players...")
        self.available_search.textChanged.connect(self._filter_available)
        self.available_table = QTableWidget(0, 5)
        self.available_table.setHorizontalHeaderLabels(["PLAYER", "CLASS", "ROLES", "BUILDS", "READY"])
        self._configure_table(self.available_table)
        self.available_card.addWidget(self.available_search)
        self.available_card.addWidget(self.available_table)
        row.addWidget(self.available_card, 3)

        self.team_tabs = QTabWidget()

        self.team_card, self.team_table = self._create_team_editor("Team A")
        self.team_b_card, self.team_b_table = self._create_team_editor("Team B")
        self.team_tabs.addTab(self.team_card, "TEAM A")
        self.team_tabs.addTab(self.team_b_card, "TEAM B")
        row.addWidget(self.team_tabs, 5)

        analysis = QVBoxLayout()
        analysis.setSpacing(10)
        self.analysis_card = FoundryCard("Team Analysis")
        self.analysis_summary = QLabel()
        self.analysis_summary.setWordWrap(True)
        self.analysis_card.addWidget(self.analysis_summary)
        analysis.addWidget(self.analysis_card)

        self.support_card = FoundryCard("Support Summary")
        self.support_text = QLabel()
        self.support_text.setWordWrap(True)
        self.support_card.addWidget(self.support_text)
        analysis.addWidget(self.support_card)

        self.risks_card = FoundryCard("Key Risks")
        self.risks_text = QLabel()
        self.risks_text.setWordWrap(True)
        self.risks_card.addWidget(self.risks_text)
        analysis.addWidget(self.risks_card)
        row.addLayout(analysis, 3)

        self.layout.addLayout(row, 1)

    def _build_recommendations_row(self):
        row = QHBoxLayout()
        row.setSpacing(10)

        self.change_card = FoundryCard("Recommended Changes")
        self.change_text = QLabel(
            "1. Add missing support coverage.\n"
            "2. Resolve redundant support sets.\n"
            "3. Fill open role slots.\n"
            "4. Adjust sustain and survivability for the encounter."
        )
        self.change_text.setWordWrap(True)
        self.change_card.addWidget(self.change_text)
        row.addWidget(self.change_card, 2)

        self.gear_card = FoundryCard("Gear Recommendations")
        self.gear_table = QTableWidget(4, 3)
        self.gear_table.setHorizontalHeaderLabels(["PLAYER", "CHANGE", "REASON"])
        self._configure_table(self.gear_table)
        self._set_dummy_rows(self.gear_table, [
            ("—", "Support set assignment pending", "Optimizer logic not connected yet"),
            ("—", "Arena weapon review", "Encounter-specific recommendation"),
            ("—", "Mythic review", "Group composition dependent"),
            ("—", "Trait / enchant review", "Final stat targets pending"),
        ])
        self.gear_card.addWidget(self.gear_table)
        row.addWidget(self.gear_card, 3)

        self.skill_card = FoundryCard("Skill Recommendations")
        self.skill_table = QTableWidget(4, 4)
        self.skill_table.setHorizontalHeaderLabels(["PLAYER", "ADD / CHANGE", "REMOVE", "REASON"])
        self._configure_table(self.skill_table)
        self._set_dummy_rows(self.skill_table, [
            ("—", "Encounter utility skill", "—", "Mechanic requirement pending"),
            ("—", "Support source", "—", "Coverage requirement pending"),
            ("—", "Cleave / execute option", "—", "Damage profile pending"),
            ("—", "Defensive flex skill", "—", "Survivability requirement pending"),
        ])
        self.skill_card.addWidget(self.skill_table)
        row.addWidget(self.skill_card, 3)

        self.notes_card = FoundryCard("Notes")
        notes = QLabel(
            "• This is a suggested team.\n"
            "• Re-run after roster or build changes.\n"
            "• Coverage and encounter requirements will feed recommendations here.\n"
            "• Farming needs can be added later if space allows."
        )
        notes.setWordWrap(True)
        self.notes_card.addWidget(notes)
        row.addWidget(self.notes_card, 2)

        self.layout.addLayout(row)

    def _create_team_editor(self, title: str):
        card = FoundryCard(title)
        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.addStretch(1)

        clear_button = QPushButton("Clear Team")
        autofill_button = QPushButton("Auto-Fill")
        actions_layout.addWidget(clear_button)
        actions_layout.addWidget(autofill_button)
        card.set_header_action(actions)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels([
            "ROLE", "PLAYER", "CLASS", "BUILD", "RESPONSIBILITIES", "STATUS"
        ])
        self._configure_table(table)
        card.addWidget(table)

        clear_button.clicked.connect(lambda: self._clear_team(table))
        autofill_button.clicked.connect(lambda: self._autofill_team(table))
        return card, table

    def _team_source_changed(self, _text: str) -> None:
        if hasattr(self, "team_table"):
            self._generate_preview()

    def _role_slots(self) -> list[str]:
        if self.group_size_combo.currentText().startswith("12"):
            return ["Main Tank", "Off Tank", "Healer 1", "Healer 2"] + [
                f"DD {index}" for index in range(1, 9)
            ]
        return ["Tank", "Healer", "DD 1", "DD 2"]

    def _populate_team_editor(self, table: QTableWidget, *, autofill: bool) -> None:
        role_slots = self._role_slots()
        builds = list(self.roster.Members)
        source_mode = self._effective_source_mode()
        table.setRowCount(len(role_slots))

        self._team_combo_signal_guard = True
        try:
            for row, role_name in enumerate(role_slots):
                table.setItem(row, 0, QTableWidgetItem(role_name))
                selector = QComboBox()
                selector.addItem("Open slot", None)
                for index, build in enumerate(builds):
                    player = (
                        getattr(build, "Name", "")
                        or getattr(build, "Gamertag", "")
                        or "Unnamed Player"
                    )
                    build_name = getattr(build, "BuildName", "") or "Current Build"
                    selector.addItem(f"{player} — {build_name}", index)

                recruitment_value = f"recruitment:{row}"
                selector.addItem(
                    f"Recruit for {role_name}",
                    recruitment_value,
                )

                if autofill:
                    if source_mode == "Recruitment Plan Only":
                        selector.setCurrentIndex(selector.findData(recruitment_value))
                    elif row < len(builds):
                        selector.setCurrentIndex(row + 1)
                    elif source_mode == "Hybrid: Players + Recruitment":
                        selector.setCurrentIndex(selector.findData(recruitment_value))

                selector.currentIndexChanged.connect(
                    lambda _index, current_table=table, current_row=row:
                    self._team_selection_changed(current_table, current_row)
                )
                table.setCellWidget(row, 1, selector)
                self._team_selection_changed(table, row)
        finally:
            self._team_combo_signal_guard = False

    def _team_selection_changed(self, table: QTableWidget, row: int) -> None:
        selector = table.cellWidget(row, 1)
        selection = selector.currentData() if isinstance(selector, QComboBox) else None
        build = (
            self.roster.Members[selection]
            if isinstance(selection, int) and 0 <= selection < len(self.roster.Members)
            else None
        )

        if isinstance(selection, str) and selection.startswith("recruitment:"):
            role_label_item = table.item(row, 0)
            role_label = role_label_item.text() if role_label_item else "DD"
            requirement = self.recruitment_planner.create_requirement(
                slot_id=selection,
                role_label=role_label,
            )
            values = (
                "Flexible",
                "Open recruitment requirement",
                requirement.qualification_summary,
                "RECRUIT",
            )
        elif build is not None:
            values = (
                getattr(build, "EsoClass", "") or "—",
                getattr(build, "BuildName", "") or "Current Build",
                "Capability and provider analysis pending",
                "SAVED",
            )
        else:
            values = ("—", "Open", "Any suitable build", "—")

        for column, value in enumerate(values, start=2):
            table.setItem(row, column, QTableWidgetItem(str(value)))
        if not self._team_combo_signal_guard:
            self._update_team_analysis()

    @staticmethod
    def _team_counts(table: QTableWidget) -> tuple[int, int]:
        real_count = 0
        recruitment_count = 0
        for row in range(table.rowCount()):
            selector = table.cellWidget(row, 1)
            selection = selector.currentData() if isinstance(selector, QComboBox) else None
            if isinstance(selection, int):
                real_count += 1
            elif isinstance(selection, str) and selection.startswith("recruitment:"):
                recruitment_count += 1
        return real_count, recruitment_count

    @classmethod
    def _selected_team_count(cls, table: QTableWidget) -> int:
        real_count, recruitment_count = cls._team_counts(table)
        return real_count + recruitment_count

    def _autofill_team(self, table: QTableWidget) -> None:
        self._populate_team_editor(table, autofill=True)
        self._update_team_analysis()

    def _update_team_analysis(self) -> None:
        if not hasattr(self, "team_table"):
            return
        target = len(self._role_slots())
        team_a_real, team_a_recruit = self._team_counts(self.team_table)
        team_a_count = team_a_real + team_a_recruit
        comparing = policy_for_mode(self._current_mode()).uses_two_teams
        team_b_real, team_b_recruit = self._team_counts(self.team_b_table)
        team_b_count = team_b_real + team_b_recruit

        self.team_card.set_badge(f"{team_a_count}/{target}")
        self.team_b_card.set_badge(f"{team_b_count}/{target}")

        lines = [
            (
                f"Team A: {team_a_real} saved player(s) + "
                f"{team_a_recruit} recruitment requirement(s)"
            ),
            "Modeled Composition Potential: unresolved",
        ]
        if comparing:
            lines.insert(
                1,
                (
                    f"Team B: {team_b_real} saved player(s) + "
                    f"{team_b_recruit} recruitment requirement(s)"
                ),
            )
            lines.append("Comparison: select an encounter model before ranking")
        self.analysis_summary.setText("\n".join(lines))
        self.support_text.setText(
            "Recruitment entries are open requirements, not fabricated players.\n"
            "Encounter capability assignments and declared uptime remain unresolved."
        )

        open_a = target - team_a_count
        open_b = target - team_b_count if comparing else 0
        risks = [
            f"⚠ Team A has {open_a} unplanned slot(s)."
            if open_a else "✓ Team A has a plan for every slot."
        ]
        if comparing:
            risks.append(
                f"⚠ Team B has {open_b} unplanned slot(s)."
                if open_b else "✓ Team B has a plan for every slot."
            )
        if team_a_recruit or (comparing and team_b_recruit):
            risks.append(
                "⚠ Recruitment requirements are not modeled damage contributors "
                "until matched to canonical builds."
            )
        risks.append("⚠ No encounter damage scenario selected; no numeric ranking produced.")
        self.risks_text.setText("\n".join(risks))

    @staticmethod
    def _configure_table(table: QTableWidget):
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)

    @staticmethod
    def _set_dummy_rows(table: QTableWidget, rows):
        table.setRowCount(len(rows))
        for r, values in enumerate(rows):
            for c, value in enumerate(values):
                table.setItem(r, c, QTableWidgetItem(str(value)))

    def refresh(self):
        try:
            self.roster = self.build_service.load()
        except Exception as exc:
            self.roster = BuildRoster()
            self.status.error(f"Failed to load builds: {exc}")
            return

        self._populate_available()
        self._generate_preview()
        self.status.info(
            f"Team Builder ready • {len(self.roster.Members)} saved build(s) available. "
            "Recommendations marked as pending are layout placeholders until optimizer logic is connected."
        )

    def _populate_available(self):
        self.available_table.setRowCount(0)
        for build in self.roster.Members:
            row = self.available_table.rowCount()
            self.available_table.insertRow(row)
            name = getattr(build, "Name", "") or getattr(build, "Gamertag", "") or "Unnamed Player"
            eso_class = getattr(build, "EsoClass", "") or "—"
            role = getattr(build, "Role", "") or "—"
            build_name = getattr(build, "BuildName", "") or "1"
            values = (name, eso_class, role, build_name, "✓")
            for col, value in enumerate(values):
                self.available_table.setItem(row, col, QTableWidgetItem(str(value)))
        self.available_card.set_badge(f"{self.available_table.rowCount()} SAVED")

    def _filter_available(self, text: str):
        query = text.strip().lower()
        for row in range(self.available_table.rowCount()):
            haystack = " ".join(
                self.available_table.item(row, col).text()
                for col in range(self.available_table.columnCount())
                if self.available_table.item(row, col) is not None
            ).lower()
            self.available_table.setRowHidden(row, bool(query and query not in haystack))

    def _generate_preview(self, *_args):
        self._populate_team_editor(self.team_table, autofill=True)
        self._populate_team_editor(self.team_b_table, autofill=True)
        self._update_team_analysis()

    def _clear_team(self, table=None):
        target_table = table or self.team_table
        for row in range(target_table.rowCount()):
            selector = target_table.cellWidget(row, 1)
            if isinstance(selector, QComboBox):
                selector.setCurrentIndex(0)
        self._update_team_analysis()
