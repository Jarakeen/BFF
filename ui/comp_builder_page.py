from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.raid_plan_repository import RaidPlanRepository
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
from ui.components.team_progress_panels import make_coverage_card
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

class EditablePlanNameCombo(QComboBox):
    """Editable Raid Plan picker that preserves the old QLineEdit API."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        if self.lineEdit() is not None:
            self.lineEdit().setPlaceholderText("Choose a saved plan or type a new name…")
            self.lineEdit().setClearButtonEnabled(True)

    def text(self) -> str:
        return self.currentText()

    def setText(self, value: object) -> None:
        self.setEditText(str(value or ""))


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
        self.raid_plan_repository = RaidPlanRepository(data_dir / "raid_plans.json")
        self.current_template: TeamCompositionTemplate | None = None
        self.current_slots: tuple[CompositionSlot, ...] = ()
        self._build_ui()
        self._load_for_goal()
        self._refresh_raid_plan_name_choices()

    @staticmethod
    def _seat_label(seat_id: object) -> str:
        key = str(seat_id or "").strip().casefold()
        labels = {
            "tank-1": "Tank 1",
            "tank-2": "Tank 2",
            "healer-1": "Healer 1",
            "healer-2": "Healer 2",
            **{f"dd-{index}": f"DD {index}" for index in range(1, 9)},
        }
        return labels.get(key, str(seat_id or "").strip())

    @staticmethod
    def _raid_plan_group_size(plan) -> int:
        """Infer 4/12 from canonical planning chairs, not named-player count."""
        seats = {
            str(member.seat_id or "").strip().casefold()
            for member in tuple(plan.members or ())
            if str(member.seat_id or "").strip()
        }
        twelve_player_only = {
            "tank-2",
            "healer-2",
            *{f"dd-{index}" for index in range(3, 9)},
        }
        if seats & twelve_player_only:
            return 12
        four_player_seats = {"tank-1", "healer-1", "dd-1", "dd-2"}
        if seats and seats.issubset(four_player_seats):
            return 4
        return 12

    @staticmethod
    def _planned_five_piece_sets_by_seat(plan) -> dict[str, tuple[str, ...]]:
        """Classify all planned set names in one DB query, then project by seat."""
        from services.comp_builder_build_candidates import _five_piece_set_names

        all_names = tuple(
            dict.fromkeys(
                str(name or "").strip()
                for member in plan.members
                for name in tuple(member.planned_gear_sets or ())
                if str(name or "").strip()
            )
        )
        if not all_names:
            return {}
        five_piece_names = {
            name.casefold()
            for name in _five_piece_set_names(
                get_data_dir() / "eso.db",
                all_names,
            )
        }
        return {
            CompBuilderPage._seat_label(member.seat_id): tuple(
                name
                for name in tuple(member.planned_gear_sets or ())
                if str(name or "").strip().casefold() in five_piece_names
            )[:2]
            for member in plan.members
            if any(
                str(name or "").strip().casefold() in five_piece_names
                for name in tuple(member.planned_gear_sets or ())
            )
        }

    def _refresh_raid_plan_name_choices(self) -> None:
        current = self.plan_name_input.text().strip()
        self.plan_name_input.blockSignals(True)
        self.plan_name_input.clear()
        self.plan_name_input.addItem("", None)
        try:
            plans = self.raid_plan_repository.list_plans()
        except Exception:
            plans = ()
        for plan in plans:
            self.plan_name_input.addItem(plan.name, plan.plan_id)
        if current:
            self.plan_name_input.setText(current)
        else:
            self.plan_name_input.setCurrentIndex(0)
        self.plan_name_input.blockSignals(False)

    def _restore_raid_plan_picker_to_current_state(self) -> None:
        state = getattr(self, "_comp_plan_state", None)
        current_id = str(getattr(state, "raid_plan_id", "") or "").strip()
        current_name = str(getattr(state, "raid_plan_name", "") or "").strip()

        self.plan_name_input.blockSignals(True)
        try:
            if current_id:
                current_index = self.plan_name_input.findData(current_id)
                if current_index >= 0:
                    self.plan_name_input.setCurrentIndex(current_index)
                    return
            self.plan_name_input.setCurrentIndex(0)
            if current_name:
                self.plan_name_input.setText(current_name)
        finally:
            self.plan_name_input.blockSignals(False)

    def _confirm_raid_plan_switch(self, target_plan_id: str) -> bool:
        state = getattr(self, "_comp_plan_state", None)
        current_id = str(getattr(state, "raid_plan_id", "") or "").strip()
        if current_id and current_id == str(target_plan_id or "").strip():
            return True

        has_pending = getattr(self, "has_pending_changes", None)
        if not callable(has_pending) or not has_pending():
            return True

        box = QMessageBox(self)
        box.setWindowTitle("Unsaved Comp Plan Changes")
        box.setText("You have unsaved changes in Comp Maker.")
        box.setInformativeText(
            "Save them before loading another Raid Plan, discard them, or cancel the switch."
        )
        box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        answer = box.exec()

        if answer == QMessageBox.StandardButton.Save:
            save_pending = getattr(self, "save_pending_changes", None)
            if not callable(save_pending) or not bool(save_pending()):
                self._restore_raid_plan_picker_to_current_state()
                return False
            return True
        if answer == QMessageBox.StandardButton.Discard:
            discard_pending = getattr(self, "discard_pending_changes", None)
            if callable(discard_pending):
                discard_pending()
            return True

        self._restore_raid_plan_picker_to_current_state()
        return False

    def _raid_plan_name_selected(self, index: int) -> None:
        plan_id = self.plan_name_input.itemData(index)
        if not plan_id:
            return
        if not self._confirm_raid_plan_switch(str(plan_id)):
            return
        plan = self.raid_plan_repository.get(str(plan_id))
        if plan is None:
            return

        trial_key = str(plan.trial_id or "").replace("-", " ").casefold()
        self.goal_combo.blockSignals(True)
        self.difficulty_combo.blockSignals(True)
        try:
            for combo_index in range(self.goal_combo.count()):
                label = self.goal_combo.itemText(combo_index)
                trial_label = GOAL_TRIALS.get(label, label)
                if trial_label.replace("-", " ").casefold() == trial_key:
                    self.goal_combo.setCurrentIndex(combo_index)
                    break
            if plan.difficulty:
                difficulty_index = self.difficulty_combo.findText(
                    str(plan.difficulty),
                    Qt.MatchFlag.MatchFixedString,
                )
                if difficulty_index >= 0:
                    self.difficulty_combo.setCurrentIndex(difficulty_index)
        finally:
            self.goal_combo.blockSignals(False)
            self.difficulty_combo.blockSignals(False)

        from services.comp_plan_state_service import CompPlanStateService
        from services.eso_database import EsoDatabase
        from services.roster_service import RosterService

        self._comp_plan_state = CompPlanStateService.from_raid_plan(
            plan,
            achievement_goal=self.goal_combo.currentText().strip() or None,
        )

        roster_service = RosterService(EsoDatabase(get_data_dir() / "eso.db"))
        personnel = tuple(roster_service.list_members())

        def _legacy_personnel_match(member):
            if member.roster_member_id is not None:
                return roster_service.get_member(int(member.roster_member_id))
            gamertag = str(member.gamertag or "").strip().casefold()
            if not gamertag:
                return None
            matches = tuple(
                row
                for row in personnel
                if str(getattr(row, "PlayerName", "") or "").strip().casefold()
                == gamertag
                and getattr(row, "Id", None) is not None
            )
            return matches[0] if len(matches) == 1 else None

        members = []
        for member in plan.members:
            personnel_row = _legacy_personnel_match(member)
            members.append(
                SimpleNamespace(
                    Id=(
                        member.roster_member_id
                        if member.roster_member_id is not None
                        else getattr(personnel_row, "Id", None)
                    ),
                    CanonicalPlayerId=(
                        str(member.player_id or "").strip()
                        or str(
                            getattr(personnel_row, "CanonicalPlayerId", "") or ""
                        ).strip()
                    ),
                    CanonicalCharacterId=(
                        str(member.character_id or "").strip()
                        or str(
                            getattr(personnel_row, "CanonicalCharacterId", "") or ""
                        ).strip()
                    ),
                    RaidSeatId=self._seat_label(member.seat_id),
                    PlayerName=str(member.gamertag or "").strip() or "Recruit",
                    CharacterName=str(member.character_name or "").strip(),
                    PrimaryRole=str(member.role or "").strip(),
                    EsoClass=str(member.eso_class or "").strip(),
                )
            )
        members = tuple(members)
        self._raid_plan_origin_id = plan.plan_id
        self._raid_plan_class_by_seat = {
            self._seat_label(member.seat_id): str(member.eso_class or "").strip()
            for member in plan.members
            if str(member.eso_class or "").strip()
        }
        self._comp_class_constraint_by_slot = dict(self._raid_plan_class_by_seat)
        planned_five_piece_sets = self._planned_five_piece_sets_by_seat(plan)
        self._comp_manual_gear_sets_by_slot = dict(planned_five_piece_sets)

        apply_context = getattr(self, "apply_roster_team_context", None)
        self._comp_loading_plan = True
        try:
            if callable(apply_context):
                apply_context(
                    plan.name,
                    members,
                    group_size=self._raid_plan_group_size(plan),
                )
        finally:
            self._comp_loading_plan = False

        # Roster intake may rebuild chair state. Reassert exact Raid Plan ownership
        # after that rebuild so classes and planned gear cannot be replaced by defaults.
        self._comp_manual_gear_sets_by_slot = dict(planned_five_piece_sets)

        try:
            from ui.comp_builder_roster_intake_support import apply_raid_plan_class_constraints
            apply_raid_plan_class_constraints(self, self._raid_plan_class_by_seat)
        except (AttributeError, TypeError, ValueError):
            pass

        self.plan_name_input.setText(plan.name)
        self._comp_plan_state = self._comp_plan_state.mark_saved()
        self._comp_unbound_baseline_state = None
        try:
            from ui.comp_builder_phase14_shell_support import refresh_phase14_presentation
            refresh_phase14_presentation(self)
        except (AttributeError, TypeError, ValueError):
            pass
        self.status.success(f"Loaded Raid Plan into Comp Maker: {plan.name}.")

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
        self.matrix_card.setMaximumHeight(480)
        matrix_actions = QWidget()
        matrix_actions_layout = QHBoxLayout(matrix_actions)
        matrix_actions_layout.setContentsMargins(0, 0, 0, 0)
        matrix_actions_layout.setSpacing(6)
        self.recommended_button = QPushButton("Load Recommended")
        self.reset_button = QPushButton("Reset Flexible")
        matrix_actions_layout.addWidget(self.recommended_button)
        matrix_actions_layout.addWidget(self.reset_button)
        self.matrix_card.set_header_action(matrix_actions)

        self.matrix_table = QTableWidget(0, 8)
        self.matrix_table.setHorizontalHeaderLabels(
            (
                "SLOT",
                "ROLE",
                "PREFERRED CLASS",
                "ALTERNATIVES",
                "REQUIRED",
                "OPTIONAL / FLEX",
                "PROVIDERS",
                "MECHANIC JOBS",
            )
        )
        self.matrix_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.matrix_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.matrix_table.setAlternatingRowColors(True)
        self.matrix_table.verticalHeader().setVisible(False)
        self.matrix_table.verticalHeader().setDefaultSectionSize(32)
        self.matrix_table.horizontalHeader().setStretchLastSection(True)
        self.matrix_table.setFixedHeight(430)
        self.matrix_card.addWidget(self.matrix_table)
        top.addWidget(self.matrix_card, 7)

        side = QVBoxLayout()
        side.setSpacing(10)

        actions_card = FoundryCard("Actions", "➜")
        actions_card.setMaximumHeight(178)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("PLAN NAME"))
        self.plan_name_input = EditablePlanNameCombo()
        self.plan_name_input.activated.connect(self._raid_plan_name_selected)
        name_row.addWidget(self.plan_name_input, 1)
        actions_card.addLayout(name_row)

        action_buttons = QHBoxLayout()
        self.send_button = QPushButton("Send to Raid Plan")
        self.send_button.setProperty("primary", True)
        self.save_template_button = QPushButton("Save Plan")
        self.load_template_button = QPushButton("Legacy Load")
        action_buttons.addWidget(self.send_button, 2)
        action_buttons.addWidget(self.save_template_button, 1)
        action_buttons.addWidget(self.load_template_button, 1)
        actions_card.addLayout(action_buttons)
        side.addWidget(actions_card, 0)

        context_card = FoundryCard("Composition Details & Summary", "✦")
        context_scroll = QScrollArea()
        context_scroll.setWidgetResizable(True)
        context_scroll.setFrameShape(QFrame.Shape.NoFrame)
        context_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        context_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        context_body = QWidget()
        context_layout = QVBoxLayout(context_body)
        context_layout.setContentsMargins(0, 0, 0, 0)
        context_layout.setSpacing(6)
        self.trial_label = QLabel()
        self.trial_label.setWordWrap(True)
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.coverage_label = QLabel()
        self.coverage_label.setWordWrap(True)
        context_layout.addWidget(self.trial_label)
        context_layout.addWidget(self.summary_label)
        context_layout.addWidget(self.coverage_label)
        context_layout.addStretch(1)
        context_scroll.setWidget(context_body)
        context_card.addWidget(context_scroll)
        side.addWidget(context_card, 1)

        top.addLayout(side, 3)
        root.addLayout(top)

        lower = QHBoxLayout()
        lower.setSpacing(10)

        self.progress_coverage_card, self.progress_coverage_grid = make_coverage_card()
        lower.addWidget(self.progress_coverage_card, 7)

        evidence_card = FoundryCard("Evidence & Provenance", "⌁")
        self.evidence_text = QTextEdit()
        self.evidence_text.setReadOnly(True)
        self.evidence_text.setMinimumHeight(190)
        self.evidence_text.setMaximumHeight(270)
        evidence_card.addWidget(self.evidence_text)
        lower.addWidget(evidence_card, 3)

        root.addLayout(lower)
        self.add_workspace(workspace)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

        self.goal_combo.currentTextChanged.connect(self._load_for_goal)
        self.difficulty_combo.currentTextChanged.connect(self._load_for_goal)
        self.recommended_button.clicked.connect(self._load_recommended)
        self.reset_button.clicked.connect(self._load_flexible)
        self.send_button.clicked.connect(self._send_to_roster)
        self.save_template_button.clicked.connect(self._save_user_template)
        self.load_template_button.clicked.connect(self._load_user_template)

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
            "No external class, provider, or mechanic recommendation is being asserted for this matrix."
        )
        self.evidence_text.setPlainText(
            "No published composition evidence is attached to this manual matrix.\n\n"
            "Choose classes, required duties, optional flex duties, provider obligations, and mechanic jobs deliberately. BFF preserves them as roster-plan requirements, not complete builds."
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
            "Class evidence and planning responsibilities are separate from complete build prescriptions."
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

    def _editable_text_cell(self, row: int, column: int, value: str, placeholder: str) -> None:
        field = QLineEdit()
        field.setText(value)
        field.setPlaceholderText(placeholder)
        field.textChanged.connect(self._refresh_coverage)
        self.matrix_table.setCellWidget(row, column, field)

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
            self._editable_text_cell(
                row,
                4,
                " • ".join(slot.required_responsibilities),
                "Required chair duties",
            )
            self._editable_text_cell(
                row,
                5,
                " • ".join(slot.optional_responsibilities),
                "Optional / flex duties",
            )
            self._editable_text_cell(
                row,
                6,
                " • ".join(slot.provider_requirements),
                "Buff, debuff, or utility obligations",
            )
            self._editable_text_cell(
                row,
                7,
                " • ".join(slot.mechanic_jobs),
                "Portal, kite, tombs, add duty, etc.",
            )

    def _selected_class(self, row: int) -> str:
        combo = self.matrix_table.cellWidget(row, 2)
        return combo.currentText().strip() if isinstance(combo, QComboBox) else "Any class"

    def _cell_text(self, row: int, column: int) -> str:
        widget = self.matrix_table.cellWidget(row, column)
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        item = self.matrix_table.item(row, column)
        return item.text().strip() if item is not None else ""

    @staticmethod
    def _split_values(value: str) -> tuple[str, ...]:
        normalized = str(value or "").replace("•", ",")
        return tuple(part.strip() for part in normalized.split(",") if part.strip())

    def _current_slot_payloads(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row in range(self.matrix_table.rowCount()):
            rows.append(
                {
                    "slot_name": self._cell_text(row, 0),
                    "role": self._cell_text(row, 1),
                    "preferred_class": self._selected_class(row),
                    "alternative_classes": list(self._split_values(self._cell_text(row, 3))),
                    "required_responsibilities": list(self._split_values(self._cell_text(row, 4))),
                    "optional_responsibilities": list(self._split_values(self._cell_text(row, 5))),
                    "provider_requirements": list(self._split_values(self._cell_text(row, 6))),
                    "mechanic_jobs": list(self._split_values(self._cell_text(row, 7))),
                }
            )
        return rows

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

        providers = [
            value
            for row in range(self.matrix_table.rowCount())
            if (value := self._cell_text(row, 6))
        ]
        jobs = [
            value
            for row in range(self.matrix_table.rowCount())
            if (value := self._cell_text(row, 7))
        ]
        provider_summary = (
            "\n".join(f"• {value}" for value in providers)
            if providers
            else "• No explicit providers recorded"
        )
        job_summary = (
            "\n".join(f"• {value}" for value in jobs)
            if jobs
            else "• No mechanic jobs assigned yet"
        )
        self.coverage_label.setText(
            f"CLASS MIX\n{class_summary}\n\n"
            f"DECLARED PROVIDER RESPONSIBILITIES\n{provider_summary}\n\n"
            f"MECHANIC JOBS\n{job_summary}"
        )

    def _save_user_template(self, *_args) -> None:
        """Compatibility stub. Phase 14 Save is owned by canonical Raid Plan persistence."""
        self.status.warning(
            "Legacy composition-template saving is retired. Use Save Plan in Comp Maker."
        )

    def _load_user_template(self, *_args) -> None:
        """Compatibility stub retained for decorators that still expect the attribute."""
        self.status.info(
            "Legacy composition templates are retired. Choose a saved Raid Plan from Plan Name."
        )

    def _send_to_roster(self, *_args) -> None:
        """Compatibility stub. Phase 14 redirects this method to canonical Raid Plan save."""
        self.status.warning(
            "Legacy generated-roster transfer is retired. Use Send to Raid Plan."
        )
