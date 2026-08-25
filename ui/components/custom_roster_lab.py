from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from minmax.custom_roster_lab import CustomRosterLab
from minmax.mock_roster_lab import LAB_EFFECTS
from minmax.role import Role
from ui.components.foundry_card import FoundryCard


class CustomRosterLabWidget(QWidget):
    """Human-friendly Phase 5B sandbox for building disposable rosters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lab = CustomRosterLab()
        self._build_ui()
        self._refresh_roster()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        intro = FoundryCard("CUSTOM ROSTER • PHASE 5B")
        intro.addWidget(QLabel(
            "Build any disposable roster you want, then send it through the real Phase 4 EncounterEvaluator."
        ))
        intro.addWidget(QLabel(
            "Nothing here writes to Builds, ESO Logs, assignments, or the production roster."
        ))
        root.addWidget(intro)

        editor = FoundryCard("Add Player")
        name_row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Player name")
        self.role_combo = QComboBox()
        self.role_combo.addItems([role.value.title() for role in Role])
        self.uptime = QDoubleSpinBox()
        self.uptime.setRange(0.0, 1.0)
        self.uptime.setSingleStep(0.01)
        self.uptime.setValue(1.0)
        self.uptime.setSuffix(" uptime")
        name_row.addWidget(QLabel("PLAYER"))
        name_row.addWidget(self.name_edit, 2)
        name_row.addWidget(QLabel("ROLE"))
        name_row.addWidget(self.role_combo)
        name_row.addWidget(QLabel("UPTIME"))
        name_row.addWidget(self.uptime)
        editor.addLayout(name_row)

        capability_row = QHBoxLayout()
        self.capability_list = QListWidget()
        self.capability_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.capability_list.setMaximumHeight(105)
        for effect in LAB_EFFECTS:
            item = QListWidgetItem(effect.replace("_", " ").title())
            item.setData(Qt.UserRole, effect)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.capability_list.addItem(item)
        capability_row.addWidget(QLabel("CAPABILITIES"))
        capability_row.addWidget(self.capability_list, 1)
        editor.addLayout(capability_row)

        buttons = QHBoxLayout()
        add_button = QPushButton("ADD PLAYER")
        clear_button = QPushButton("CLEAR ROSTER")
        buttons.addWidget(add_button)
        buttons.addWidget(clear_button)
        buttons.addStretch(1)
        editor.addLayout(buttons)
        root.addWidget(editor)

        roster = FoundryCard("Mock Roster")
        self.roster_table = QTableWidget(0, 5)
        self.roster_table.setHorizontalHeaderLabels(["Player", "Role", "Uptime", "Capabilities", ""])
        self.roster_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.roster_table.horizontalHeader().setStretchLastSection(True)
        self.roster_table.setMinimumHeight(230)
        roster.addWidget(self.roster_table)
        remove_button = QPushButton("REMOVE SELECTED PLAYER")
        remove_button.clicked.connect(self._remove_selected)
        roster.addWidget(remove_button)
        root.addWidget(roster)

        evaluation = FoundryCard("Encounter Evaluation")
        action_row = QHBoxLayout()
        evaluate_button = QPushButton("EVALUATE ROSTER")
        self.state_label = QLabel("READY • No evaluation yet")
        action_row.addWidget(evaluate_button)
        action_row.addWidget(self.state_label)
        action_row.addStretch(1)
        evaluation.addLayout(action_row)

        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(["Requirement", "Result", "Valid", "Required", "Explanation"])
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setMinimumHeight(260)
        evaluation.addWidget(self.results_table)
        root.addWidget(evaluation)
        root.addStretch(1)

        add_button.clicked.connect(self._add_player)
        clear_button.clicked.connect(self._clear)
        evaluate_button.clicked.connect(self._evaluate)

    def _selected_capabilities(self) -> list[str]:
        values = []
        for index in range(self.capability_list.count()):
            item = self.capability_list.item(index)
            if item.checkState() == Qt.Checked:
                values.append(item.data(Qt.UserRole))
        return values

    def _reset_capabilities(self):
        for index in range(self.capability_list.count()):
            self.capability_list.item(index).setCheckState(Qt.Unchecked)

    def _add_player(self):
        self.lab.add_player(
            self.name_edit.text(),
            Role(self.role_combo.currentText().casefold()),
            self._selected_capabilities(),
            self.uptime.value(),
        )
        self.name_edit.clear()
        self.uptime.setValue(1.0)
        self._reset_capabilities()
        self._refresh_roster()

    def _remove_selected(self):
        row = self.roster_table.currentRow()
        if row >= 0:
            self.lab.remove_player(row)
            self._refresh_roster()

    def _clear(self):
        self.lab.clear()
        self.results_table.setRowCount(0)
        self.state_label.setText("READY • Roster cleared")
        self._refresh_roster()

    def _refresh_roster(self):
        self.roster_table.setRowCount(len(self.lab.players))
        for row, player in enumerate(self.lab.players):
            self.roster_table.setItem(row, 0, QTableWidgetItem(player.name))
            self.roster_table.setItem(row, 1, QTableWidgetItem(player.role.value.upper()))
            self.roster_table.setItem(row, 2, QTableWidgetItem(f"{player.uptime:.0%}"))
            self.roster_table.setItem(row, 3, QTableWidgetItem(", ".join(player.capabilities) or "None"))
            self.roster_table.setItem(row, 4, QTableWidgetItem(""))

    def _evaluate(self):
        evaluation = self.lab.evaluate()
        self.results_table.setRowCount(len(evaluation.classifications))
        for row, result in enumerate(evaluation.classifications):
            self.results_table.setItem(row, 0, QTableWidgetItem(result.effect_name))
            self.results_table.setItem(row, 1, QTableWidgetItem(result.classification.value.upper()))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(result.valid_provider_count)))
            self.results_table.setItem(row, 3, QTableWidgetItem(str(result.required_provider_count)))
            self.results_table.setItem(row, 4, QTableWidgetItem(result.explanation))
        if evaluation.is_fully_covered:
            self.state_label.setText("READY • Fully covered")
        else:
            self.state_label.setText(f"ATTENTION • {len(evaluation.problems)} problem(s)")
