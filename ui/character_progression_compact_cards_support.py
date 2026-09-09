from __future__ import annotations

"""Compact card layout for character-owned passive progression.

The original one-family-at-a-time treatment behaved like a rolodex: only one
skill family was open at a time. That was thematically cute and operationally
tiresome. This support layer keeps the same persistence and controls while
showing every skill family and passive Champion discipline as compact cards in
a multi-column grid.
"""

from collections import defaultdict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.phase5_build_ui_support import (
    CharacterProgressionDialog,
    _DISCIPLINE_NAMES,
    _clean,
    _int,
    _racial_skill_line_race,
    _set_progression_spins,
)


_INSTALLED = False
CARD_COLUMNS = 3


def _buy_all_skill_progression(dialog: CharacterProgressionDialog) -> None:
    """Unlock every optional line and max every recorded passive rank."""
    for check in dialog._line_checks.values():
        check.setChecked(True)
    _set_progression_spins(
        [spin for _name, spin in dialog._passive_spins.values()],
        "max",
    )


def _buy_all_passive_cp(dialog: CharacterProgressionDialog) -> None:
    """Max every non-slottable Champion star shown in Character Progression."""
    _set_progression_spins(
        [spin for _name, spin in dialog._cp_spins.values()],
        "max",
    )


def _line_card(dialog: CharacterProgressionDialog, line: str, rows: list[dict]) -> FoundryCard:
    card = FoundryCard(line)
    card.set_body_margins(8, 6, 8, 8)
    card.set_body_spacing(5)

    owner_values = {
        _clean(row.get("class_type"))
        for row in rows
        if _clean(row.get("class_type"))
    }
    class_line = bool(owner_values) and dialog.eso_class in owner_values
    line_race = _racial_skill_line_race(line, dialog._race_skill_lines)
    racial_line = bool(dialog.race) and line_race == dialog.race.casefold()
    intrinsic_line = class_line or racial_line

    access_row = QHBoxLayout()
    if class_line:
        access = QLabel(f"{dialog.eso_class} class line")
        access.setProperty("cardBadge", True)
        access_row.addWidget(access)
    elif racial_line:
        access = QLabel(f"{dialog.race} racial line")
        access.setProperty("cardBadge", True)
        access_row.addWidget(access)
    else:
        check = QCheckBox("Unlocked")
        check.setToolTip("This character has unlocked this skill line.")
        check.setChecked(line.casefold() in dialog._owned)
        dialog._line_checks[line] = check
        access_row.addWidget(check)
    access_row.addStretch(1)
    card.addLayout(access_row)

    passive_grid = QGridLayout()
    passive_grid.setContentsMargins(0, 0, 0, 0)
    passive_grid.setHorizontalSpacing(6)
    passive_grid.setVerticalSpacing(3)
    line_spins: list[QSpinBox] = []

    for row_index, skill in enumerate(rows):
        name = _clean(skill.get("name"))
        maximum = max(1, _int(skill.get("rank"), 1))
        stored = (
            dialog._stored_passives.get(name.casefold())
            if name.casefold() in dialog._stored_passives
            else None
        )
        spin = dialog._progression_spin(maximum=maximum, stored=stored, width=88)
        description = _clean(skill.get("description"))
        label = QLabel(name)
        label.setWordWrap(True)
        if description:
            label.setToolTip(description)
            spin.setToolTip(description)
        passive_grid.addWidget(label, row_index, 0)
        passive_grid.addWidget(spin, row_index, 1)
        passive_grid.setColumnStretch(0, 1)
        dialog._passive_spins[name.casefold()] = (name, spin)
        line_spins.append(spin)

    card.addLayout(passive_grid)

    actions = QHBoxLayout()
    actions.setContentsMargins(0, 2, 0, 0)
    actions.setSpacing(4)
    buy_all = FoundryButton("Buy All", role=ButtonRole.SECONDARY, compact=True)
    clear = FoundryButton("Clear", role=ButtonRole.GHOST, compact=True)
    unknown = FoundryButton("Unknown", role=ButtonRole.GHOST, compact=True)
    actions.addWidget(buy_all)
    actions.addWidget(clear)
    actions.addWidget(unknown)
    actions.addStretch(1)
    card.addLayout(actions)

    def buy_line(*_args, spins=line_spins, skill_line=line, intrinsic=intrinsic_line) -> None:
        if not intrinsic and skill_line in dialog._line_checks:
            dialog._line_checks[skill_line].setChecked(True)
        _set_progression_spins(spins, "max")

    buy_all.clicked.connect(buy_line)
    clear.clicked.connect(lambda *_args, spins=line_spins: _set_progression_spins(spins, "zero"))
    unknown.clicked.connect(lambda *_args, spins=line_spins: _set_progression_spins(spins, "unknown"))
    return card


