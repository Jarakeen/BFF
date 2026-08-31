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
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from models.build_model import BuildRoster
from services.build_service import BuildService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


class OptimizationPage(FoundryPage):
    """Raid Engine team-building and optimization workspace."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.build_service = BuildService(get_data_dir() / "builds.json")
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
        self.team_source_combo.addItems(["Saved Roster", "Custom Selection", "Current Team"])
        self.header.add_context_widget(self._context_field("TEAM SOURCE", self.team_source_combo))

        self.workspace = QWidget()
        self.layout = QVBoxLayout(self.workspace)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        self.add_workspace(self.workspace)

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

        self.team_card = FoundryCard("Proposed Team")
        team_actions = QWidget()
        team_actions_layout = QHBoxLayout(team_actions)
        team_actions_layout.setContentsMargins(0, 0, 0, 0)
        team_actions_layout.addStretch(1)
        clear_button = QPushButton("Clear Team")
        clear_button.clicked.connect(self._clear_team)
        autofill_button = QPushButton("Auto-Fill")
        autofill_button.clicked.connect(self._generate_preview)
        team_actions_layout.addWidget(clear_button)
        team_actions_layout.addWidget(autofill_button)
        self.team_card.set_header_action(team_actions)
        self.team_table = QTableWidget(0, 6)
        self.team_table.setHorizontalHeaderLabels([
            "ROLE", "PLAYER", "CLASS", "BUILD", "RESPONSIBILITIES", "STATUS"
        ])
        self._configure_table(self.team_table)
        self.team_card.addWidget(self.team_table)
        row.addWidget(self.team_card, 5)

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
        self.available_card.set_badge(f"{self.available_table.rowCount()} AVAILABLE")

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
        target = 12 if self.group_size_combo.currentText().startswith("12") else 4
        members = list(self.roster.Members)[:target]
        self.team_table.setRowCount(0)

        if target == 12:
            role_slots = ["Main Tank", "Off Tank", "Healer 1", "Healer 2"] + [f"DD {i}" for i in range(1, 9)]
        else:
            role_slots = ["Tank", "Healer", "DD 1", "DD 2"]

        for index in range(target):
            row = self.team_table.rowCount()
            self.team_table.insertRow(row)
            build = members[index] if index < len(members) else None
            if build is None:
                values = (role_slots[index], "TBD", "—", "Open", "Any suitable build", "—")
            else:
                name = getattr(build, "Name", "") or getattr(build, "Gamertag", "") or "Unnamed Player"
                eso_class = getattr(build, "EsoClass", "") or "—"
                build_name = getattr(build, "BuildName", "") or "Current Build"
                values = (role_slots[index], name, eso_class, build_name, "Pending optimizer analysis", "✓")
            for col, value in enumerate(values):
                self.team_table.setItem(row, col, QTableWidgetItem(str(value)))

        filled = len(members)
        self.team_card.set_badge(f"{filled}/{target}")
        readiness = round((filled / target) * 100) if target else 0
        self.analysis_summary.setText(
            f"Overall Readiness: {readiness}%\n"
            f"Team Slots Filled: {filled}/{target}\n"
            "Group Balance: Pending composition analysis\n"
            "Damage Profile: Pending encounter weighting"
        )
        self.support_text.setText(
            "Major Courage  •  Crusher  •  War Horn\n"
            "Major Slayer  •  Major Vulnerability  •  Purify\n"
            "Detailed provider coverage will come from the Coverage page."
        )
        open_slots = max(0, target - filled)
        self.risks_text.setText(
            (f"⚠ {open_slots} open team slot(s).\n" if open_slots else "✓ Team size filled.\n")
            + "⚠ Encounter-specific buff/debuff requirements not connected yet.\n"
            + "⚠ Gear and skill recommendations are currently placeholders."
        )

    def _clear_team(self):
        self.team_table.setRowCount(0)
        self.team_card.set_badge("0")
        self.analysis_summary.setText("No proposed team. Use Auto-Fill or Generate Best Team.")
        self.support_text.setText("Coverage analysis will appear after a team is proposed.")
        self.risks_text.setText("No team selected.")
