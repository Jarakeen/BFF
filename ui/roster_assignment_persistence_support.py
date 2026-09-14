from __future__ import annotations

"""Persist Assignments-tab planning by team with optional boss overrides.

Team Default is the normal raid job. A selected boss creates or reads an override
for that fight. Boss rows inherit the team default until the user changes them.
All Teams remains a safe overview instead of an ambiguous editing surface.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QTableWidgetItem

from services.roster_assignment_context_service import RosterAssignmentContextService
from ui.roster_encounter_assignment_context_support import selected_encounter_id


_INSTALLED = False

_FIELD_BY_COLUMN = {
    4: "primary_assignment",
    5: "secondary_assignment",
    6: "gear_needed",
    7: "notes",
}


def _member_id_for_row(page, row: int) -> int | None:
    item = page.assignment_table.item(row, 0)
    if item is None:
        return None
    value = item.data(Qt.ItemDataRole.UserRole)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _team_name(page) -> str:
    return str(getattr(page, "assignment_team_filter", "") or "").strip()


def _context_service(page) -> RosterAssignmentContextService:
    service = getattr(page, "assignment_context_service", None)
    if service is None:
        service = RosterAssignmentContextService(page.database)
        page.assignment_context_service = service
    return service


def _persist_field(page, member_id: int | None, field: str, value: str) -> None:
    if member_id is None:
        return
    team_name = _team_name(page)
    if not team_name:
        page.status.warning("Choose a team before editing assignments.")
        return
    try:
        _context_service(page).set_field(
            member_id,
            team_name=team_name,
            encounter_id=selected_encounter_id(page),
            field=field,
            value=value,
        )
    except (OSError, ValueError) as exc:
        page.status.error(f"Could not save assignment: {exc}")


def _persist_item_edit(page, item: QTableWidgetItem) -> None:
    if getattr(page, "_loading_assignment_persistence", False):
        return
    field = _FIELD_BY_COLUMN.get(item.column())
    if field not in {"gear_needed", "notes"}:
        return
    member_id = _member_id_for_row(page, item.row())
    _persist_field(page, member_id, field, item.text())


def _set_editable(item: QTableWidgetItem | None, editable: bool) -> None:
    if item is None:
        return
    flags = item.flags()
    if editable:
        flags |= Qt.ItemFlag.ItemIsEditable
    else:
        flags &= ~Qt.ItemFlag.ItemIsEditable
    item.setFlags(flags)


def _restore_row(page, row: int) -> None:
    member_id = _member_id_for_row(page, row)
    if member_id is None:
        return

    team_name = _team_name(page)
    encounter_id = selected_encounter_id(page)
    if team_name:
        saved = _context_service(page).get_effective_assignment(
            member_id,
            team_name=team_name,
            encounter_id=encounter_id,
            legacy_service=page.roster_service,
        )
    else:
        saved = page.roster_service.get_member_assignment(member_id)
        saved["_source"] = "overview"
        saved["_inherited"] = False
        saved["_encounter_fields"] = ()

    role_item = page.assignment_table.item(row, 1)
    role = role_item.text().strip() if role_item is not None else ""
    defaults = {
        "primary_assignment": page._default_assignment(role),
        "secondary_assignment": page._secondary_assignment(role),
    }

    for column, field in ((4, "primary_assignment"), (5, "secondary_assignment")):
        combo = page.assignment_table.cellWidget(row, column)
        if not isinstance(combo, QComboBox):
            continue
        value = str(saved.get(field, "") or defaults[field])
        combo.blockSignals(True)
        combo.setCurrentText(value)
        combo.setEnabled(bool(team_name))
        combo.setToolTip("")
        combo.blockSignals(False)
        backing = page.assignment_table.item(row, column)
        if backing is not None:
            backing.setText(value)
        combo.currentTextChanged.connect(
            lambda text, member_id=member_id, field=field: _persist_field(
                page, member_id, field, text
            )
        )

    gear = str(saved.get("gear_needed", "") or "")
    notes = str(saved.get("notes", "") or "")
    gear_item = page.assignment_table.item(row, 6)
    notes_item = page.assignment_table.item(row, 7)
    if gear_item is not None:
        gear_item.setText(gear or "—")
        _set_editable(gear_item, bool(team_name))
        gear_item.setToolTip("")
    if notes_item is not None:
        notes_item.setText(notes)
        _set_editable(notes_item, bool(team_name))
        notes_item.setToolTip("")


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original_build_assignments_tab = RosterPage._build_assignments_tab
    original_populate_assignment_table = RosterPage._populate_assignment_table

    def build_assignments_tab_with_persistence(self):
        page = original_build_assignments_tab(self)
        self.assignment_context_service = RosterAssignmentContextService(self.database)
        self.assignment_table.itemChanged.connect(
            lambda item: _persist_item_edit(self, item)
        )
        return page

    def populate_assignment_table_with_persistence(self, *args, **kwargs):
        self._loading_assignment_persistence = True
        try:
            result = original_populate_assignment_table(self, *args, **kwargs)
            for row in range(self.assignment_table.rowCount()):
                _restore_row(self, row)
            return result
        finally:
            self._loading_assignment_persistence = False

    RosterPage._build_assignments_tab = build_assignments_tab_with_persistence
    RosterPage._populate_assignment_table = populate_assignment_table_with_persistence
    _INSTALLED = True