def _cp_card(dialog: CharacterProgressionDialog, discipline: int, rows: list[dict]) -> FoundryCard:
    title = _DISCIPLINE_NAMES.get(discipline, f"Discipline {discipline}")
    card = FoundryCard(title)
    card.set_body_margins(8, 6, 8, 8)
    card.set_body_spacing(5)

    cp_grid = QGridLayout()
    cp_grid.setContentsMargins(0, 0, 0, 0)
    cp_grid.setHorizontalSpacing(6)
    cp_grid.setVerticalSpacing(3)
    discipline_spins: list[QSpinBox] = []

    for row_index, cp in enumerate(rows):
        name = _clean(cp.get("name"))
        maximum = max(1, _int(cp.get("max_points"), 1))
        stored = (
            dialog._stored_cp.get(name.casefold())
            if name.casefold() in dialog._stored_cp
            else None
        )
        spin = dialog._progression_spin(maximum=maximum, stored=stored, width=88)
        description = _clean(cp.get("description"))
        label = QLabel(name)
        label.setWordWrap(True)
        if description:
            label.setToolTip(description)
            spin.setToolTip(description)
        cp_grid.addWidget(label, row_index, 0)
        cp_grid.addWidget(spin, row_index, 1)
        cp_grid.setColumnStretch(0, 1)
        dialog._cp_spins[name.casefold()] = (name, spin)
        discipline_spins.append(spin)

    card.addLayout(cp_grid)

    actions = QHBoxLayout()
    actions.setContentsMargins(0, 2, 0, 0)
    actions.setSpacing(4)
    buy_all = FoundryButton("Buy All", role=ButtonRole.SECONDARY, compact=True)
    clear = FoundryButton("Clear", role=ButtonRole.GHOST, compact=True)
    unknown = FoundryButton("Unknown", role=ButtonRole.GHOST, compact=True)
    actions.addWidget(buy_all)
    actions.addWidget(clear)
    actions.addWidget(unknown)
    actions.addStretch(1)
    card.addLayout(actions)

    buy_all.clicked.connect(
        lambda *_args, spins=discipline_spins: _set_progression_spins(spins, "max")
    )
    clear.clicked.connect(
        lambda *_args, spins=discipline_spins: _set_progression_spins(spins, "zero")
    )
    unknown.clicked.connect(
        lambda *_args, spins=discipline_spins: _set_progression_spins(spins, "unknown")
    )
    return card


def _compact_skill_passive_tab(self: CharacterProgressionDialog) -> QWidget:
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    top_row = QHBoxLayout()
    note = QLabel(
        "All skill families are shown at once. Unknown means the rank has not been recorded; "
        "zero means explicitly not purchased. Buy All uses the database-backed maximum rank."
    )
    note.setWordWrap(True)
    note.setProperty("pageSubtitle", True)
    top_row.addWidget(note, 1)
    buy_everything = FoundryButton("Buy All", role=ButtonRole.SECONDARY, compact=True)
    buy_everything.setToolTip("Unlock every available skill line and buy every passive at its maximum rank.")
    buy_everything.clicked.connect(lambda *_: _buy_all_skill_progression(self))
    top_row.addWidget(buy_everything, 0)
    top_row.setAlignment(buy_everything, Qt.AlignmentFlag.AlignTop)
    layout.addLayout(top_row)

    cards = QGridLayout()
    cards.setContentsMargins(0, 0, 0, 0)
    cards.setHorizontalSpacing(8)
    cards.setVerticalSpacing(8)

    for index, (line, rows) in enumerate(self._passive_rows_by_line().items()):
        row = index // CARD_COLUMNS
        column = index % CARD_COLUMNS
        cards.addWidget(_line_card(self, line, rows), row, column)

    for column in range(CARD_COLUMNS):
        cards.setColumnStretch(column, 1)
    layout.addLayout(cards)
    layout.addStretch(1)
    return host


def _compact_passive_cp_tab(self: CharacterProgressionDialog) -> QWidget:
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    top_row = QHBoxLayout()
    note = QLabel(
        "Only non-slottable Champion stars appear here. Unknown means unrecorded; zero means explicitly unpurchased. "
        "The 12 slotted stars remain build-specific in the normal Champion Points editor."
    )
    note.setWordWrap(True)
    note.setProperty("pageSubtitle", True)
    top_row.addWidget(note, 1)
    buy_everything = FoundryButton("Buy All", role=ButtonRole.SECONDARY, compact=True)
    buy_everything.setToolTip("Buy every passive Champion star shown here at its database-backed maximum.")
    buy_everything.clicked.connect(lambda *_: _buy_all_passive_cp(self))
    top_row.addWidget(buy_everything, 0)
    top_row.setAlignment(buy_everything, Qt.AlignmentFlag.AlignTop)
    layout.addLayout(top_row)

    grouped: dict[int, list[dict]] = defaultdict(list)
    for cp in self.reference.list_champion_points():
        if not isinstance(cp, dict) or _int(cp.get("skill_type"), -1) != 0:
            continue
        name = _clean(cp.get("name"))
        if name:
            grouped[_int(cp.get("discipline_id"))].append(cp)

    cards = QGridLayout()
    cards.setContentsMargins(0, 0, 0, 0)
    cards.setHorizontalSpacing(8)
    cards.setVerticalSpacing(8)

    for index, discipline in enumerate(sorted(grouped)):
        rows = sorted(grouped[discipline], key=lambda value: _clean(value.get("name")).casefold())
        row = index // CARD_COLUMNS
        column = index % CARD_COLUMNS
        cards.addWidget(_cp_card(self, discipline, rows), row, column)

    for column in range(CARD_COLUMNS):
        cards.setColumnStretch(column, 1)
    layout.addLayout(cards)
    layout.addStretch(1)
    return host


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    CharacterProgressionDialog._skill_passive_tab = _compact_skill_passive_tab
    CharacterProgressionDialog._passive_cp_tab = _compact_passive_cp_tab
    _INSTALLED = True
