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
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from minmax.build_backed_roster_lab import BuildBackedRosterLab
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.custom_roster_lab import CustomRosterLab
from minmax.mock_roster_lab import LAB_EFFECTS
from minmax.role import Role
from ui.components.foundry_card import FoundryCard


class CustomRosterLabWidget(QWidget):
    """Phase 5B sandbox with Evidence and Build-backed test modes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lab = CustomRosterLab()
        self.build_lab = BuildBackedRosterLab()
        self._build_ui()
        self._refresh_roster()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        intro = FoundryCard("CUSTOM ROSTER • PHASE 5B")
        intro.addWidget(QLabel(
            "Test disposable rosters through the real Phase 4 EncounterEvaluator."
        ))
        intro.addWidget(QLabel(
            "Evidence mode injects known capabilities. Build mode resolves supported build ingredients into the same evaluator path and reports anything the current model cannot prove."
        ))
        root.addWidget(intro)

        mode_card = FoundryCard("Evidence Source")
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("SOURCE"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Evidence", "Build-backed"])
        self.mode_combo.currentTextChanged.connect(self._switch_mode)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch(1)
        mode_card.addLayout(mode_row)
        root.addWidget(mode_card)

        self.editor_host = QWidget()
        self.editor_layout = QVBoxLayout(self.editor_host)
        self.editor_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.editor_host)

        roster = FoundryCard("Mock Roster")
        self.roster_table = QTableWidget(0, 6)
        self.roster_table.setHorizontalHeaderLabels([
            "Player", "Role", "Build / Evidence", "Uptime", "Resolved / Capabilities", ""
        ])
        self.roster_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.roster_table.horizontalHeader().setStretchLastSection(True)
        self.roster_table.setMinimumHeight(230)
        roster.addWidget(self.roster_table)
        remove_button = QPushButton("REMOVE SELECTED PLAYER")
        remove_button.clicked.connect(self._remove_selected)
        roster.addWidget(remove_button)
        root.addWidget(roster)

        evaluation = FoundryCard("Encounter Evaluation")
        action_host = QWidget()
        action_row = QHBoxLayout(action_host)
        action_row.setContentsMargins(14, 14, 14, 14)
        evaluate_button = QPushButton("EVALUATE ROSTER")
        self.state_label = QLabel("READY • No evaluation yet")
        action_row.addWidget(evaluate_button)
        action_row.addWidget(self.state_label)
        action_row.addStretch(1)
        evaluation.addWidget(action_host)
        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels([
            "Requirement", "Result", "Valid", "Required", "Explanation"
        ])
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setMinimumHeight(260)
        self.results_table.setFrameShape(QTableWidget.NoFrame)
        self.results_table.setLineWidth(0)
        evaluation.addWidget(self.results_table)
        root.addWidget(evaluation)
        root.addStretch(1)

        self._build_evidence_editor()
        evaluate_button.clicked.connect(self._evaluate)

    def _clear_editor(self):
        while self.editor_layout.count():
            item = self.editor_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _build_evidence_editor(self):
        self._clear_editor()
        editor = FoundryCard("Evidence Player")
        row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Player name")
        self.role_combo = QComboBox()
        self.role_combo.addItems([role.value.title() for role in Role])
        self.uptime = QDoubleSpinBox()
        self.uptime.setRange(0.0, 1.0)
        self.uptime.setSingleStep(0.01)
        self.uptime.setValue(1.0)
        self.uptime.setSuffix(" uptime")
        row.addWidget(QLabel("PLAYER"))
        row.addWidget(self.name_edit, 2)
        row.addWidget(QLabel("ROLE"))
        row.addWidget(self.role_combo)
        row.addWidget(QLabel("UPTIME"))
        row.addWidget(self.uptime)
        editor.addLayout(row)

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
        add_button.clicked.connect(self._add_player)
        clear_button.clicked.connect(self._clear)
        self.editor_layout.addWidget(editor)

    def _build_build_editor(self):
        self._clear_editor()
        editor = FoundryCard("Build-backed Player")
        row = QHBoxLayout()
        self.build_name_edit = QLineEdit()
        self.build_name_edit.setPlaceholderText("Player name")
        self.build_role_combo = QComboBox()
        self.build_role_combo.addItems([role.value.title() for role in Role])
        self.class_combo = QComboBox()
        self.class_combo.addItems([character_class.value.title() for character_class in CharacterClass])
        self.gear_combo = QComboBox()
        for set_id, name in self.build_lab.available_gear_sets():
            self.gear_combo.addItem(name, set_id)
        self.gear_pieces = QSpinBox()
        self.gear_pieces.setRange(1, 10)
        self.gear_pieces.setValue(5)
        self.bar_combo = QComboBox()
        self.bar_combo.addItems([bar.value.title() for bar in BarId])
        row.addWidget(QLabel("PLAYER"))
        row.addWidget(self.build_name_edit, 2)
        row.addWidget(QLabel("ROLE"))
        row.addWidget(self.build_role_combo)
        row.addWidget(QLabel("CLASS"))
        row.addWidget(self.class_combo)
        editor.addLayout(row)

        gear_row = QHBoxLayout()
        gear_row.addWidget(QLabel("GEAR SET"))
        gear_row.addWidget(self.gear_combo, 2)
        gear_row.addWidget(QLabel("PIECES"))
        gear_row.addWidget(self.gear_pieces)
        add_set_button = QPushButton("ADD SET")
        gear_row.addWidget(add_set_button)
        gear_row.addWidget(QLabel("ACTIVE BAR"))
        gear_row.addWidget(self.bar_combo)
        editor.addLayout(gear_row)

        self.gear_assignment_list = QListWidget()
        self.gear_assignment_list.setMaximumHeight(110)
        editor.addWidget(QLabel("EQUIPPED SETS"))
        editor.addWidget(self.gear_assignment_list)

        assignment_buttons = QHBoxLayout()
        remove_set_button = QPushButton("REMOVE SELECTED SET")
        clear_sets_button = QPushButton("CLEAR SETS")
        assignment_buttons.addWidget(remove_set_button)
        assignment_buttons.addWidget(clear_sets_button)
        assignment_buttons.addStretch(1)
        editor.addLayout(assignment_buttons)

        note = QLabel(
            "A mock build can use multiple simultaneous set bonuses, such as 5 + 5 armor/jewelry pieces. The resolver counts the actual equipped pieces before evaluating known effects."
        )
        note.setWordWrap(True)
        editor.addWidget(note)

        buttons = QHBoxLayout()
        add_button = QPushButton("ADD BUILD PLAYER")
        clear_button = QPushButton("CLEAR ROSTER")
        buttons.addWidget(add_button)
        buttons.addWidget(clear_button)
        buttons.addStretch(1)
        editor.addLayout(buttons)
        add_button.clicked.connect(self._add_build_player)
        clear_button.clicked.connect(self._clear)
        add_set_button.clicked.connect(self._add_set_assignment)
        remove_set_button.clicked.connect(self._remove_set_assignment)
        clear_sets_button.clicked.connect(self._clear_set_assignments)
        self.editor_layout.addWidget(editor)

    def _switch_mode(self, mode: str):
        if mode == "Build-backed":
            self._build_build_editor()
        else:
            self._build_evidence_editor()
        self.results_table.setRowCount(0)
        self._refresh_roster()

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

    def _add_set_assignment(self):
        if self.gear_combo.currentIndex() < 0:
            return
        set_id = int(self.gear_combo.currentData())
        pieces = self.gear_pieces.value()
        current_total = sum(
            int(self.gear_assignment_list.item(index).data(Qt.UserRole + 1))
            for index in range(self.gear_assignment_list.count())
        )
        if current_total + pieces > self.build_lab.MAX_ARMOR_SLOTS:
            self.state_label.setText(
                f"ATTENTION • {self.build_lab.MAX_ARMOR_SLOTS} armor/jewelry slots maximum"
            )
            return
        item = QListWidgetItem(
            f"{self.gear_combo.currentText()} • {pieces} piece(s)"
        )
        item.setData(Qt.UserRole, set_id)
        item.setData(Qt.UserRole + 1, pieces)
        self.gear_assignment_list.addItem(item)

    def _remove_set_assignment(self):
        row = self.gear_assignment_list.currentRow()
        if row >= 0:
            self.gear_assignment_list.takeItem(row)

    def _clear_set_assignments(self):
        self.gear_assignment_list.clear()

    def _add_build_player(self):
        assignments = []
        for index in range(self.gear_assignment_list.count()):
            item = self.gear_assignment_list.item(index)
            assignments.append((int(item.data(Qt.UserRole)), int(item.data(Qt.UserRole + 1))))

        player = self.build_lab.add_player(
            self.build_name_edit.text(),
            Role(self.build_role_combo.currentText().casefold()),
            CharacterClass(self.class_combo.currentText().casefold()),
            gear_sets=tuple(assignments),
            active_bar=BarId(self.bar_combo.currentText().casefold()),
        )
        self.build_name_edit.clear()
        self._clear_set_assignments()
        self._refresh_roster()
        if player.validation_errors:
            self.state_label.setText("ATTENTION • Build validation failed")
        elif player.unsupported_sources:
            self.state_label.setText("ATTENTION • Some build effects are not yet supported")
        else:
            self.state_label.setText("READY • Build effects resolved")

    def _remove_selected(self):
        row = self.roster_table.currentRow()
        if row < 0:
            return
        if self.mode_combo.currentText() == "Build-backed":
            self.build_lab.remove_player(row)
        else:
            self.lab.remove_player(row)
        self._refresh_roster()

    def _clear(self):
        self.lab.clear()
        self.build_lab.clear()
        self.results_table.setRowCount(0)
        self.state_label.setText("READY • Roster cleared")
        if hasattr(self, "gear_assignment_list"):
            self._clear_set_assignments()
        self._refresh_roster()

    def _refresh_roster(self):
        build_mode = self.mode_combo.currentText() == "Build-backed"
        players = self.build_lab.players if build_mode else self.lab.players
        self.roster_table.setRowCount(len(players))
        for row, player in enumerate(players):
            self.roster_table.setItem(row, 0, QTableWidgetItem(player.name))
            self.roster_table.setItem(row, 1, QTableWidgetItem(player.role.value.upper()))
            if build_mode:
                source = ", ".join(
                    f"{name} ({pieces}p)"
                    for _, name, pieces in player.gear_sets
                    if name
                ) or "No gear"
                resolved = ", ".join(player.resolved_effects)
                if not resolved:
                    resolved = "; ".join(player.unsupported_sources) or "No resolved support effects"
                uptime = "Build"
            else:
                source = "Manual evidence"
                resolved = ", ".join(player.capabilities) or "None"
                uptime = f"{player.uptime:.0%}"
            self.roster_table.setItem(row, 2, QTableWidgetItem(source))
            self.roster_table.setItem(row, 3, QTableWidgetItem(uptime))
            self.roster_table.setItem(row, 4, QTableWidgetItem(resolved))
            self.roster_table.setItem(row, 5, QTableWidgetItem(""))

    def _evaluate(self):
        try:
            evaluation = (
                self.build_lab.evaluate()
                if self.mode_combo.currentText() == "Build-backed"
                else self.lab.evaluate()
            )
        except Exception as exc:
            self.results_table.setRowCount(0)
            self.state_label.setText(f"ERROR • {exc}")
            return

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
