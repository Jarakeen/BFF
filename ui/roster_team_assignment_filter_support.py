from __future__ import annotations

"""Let a Teams-card selection scope the Assignments table to that team.

This is presentation-only state. Team membership continues to come from the
existing roster records and canonical build-team assignments; no duplicate team
or assignment persistence is introduced here.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from ui.components.foundry_card import FoundryCard


_INSTALLED = False


def _legacy_team_names(value: str) -> set[str]:
    return {
        piece.strip().casefold()
        for piece in str(value or "").split(",")
        if piece.strip()
    }


def _canonical_team_players(page, team_name: str) -> set[str]:
    build_library = getattr(page, "build_library", None)
    if build_library is None:
        return set()

    catalog = build_library.canonical.catalog_service
    players: set[str] = set()
    for assignment in catalog.assignments_for_team(team_name):
        build = catalog.get_build(str(assignment.get("build_id") or "").strip()) or {}
        character_id = str(build.get("character_id") or "").strip()
        if not character_id:
            continue
        player = catalog.player_for_character(character_id) or {}
        gamertag = str(player.get("gamertag") or "").strip()
        if gamertag:
            players.add(gamertag.casefold())
    return players


def _member_belongs_to_team(page, member, team_name: str, canonical_players: set[str]) -> bool:
    team_key = team_name.strip().casefold()
    if not team_key:
        return True
    if team_key in _legacy_team_names(getattr(member, "Team", "")):
        return True
    player_name = str(getattr(member, "PlayerName", "") or "").strip().casefold()
    return bool(player_name and player_name in canonical_players)


def _assignment_tab_index(page) -> int:
    for index in range(page.tabs.count()):
        if page.tabs.tabText(index).strip().casefold() == "assignments":
            return index
    return -1


def _set_clear_filter_visibility(page) -> None:
    button = getattr(page, "assignment_all_teams_button", None)
    if button is not None:
        button.setVisible(bool(getattr(page, "assignment_team_filter", "")))


def _clear_team_filter(page) -> None:
    page.assignment_team_filter = ""
    _set_clear_filter_visibility(page)
    page._populate_assignment_table()
    page.status.info("Assignments showing all roster members.")


def _select_team_for_assignments(page, team_name: str) -> None:
    team_name = str(team_name or "").strip()
    if not team_name:
        return
    page.assignment_team_filter = team_name
    _set_clear_filter_visibility(page)
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
            button = QPushButton("All Teams")
            button.setToolTip("Clear the selected team and show every roster member.")
            button.clicked.connect(lambda _checked=False: _clear_team_filter(self))
            button.setVisible(False)
            card.header_action_layout.addWidget(button)
            self.assignment_all_teams_button = button
        return page

    def populate_assignment_table_with_team_scope(self, *args, **kwargs):
        team_name = str(getattr(self, "assignment_team_filter", "") or "").strip()
        if not team_name:
            return original_populate_assignment_table(self, *args, **kwargs)

        canonical_players = _canonical_team_players(self, team_name)
        original_members = self.members
        try:
            self.members = [
                member
                for member in original_members
                if _member_belongs_to_team(self, member, team_name, canonical_players)
            ]
            return original_populate_assignment_table(self, *args, **kwargs)
        finally:
            self.members = original_members

    def refresh_team_cards_with_assignment_filter(self):
        result = original_refresh_team_cards(self)
        _wire_team_cards(self)
        return result

    RosterPage._build_assignments_tab = build_assignments_tab_with_team_scope
    RosterPage._populate_assignment_table = populate_assignment_table_with_team_scope
    RosterPage._refresh_team_cards = refresh_team_cards_with_assignment_filter
    _INSTALLED = True
