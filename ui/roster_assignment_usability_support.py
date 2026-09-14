from __future__ import annotations

"""Small usability improvements for Roster -> Assignments.

Player, Role, and Class headers sort alphabetically without enabling live sorting
while rows are being populated. The optional Boss selector is upgraded to the
same searchable contains-matching combo behavior used elsewhere in FoundryDock.
Reviewed raid-planning identities replace their raw member bosses, while unrelated
encounters remain available.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter

from engine.config import get_data_dir
from services.encounter_repository import EncounterRepository
from services.raid_encounter_identity_service import load_raid_encounter_identities


_INSTALLED = False
_SORTABLE_COLUMNS = {0: "Player", 1: "Role", 2: "Class"}


def _encounter_choices() -> tuple[tuple[str, str], ...]:
    data_root = get_data_dir()
    try:
        identities = load_raid_encounter_identities(data_root)
    except Exception:
        identities = ()

    choices: list[tuple[str, str]] = [
        (row.display_name, row.encounter_id) for row in identities
    ]
    represented_ids = {
        encounter_id
        for row in identities
        for encounter_id in (row.encounter_id, *row.member_ids)
    }

    # Keep dungeon/add-pull/other canonical encounters that do not have reviewed
    # raid-planning identities. Reviewed grouped identities replace only their own
    # member records, so Lylanar/Turlassil (for example) appear once as a fight.
    try:
        repository = EncounterRepository.from_data_root(data_root)
        for encounter_id in repository.encounter_ids():
            if encounter_id in represented_ids:
                continue
            try:
                definition = repository.get(encounter_id)
            except Exception:
                continue
            name = str(definition.name or encounter_id).strip()
            if name:
                choices.append((name, encounter_id))
    except Exception:
        pass

    unique: dict[str, tuple[str, str]] = {}
    for name, encounter_id in choices:
        unique.setdefault(str(encounter_id).casefold(), (name, encounter_id))
    return tuple(sorted(unique.values(), key=lambda item: item[0].casefold()))


def _configure_boss_combo(page) -> None:
    combo = getattr(page, "assignment_encounter_combo", None)
    if not isinstance(combo, QComboBox):
        return

    current_id = str(combo.currentData() or "").strip()
    combo.blockSignals(True)
    try:
        combo.clear()
        combo.addItem("Team Default (most common)", "")
        for name, encounter_id in _encounter_choices():
            combo.addItem(name, encounter_id)
        index = combo.findData(current_id) if current_id else 0
        combo.setCurrentIndex(index if index >= 0 else 0)

        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setDuplicatesEnabled(False)
        if combo.lineEdit() is not None:
            combo.lineEdit().setClearButtonEnabled(True)
            combo.lineEdit().setPlaceholderText("Type to find boss…")
        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)
    finally:
        combo.blockSignals(False)


def _sort_assignments(page, column: int) -> None:
    if column not in _SORTABLE_COLUMNS:
        return
    table = getattr(page, "assignment_table", None)
    if table is None:
        return

    previous_column = getattr(page, "_assignment_sort_column", None)
    previous_order = getattr(page, "_assignment_sort_order", Qt.SortOrder.AscendingOrder)
    if previous_column == column:
        order = (
            Qt.SortOrder.DescendingOrder
            if previous_order == Qt.SortOrder.AscendingOrder
            else Qt.SortOrder.AscendingOrder
        )
    else:
        order = Qt.SortOrder.AscendingOrder

    page._assignment_sort_column = column
    page._assignment_sort_order = order
    table.sortItems(column, order)
    table.horizontalHeader().setSortIndicator(column, order)


def _apply_saved_sort(page) -> None:
    table = getattr(page, "assignment_table", None)
    column = getattr(page, "_assignment_sort_column", None)
    if table is None or column not in _SORTABLE_COLUMNS:
        return
    order = getattr(page, "_assignment_sort_order", Qt.SortOrder.AscendingOrder)
    table.sortItems(column, order)
    table.horizontalHeader().setSortIndicator(column, order)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original_build_assignments_tab = RosterPage._build_assignments_tab
    original_populate_assignment_table = RosterPage._populate_assignment_table

    def build_assignments_tab_with_usability(self):
        page = original_build_assignments_tab(self)
        table = getattr(self, "assignment_table", None)
        if table is not None:
            header = table.horizontalHeader()
            header.setSectionsClickable(True)
            header.setSortIndicatorShown(True)
            header.sectionClicked.connect(lambda column: _sort_assignments(self, column))
        _configure_boss_combo(self)
        return page

    def populate_assignment_table_with_usability(self, *args, **kwargs):
        result = original_populate_assignment_table(self, *args, **kwargs)
        _apply_saved_sort(self)
        return result

    RosterPage._build_assignments_tab = build_assignments_tab_with_usability
    RosterPage._populate_assignment_table = populate_assignment_table_with_usability
    _INSTALLED = True


__all__ = ["install"]
