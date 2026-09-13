from __future__ import annotations

"""Polish Assignments layout and add simple raid-lead actions.

The action card deliberately stays small: Save, Clear, Send to Comp Maker, and
Evaluate. Assignment context comes from the selected Team + optional Boss.
"""

from PySide6.QtWidgets import QComboBox, QGridLayout, QHeaderView, QPushButton, QSizePolicy

from engine.config import get_data_dir
from services.build_service import BuildService
from services.roster_assignment_context_service import RosterAssignmentContextService
from ui.roster_encounter_assignment_context_support import (
    selected_encounter_id,
    selected_encounter_name,
)


_INSTALLED = False


def _selected_team_name(page) -> str:
    team = str(getattr(page, "assignment_team_filter", "") or "").strip()
    if team:
        return team
    combo = getattr(page, "assignment_team_combo", None)
    if combo is not None:
        return str(combo.currentData() or "").strip()
    return ""


def _team_members(page, team_name: str):
    from ui.roster_team_assignment_filter_support import (
        _canonical_team_members,
        _member_belongs_to_team,
    )

    canonical = _canonical_team_members(page, team_name)
    return [
        member
        for member in page.members
        if _member_belongs_to_team(page, member, team_name, canonical)
    ]


def _show_page(page, key: str) -> bool:
    window = page.window()
    show_page = getattr(window, "show_page", None)
    if not callable(show_page):
        page.status.warning("This navigation action is only available in the main app window.")
        return False
    show_page(key)
    return True


def _member_id_for_row(page, row: int) -> int | None:
    item = page.assignment_table.item(row, 0)
    if item is None:
        return None
    try:
        value = item.data(256)  # Qt.UserRole without importing another enum surface.
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _row_field_text(page, row: int, column: int) -> str:
    widget = page.assignment_table.cellWidget(row, column)
    if isinstance(widget, QComboBox):
        return widget.currentText().strip()
    item = page.assignment_table.item(row, column)
    if item is None:
        return ""
    text = item.text().strip()
    return "" if text == "—" else text


def _save_assignments(page) -> None:
    team_name = _selected_team_name(page)
    if not team_name:
        page.status.warning("Choose a team before saving assignments.")
        return

    service = getattr(page, "assignment_context_service", None)
    if service is None:
        service = RosterAssignmentContextService(page.database)
        page.assignment_context_service = service
    encounter_id = selected_encounter_id(page)

    saved_rows = 0
    for row in range(page.assignment_table.rowCount()):
        member_id = _member_id_for_row(page, row)
        if member_id is None:
            continue
        for column, field in (
            (4, "primary_assignment"),
            (5, "secondary_assignment"),
            (6, "gear_needed"),
            (7, "notes"),
        ):
            service.set_field(
                member_id,
                team_name=team_name,
                encounter_id=encounter_id,
                field=field,
                value=_row_field_text(page, row, column),
            )
        saved_rows += 1

    context = selected_encounter_name(page) or "Team Default"
    page.status.success(f"Saved {saved_rows} assignment row(s) for {team_name} • {context}.")


def _clear_assignments(page) -> None:
    team_name = _selected_team_name(page)
    if not team_name:
        page.status.warning("Choose a team before clearing assignments.")
        return

    service = getattr(page, "assignment_context_service", None)
    if service is None:
        service = RosterAssignmentContextService(page.database)
        page.assignment_context_service = service
    encounter_id = selected_encounter_id(page)

    cleared = 0
    for row in range(page.assignment_table.rowCount()):
        member_id = _member_id_for_row(page, row)
        if member_id is None:
            continue
        service.clear_context(
            member_id,
            team_name=team_name,
            encounter_id=encounter_id,
        )
        cleared += 1

    page._populate_assignment_table()
    if encounter_id:
        page.status.success(
            f"Cleared {cleared} boss override row(s). {selected_encounter_name(page)} now inherits {team_name}'s defaults."
        )
    else:
        page.status.success(
            f"Cleared {cleared} saved team-default row(s) for {team_name}."
        )


def _send_to_comp_maker(page) -> None:
    team_name = _selected_team_name(page)
    if not team_name:
        page.status.warning("Choose a team before sending it to Comp Maker.")
        return

    members = _team_members(page, team_name)
    if not members:
        page.status.warning(f"{team_name} has no roster members to send to Comp Maker.")
        return

    window = page.window()
    comp = getattr(window, "pages", {}).get("comp_builder")
    if comp is not None and hasattr(comp, "apply_roster_team_context"):
        comp.apply_roster_team_context(team_name, members)

    if not _show_page(page, "comp_builder"):
        return

    if comp is not None and not hasattr(comp, "apply_roster_team_context"):
        comp._roster_team_context_name = team_name
        comp._roster_team_context_member_ids = tuple(
            int(member.Id) for member in members if member.Id is not None
        )
        status = getattr(comp, "status", None)
        if status is not None:
            status.info(
                f"Roster team ready for Comp Maker: {team_name} ({len(members)} player(s))."
            )


def _clean_identity(value: object) -> str:
    return str(value or "").strip().lstrip("@").casefold()


