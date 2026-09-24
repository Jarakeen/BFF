from __future__ import annotations

"""Plan-owned assignment editing for the persistent Raid Plan workspace.

This layer exposes the existing RaidPlanMember primary/secondary assignment fields without
moving assignment ownership into global Roster/Team persistence. The autocomplete choices
reuse the established Roster Assignments vocabulary so both surfaces speak the same human
language while remaining separate persistence domains.
"""

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter, QHeaderView, QTableWidget, QTableWidgetItem

from models.raid_plan import RaidPlan
from services.raid_group_effect_catalog import GROUP_COVERAGE_NAMES
from services.raid_unique_support_set_catalog import UNIQUE_SUPPORT_SET_NAMES
from ui.components.foundry_card import FoundryCard
from ui.raid_plan_page import RAID_PLAN_SEATS, _clean, _slug
from ui.raid_plan_persistence_page import RaidPlanPersistencePage
from ui.roster_page import _assignment_choice_rows


def raid_plan_assignment_choices() -> tuple[str, ...]:
    """Return one complete plan-owned support assignment vocabulary."""
    values = [
        *(label for label, _identity in _assignment_choice_rows() if _clean(label)),
        *GROUP_COVERAGE_NAMES,
        *UNIQUE_SUPPORT_SET_NAMES,
    ]
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        label = _clean(raw)
        key = label.casefold()
        if not label or key in seen:
            continue
        seen.add(key)
        result.append(label)
    return tuple(result)


def merge_plan_assignment_values(
    plan: RaidPlan,
    assignments_by_seat: dict[str, tuple[str, str]],
) -> RaidPlan:
    """Apply visible assignment values to existing RaidPlan members only.

    Empty strings intentionally clear the corresponding plan-owned assignment. Unknown
    seat keys are ignored so UI presentation cannot manufacture new raid chairs.
    """
    if not isinstance(plan, RaidPlan):
        raise TypeError("plan must be a RaidPlan")

    normalized = {
        _clean(seat_id).casefold(): (_clean(primary), _clean(secondary))
        for seat_id, (primary, secondary) in assignments_by_seat.items()
        if _clean(seat_id)
    }
    members = []
    for member in plan.members:
        values = normalized.get(member.seat_id.casefold())
        if values is None:
            members.append(member)
            continue
        primary, secondary = values
        members.append(
            member.with_selection(
                primary_assignment=primary or None,
                secondary_assignment=secondary or None,
            )
        )
    return replace(plan, members=tuple(members))


class RaidPlanAssignmentPage(RaidPlanPersistencePage):
    """Persistent Raid Plan editor with plan-level primary/secondary assignments."""

    def __init__(self, parent=None) -> None:
        self.assignment_choices = raid_plan_assignment_choices()
        super().__init__(parent)

    def _build_ui(self) -> None:
        super()._build_ui()

        card = FoundryCard("Assignments", "checklist")
        self.assignment_table = QTableWidget(len(RAID_PLAN_SEATS), 4)
        self.assignment_table.setHorizontalHeaderLabels(
            ("SEAT", "PLAYER", "PRIMARY ASSIGNMENT", "SECONDARY ASSIGNMENT")
        )
        self.assignment_table.verticalHeader().setVisible(False)
        self.assignment_table.setMinimumHeight(390)
        self.assignment_table.setMinimumWidth(0)

        header = self.assignment_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        for row, seat in enumerate(RAID_PLAN_SEATS):
            seat_item = QTableWidgetItem(seat)
            seat_item.setFlags(seat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.assignment_table.setItem(row, 0, seat_item)

            player_item = QTableWidgetItem("")
            player_item.setFlags(player_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.assignment_table.setItem(row, 1, player_item)

            self.assignment_table.setCellWidget(row, 2, self._new_assignment_combo())
            self.assignment_table.setCellWidget(row, 3, self._new_assignment_combo())

        card.addWidget(self.assignment_table)
        self.workspace_layout.addWidget(card)

        self._refresh_assignment_players()

    def _new_assignment_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.addItem("")
        combo.addItems(self.assignment_choices)
        combo.currentTextChanged.connect(lambda *_: self._update_summary())
        if combo.lineEdit() is not None:
            combo.lineEdit().setClearButtonEnabled(True)
            combo.lineEdit().setPlaceholderText("Type to find assignment…")

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)
        return combo

    def _assignment_combo(self, row: int, column: int) -> QComboBox | None:
        widget = self.assignment_table.cellWidget(row, column)
        return widget if isinstance(widget, QComboBox) else None

    def _assignment_text(self, row: int, column: int) -> str:
        combo = self._assignment_combo(row, column)
        return _clean(combo.currentText() if combo is not None else "")

    def _set_assignment_text(self, row: int, column: int, value: object) -> None:
        combo = self._assignment_combo(row, column)
        if combo is None:
            return
        combo.blockSignals(True)
        combo.setCurrentText(_clean(value))
        combo.blockSignals(False)

    def _refresh_assignment_player(self, row: int) -> None:
        if not hasattr(self, "assignment_table"):
            return
        item = self.assignment_table.item(row, 1)
        if item is None:
            item = QTableWidgetItem()
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.assignment_table.setItem(row, 1, item)
        item.setText(self._player_text(row))

    def _refresh_assignment_players(self) -> None:
        if not hasattr(self, "assignment_table"):
            return
        for row in range(min(self.assignment_table.rowCount(), self.team_table.rowCount())):
            self._refresh_assignment_player(row)

    def _player_text_changed(self, row: int) -> None:
        super()._player_text_changed(row)
        self._refresh_assignment_player(row)

    def current_plan(self) -> RaidPlan:
        plan = super().current_plan()
        if not hasattr(self, "assignment_table"):
            return plan

        assignments = {
            _slug(seat): (
                self._assignment_text(row, 2),
                self._assignment_text(row, 3),
            )
            for row, seat in enumerate(RAID_PLAN_SEATS)
        }
        return merge_plan_assignment_values(plan, assignments)

    def apply_plan(self, plan: RaidPlan) -> None:
        super().apply_plan(plan)
        if not hasattr(self, "assignment_table"):
            return

        members_by_seat = {member.seat_id.casefold(): member for member in plan.members}
        for row, seat in enumerate(RAID_PLAN_SEATS):
            member = members_by_seat.get(_slug(seat).casefold())
            self._refresh_assignment_player(row)
            self._set_assignment_text(
                row,
                2,
                member.primary_assignment if member is not None else "",
            )
            self._set_assignment_text(
                row,
                3,
                member.secondary_assignment if member is not None else "",
            )
        self._update_summary()

        # The persistence base establishes its navigation baseline before this
        # subclass restores assignment widgets. Re-baseline only after the
        # visible assignment state has been fully applied so a freshly loaded
        # plan is not immediately treated as dirty.
        self._navigation_baseline_plan = self.current_plan()
        self._refresh_action_availability()

    def clear_plan(self) -> None:
        super().clear_plan()
        if not hasattr(self, "assignment_table"):
            return
        for row in range(self.assignment_table.rowCount()):
            self._refresh_assignment_player(row)
            self._set_assignment_text(row, 2, "")
            self._set_assignment_text(row, 3, "")
        self._update_summary()


__all__ = [
    "RaidPlanAssignmentPage",
    "merge_plan_assignment_values",
    "raid_plan_assignment_choices",
]
