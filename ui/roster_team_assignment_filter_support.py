from __future__ import annotations

"""Let a Teams-card selection scope the Assignments table to that team.

This is presentation-only state. Team membership continues to come from the
existing roster records and canonical build-team assignments; no duplicate team
or assignment persistence is introduced here.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox

from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ALL_TEAMS_LABEL = "All Teams"


def _legacy_team_names(value: str) -> set[str]:
    return {
        piece.strip().casefold()
        for piece in str(value or "").split(",")
        if piece.strip()
    }


def _canonical_team_members(page, team_name: str) -> set[tuple[str, str]]:
    build_library = getattr(page, "build_library", None)
    if build_library is None:
        return set()

    catalog = build_library.canonical.catalog_service
    members: set[tuple[str, str]] = set()
    for assignment in catalog.assignments_for_team(team_name):
        build = catalog.get_build(str(assignment.get("build_id") or "").strip()) or {}
        character_id = str(build.get("character_id") or "").strip()
        if not character_id:
            continue
        character = catalog.get_character(character_id) or {}
        player = catalog.player_for_character(character_id) or {}
        gamertag = str(player.get("gamertag") or "").strip().casefold()
        character_name = str(character.get("name") or "").strip().casefold()
        if gamertag:
            members.add((gamertag, character_name))
    return members


def _member_belongs_to_team(page, member, team_name: str, canonical_members: set[tuple[str, str]]) -> bool:
    team_key = team_name.strip().casefold()
    if not team_key:
        return True
    if team_key in _legacy_team_names(getattr(member, "Team", "")):
        return True

    player_name = str(getattr(member, "PlayerName", "") or "").strip().casefold()
    character_name = str(getattr(member, "CharacterName", "") or "").strip().casefold()
    if not player_name:
        return False

    # Prefer exact Player + Character identity. A player-only fallback is kept
    # for older personnel records that predate character identity persistence.
    if (player_name, character_name) in canonical_members:
        return True
    return not character_name and any(player == player_name for player, _ in canonical_members)


def _assignment_tab_index(page) -> int:
    for index in range(page.tabs.count()):
        if page.tabs.tabText(index).strip().casefold() == "assignments":
            return index
    return -1


def _team_names(page) -> list[str]:
    names = {
        str(name or "").strip()
        for name in page.roster_service.list_team_names()
        if str(name or "").strip()
    }

    build_library = getattr(page, "build_library", None)
    if build_library is not None:
        catalog = build_library.canonical.catalog_service.load()
        for assignment in catalog.get("team_assignments", []):
            if not isinstance(assignment, dict):
                continue
            name = str(assignment.get("team_name") or "").strip()
            if name:
                names.add(name)

    return sorted(names, key=str.casefold)


def _refresh_team_selector(page) -> None:
    combo = getattr(page, "assignment_team_combo", None)
    if combo is None:
        return

    selected = str(getattr(page, "assignment_team_filter", "") or "").strip()
    combo.blockSignals(True)
    try:
        combo.clear()
        combo.addItem(_ALL_TEAMS_LABEL, "")
        for team_name in _team_names(page):
            combo.addItem(team_name, team_name)
        if selected:
            index = combo.findData(selected)
            if index < 0:
                combo.addItem(selected, selected)
                index = combo.count() - 1
            combo.setCurrentIndex(index)
        else:
            combo.setCurrentIndex(0)
    finally:
        combo.blockSignals(False)


def _team_selector_changed(page, index: int) -> None:
    combo = getattr(page, "assignment_team_combo", None)
    if combo is None or index < 0:
        return

    team_name = str(combo.itemData(index) or "").strip()
    page.assignment_team_filter = team_name
    page._populate_assignment_table()
    if team_name:
        page.status.info(f"Assignments filtered to {team_name}.")
    else:
        page.status.info("Assignments showing all roster members.")


def _select_team_for_assignments(page, team_name: str) -> None:
    team_name = str(team_name or "").strip()
    if not team_name:
        return

    page.assignment_team_filter = team_name
    _refresh_team_selector(page)
    page._populate_assignment_table()

    index = _assignment_tab_index(page)
    if index >= 0:
        page.tabs.setCurrentIndex(index)
    page.status.info(f"Assignments filtered to {team_name}.")


def _wire_team_cards(page) -> None:
    grid = getattr(page, "team_overview_grid", None)
    if grid is None:
        return

    for index in range(grid.count()):
        widget = grid.itemAt(index).widget()
        if not isinstance(widget, FoundryCard):
            continue
        team_name = widget.title_label.text().strip()
        if not team_name or team_name.casefold() == "no teams yet":
            continue

        widget.setCursor(Qt.CursorShape.PointingHandCursor)
        widget.setToolTip(f"Show {team_name} members in Assignments")
        widget.setProperty("teamAssignmentFilterCard", True)

        # QLabel children normally ignore mouse presses, allowing the event to
        # reach the card. Making that explicit keeps the whole visual card click
        # target consistent without swallowing future buttons or controls.
        for label in widget.findChildren(type(widget.title_label)):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        original_press = widget.mousePressEvent

        def press(event, *, team=team_name, original=original_press):
            if event.button() == Qt.MouseButton.LeftButton:
                _select_team_for_assignments(page, team)
                event.accept()
                return
            original(event)

        widget.mousePressEvent = press


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original_build_assignments_tab = RosterPage._build_assignments_tab
    original_populate_assignment_table = RosterPage._populate_assignment_table
    original_refresh_team_cards = RosterPage._refresh_team_cards

    def build_assignments_tab_with_team_scope(self):
        page = original_build_assignments_tab(self)
        self.assignment_team_filter = ""

        card = next(
            (
                candidate
                for candidate in page.findChildren(FoundryCard)
                if candidate.title_label.text().strip() == "Player Assignments"
            ),
            None,
        )
        if card is not None:
            combo = QComboBox()
            combo.setMinimumWidth(180)
            combo.setToolTip("Show assignments for one saved team, or all teams.")
            combo.currentIndexChanged.connect(
                lambda index: _team_selector_changed(self, index)
            )
            card.header_action_layout.addWidget(combo)
            self.assignment_team_combo = combo
            _refresh_team_selector(self)
        return page

    def populate_assignment_table_with_team_scope(self, *args, **kwargs):
        team_name = str(getattr(self, "assignment_team_filter", "") or "").strip()
        if not team_name:
            return original_populate_assignment_table(self, *args, **kwargs)

        canonical_members = _canonical_team_members(self, team_name)
        original_members = self.members
        try:
            self.members = [
                member
                for member in original_members
                if _member_belongs_to_team(self, member, team_name, canonical_members)
            ]
            return original_populate_assignment_table(self, *args, **kwargs)
        finally:
            self.members = original_members

    def refresh_team_cards_with_assignment_filter(self):
        result = original_refresh_team_cards(self)
        _refresh_team_selector(self)
        _wire_team_cards(self)
        return result

    RosterPage._build_assignments_tab = build_assignments_tab_with_team_scope
    RosterPage._populate_assignment_table = populate_assignment_table_with_team_scope
    RosterPage._refresh_team_cards = refresh_team_cards_with_assignment_filter
    _INSTALLED = True