def _coverage_builds_for_team(page, members):
    builds = [
        build
        for build in BuildService(get_data_dir() / "builds.json").load().Members
        if str(getattr(build, "Name", "") or "").strip()
        or str(getattr(build, "Gamertag", "") or "").strip()
    ]

    selected = []
    unresolved = []
    for member in members:
        player_key = _clean_identity(getattr(member, "PlayerName", ""))
        character_key = _clean_identity(getattr(member, "CharacterName", ""))
        candidates = [
            build
            for build in builds
            if _clean_identity(getattr(build, "Gamertag", "")) == player_key
        ]
        if character_key:
            exact = [
                build
                for build in candidates
                if _clean_identity(getattr(build, "Name", "")) == character_key
            ]
            if exact:
                candidates = exact

        ready = [build for build in candidates if bool(getattr(build, "ReadyForRaid", False))]
        if len(ready) == 1:
            chosen = ready[0]
        elif len(candidates) == 1:
            chosen = candidates[0]
        else:
            unresolved.append(
                str(getattr(member, "PlayerName", "") or getattr(member, "CharacterName", "") or "Unnamed")
            )
            continue

        slot = str(getattr(member, "PrimaryRole", "") or getattr(member, "PlayerName", "") or "Roster")
        selected.append((slot, chosen))

    return tuple(selected), tuple(unresolved)


def _evaluate_team(page) -> None:
    team_name = _selected_team_name(page)
    if not team_name:
        page.status.warning("Choose a team before evaluating coverage.")
        return

    members = _team_members(page, team_name)
    if not members:
        page.status.warning(f"{team_name} has no roster members to evaluate.")
        return

    selected, unresolved = _coverage_builds_for_team(page, members)
    if not selected:
        page.status.warning(
            f"No unambiguous saved builds were found for {team_name}. Add or choose builds before running Coverage."
        )
        return

    if not _show_page(page, "console:7"):
        return
    window = page.window()
    coverage = getattr(window, "pages", {}).get("console:7")
    if coverage is None or not hasattr(coverage, "set_team_scope"):
        page.status.warning("Coverage opened, but the team-scope bridge is unavailable.")
        return

    coverage.set_team_scope(team_name, selected, total_slots=len(members))
    if unresolved:
        coverage.status.warning(
            f"Coverage scanned {len(selected)}/{len(members)} roster member(s). "
            f"Build selection is unresolved for: {', '.join(unresolved[:6])}"
        )
    else:
        coverage.status.success(
            f"Coverage scan loaded {team_name}: {len(selected)} saved build(s)."
        )


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child_layout = item.layout()
        if widget is not None:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        elif child_layout is not None:
            _clear_layout(child_layout)


def _clear_card_body(card) -> None:
    _clear_layout(card.body_layout)


def _clear_card_header(card) -> None:
    """Make the action card truly headerless, including any stale header button."""
    card.set_title("")
    card.set_icon("")
    card.set_badge("")
    _clear_layout(card.header_action_layout)
    card.header.hide()
    card.header.setMinimumHeight(0)
    card.header.setMaximumHeight(0)


def _install_attention_actions(page) -> None:
    card = getattr(page, "attention_card", None)
    if card is None:
        return

    _clear_card_header(card)
    card.setProperty("flatActionCard", True)
    card.set_watermark(None)
    card.set_body_margins(10, 10, 10, 10)
    card.set_body_spacing(8)
    _clear_card_body(card)

    actions = QGridLayout()
    actions.setContentsMargins(0, 0, 0, 0)
    actions.setHorizontalSpacing(8)
    actions.setVerticalSpacing(8)
    actions.setColumnStretch(0, 1)
    actions.setColumnStretch(1, 1)
    actions.setRowStretch(0, 1)
    actions.setRowStretch(1, 1)

    save = QPushButton("Save")
    save.setProperty("primary", True)
    save.setToolTip("Save the visible assignments for the selected team and optional boss.")
    save.clicked.connect(lambda *_: _save_assignments(page))

    clear = QPushButton("Clear")
    clear.setToolTip(
        "Clear this context. On a boss, this restores the team's default assignments."
    )
    clear.clicked.connect(lambda *_: _clear_assignments(page))

    send = QPushButton("Send to Comp Maker")
    send.setToolTip("Carry the selected roster team into Comp Maker.")
    send.clicked.connect(lambda *_: _send_to_comp_maker(page))

    evaluate = QPushButton("Evaluate")
    evaluate.setToolTip("Run Coverage for the selected team's saved builds.")
    evaluate.clicked.connect(lambda *_: _evaluate_team(page))

    for button in (save, clear, send, evaluate):
        button.setMinimumHeight(52)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    actions.addWidget(save, 0, 0)
    actions.addWidget(clear, 0, 1)
    actions.addWidget(send, 1, 0)
    actions.addWidget(evaluate, 1, 1)
    card.addLayout(actions)

    page.save_assignments_button = save
    page.clear_assignments_button = clear
    page.send_to_comp_maker_button = send
    page.evaluate_team_button = evaluate


def _configure_assignment_table(page) -> None:
    table = getattr(page, "assignment_table", None)
    if table is None:
        return

    ready_column = -1
    for column in range(table.columnCount()):
        item = table.horizontalHeaderItem(column)
        if item is not None and item.text().strip().casefold() == "ready":
            ready_column = column
            break
    if ready_column >= 0:
        table.setColumnHidden(ready_column, True)

    table.setMinimumHeight(500)
    header = table.horizontalHeader()
    header.setMinimumSectionSize(84)
    header.setStretchLastSection(False)

    for column in range(table.columnCount()):
        if column == ready_column:
            continue
        if column in {0, 1, 2}:
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        else:
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original_build_assignments_tab = RosterPage._build_assignments_tab
    original_refresh_summary_cards = RosterPage._refresh_summary_cards

    def build_assignments_tab_with_actions(self):
        page = original_build_assignments_tab(self)
        _configure_assignment_table(self)
        return page

    def refresh_summary_cards_with_actions(self):
        result = original_refresh_summary_cards(self)
        _install_attention_actions(self)
        return result

    RosterPage._build_assignments_tab = build_assignments_tab_with_actions
    RosterPage._refresh_summary_cards = refresh_summary_cards_with_actions
    _INSTALLED = True
