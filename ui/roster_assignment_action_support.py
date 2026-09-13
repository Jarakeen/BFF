from __future__ import annotations

"""Polish Assignments layout and add raid-lead quick actions.

This layer hides the legacy Ready column, gives the assignment table useful
horizontal breathing room, and turns the old Needs Attention summary into a
flat quick-action card without introducing another roster/team model.
"""

from PySide6.QtWidgets import QGridLayout, QHeaderView, QPushButton, QSizePolicy

from engine.config import get_data_dir
from services.build_service import BuildService


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


def _send_to_comp_maker(page) -> None:
    team_name = _selected_team_name(page)
    if not team_name:
        page.status.warning("Choose a team in the Assignments team menu before sending it to Comp Maker.")
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
        page.status.warning("Choose a team in the Assignments team menu before evaluating coverage.")
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


def _open_encounters(page) -> None:
    _show_page(page, "console:1")


def _open_gear_lookup(page) -> None:
    _show_page(page, "gear_lookup")


def _clear_card_body(card) -> None:
    while card.body_layout.count():
        item = card.body_layout.takeAt(0)
        widget = item.widget()
        layout = item.layout()
        if widget is not None:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                child_widget = child.widget()
                if child_widget is not None:
                    child_widget.hide()
                    child_widget.setParent(None)
                    child_widget.deleteLater()


def _clear_card_header(card) -> None:
    """Make this a truly headerless action card, including old header actions."""
    card.set_title("")
    card.set_icon("")
    while card.header_action_layout.count():
        item = card.header_action_layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
    card.header.hide()
    card.header.setMinimumHeight(0)
    card.header.setMaximumHeight(0)


def _install_attention_actions(page) -> None:
    card = getattr(page, "attention_card", None)
    if card is None:
        return

    # Keep the card shell because it visually belongs with the other lower cards,
    # but remove every part of the old header/readiness surface.
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

    send = QPushButton("Send to Comp Maker")
    send.setProperty("primary", True)
    send.setToolTip("Carry the selected roster team into the Comp Maker workflow.")
    send.clicked.connect(lambda *_: _send_to_comp_maker(page))

    evaluate = QPushButton("Evaluate")
    evaluate.setToolTip("Open Coverage and run a quick static buff/debuff scan for the selected team's saved builds.")
    evaluate.clicked.connect(lambda *_: _evaluate_team(page))

    encounters = QPushButton("Encounter")
    encounters.setToolTip("Open the Encounters workspace.")
    encounters.clicked.connect(lambda *_: _open_encounters(page))

    gear = QPushButton("Gear Lookup")
    gear.setToolTip("Open Gear Lookup.")
    gear.clicked.connect(lambda *_: _open_gear_lookup(page))

    for button in (send, evaluate, encounters, gear):
        button.setMinimumHeight(52)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    actions.addWidget(send, 0, 0)
    actions.addWidget(evaluate, 0, 1)
    actions.addWidget(encounters, 1, 0)
    actions.addWidget(gear, 1, 1)
    card.addLayout(actions)

    page.send_to_comp_maker_button = send
    page.evaluate_team_button = evaluate
    page.open_encounter_button = encounters
    page.open_gear_lookup_button = gear


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
        # Hide rather than physically removing the model column so older export
        # and persistence code that still references column indices remains safe.
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
