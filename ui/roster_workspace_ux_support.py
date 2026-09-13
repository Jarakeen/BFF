from __future__ import annotations

"""Make Roster read like a raid-lead workflow instead of a data schema.

Top-level ownership becomes:

Roster -> who is on the roster and how to edit them
Teams -> team overview plus schedule/management
Assignments -> what the selected people are doing
People & Builds -> canonical Player -> Character -> Build browser

The existing widgets and services remain authoritative. This layer only relocates
and labels the already-working surfaces so no second roster/team model is created.
"""

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget

from ui.components.foundry_card import FoundryCard


_INSTALLED = False


def _tab_by_text(tabs: QTabWidget, text: str) -> QWidget | None:
    target = text.strip().casefold()
    for index in range(tabs.count()):
        if tabs.tabText(index).strip().casefold() == target:
            return tabs.widget(index)
    return None


def _switch_to_roster(page) -> None:
    for index in range(page.tabs.count()):
        if page.tabs.tabText(index).strip().casefold() == "roster":
            page.tabs.setCurrentIndex(index)
            return


def _add_player(page) -> None:
    _switch_to_roster(page)
    page.new_member()
    record = getattr(page, "record", None)
    if record is not None and hasattr(record, "player_name"):
        record.player_name.setFocus()


def _import_roster(page) -> None:
    from ui.roster_import_workflow import _import_roster_from_file

    _import_roster_from_file(page)


def _open_comp_maker(page) -> None:
    """Navigate to the existing Comp Maker; its Send to Roster remains authoritative."""
    window = page.window()
    show_page = getattr(window, "show_page", None)
    if callable(show_page):
        show_page("comp_builder")
        return
    page.status.warning("Comp Maker navigation is unavailable from this window.")


def _polish_existing_roster_actions(page) -> None:
    actions = getattr(page, "actions", None)
    if actions is not None:
        if hasattr(actions, "new_button"):
            actions.new_button.setVisible(False)
        if hasattr(actions, "save_button"):
            actions.save_button.setText("Save Player")
        if hasattr(actions, "delete_button"):
            actions.delete_button.setText("Remove Player")
            actions.delete_button.setToolTip("Remove the selected roster member.")

    # Assignment removal previously deleted the underlying roster member, which
    # is not an assignment-edit action. Keep deletion on the Roster tab instead.
    remove_assignment = getattr(page, "remove_assignment_button", None)
    if remove_assignment is not None:
        remove_assignment.setVisible(False)

    # The importer now has an obvious home on Roster, so hide the duplicate
    # Assignments header copy after the existing importer has finished wiring it.
    assignments = _tab_by_text(page.tabs, "ASSIGNMENTS")
    if assignments is not None:
        for button in assignments.findChildren(QPushButton):
            if button.text().strip().casefold() == "import roster":
                button.setVisible(False)


def _install_roster_quick_actions(page, roster_tab: QWidget) -> None:
    layout = roster_tab.layout()
    if layout is None or getattr(page, "roster_quick_actions_card", None) is not None:
        return

    card = FoundryCard("Build This Roster", "group")
    intro = QLabel(
        "Add people directly, import an existing raid sheet, or build a composition in Comp Maker and send it back here."
    )
    intro.setWordWrap(True)
    intro.setProperty("pageSubtitle", True)
    card.addWidget(intro)

    row = QHBoxLayout()
    row.setSpacing(8)

    add_player = QPushButton("Add Player")
    add_player.setProperty("primary", True)
    add_player.setToolTip("Start a blank roster personnel record.")
    add_player.clicked.connect(lambda _checked=False: _add_player(page))
    row.addWidget(add_player)

    import_roster = QPushButton("Import Roster")
    import_roster.setToolTip("Import Excel, CSV, or JSON with the existing review-first roster importer.")
    import_roster.clicked.connect(lambda _checked=False: _import_roster(page))
    row.addWidget(import_roster)

    comp_maker = QPushButton("Open Comp Maker")
    comp_maker.setToolTip("Build or edit a composition in Comp Maker, then use its Send to Roster workflow.")
    comp_maker.clicked.connect(lambda _checked=False: _open_comp_maker(page))
    row.addWidget(comp_maker)
    row.addStretch(1)

    card.addLayout(row)
    layout.insertWidget(0, card)

    page.roster_quick_actions_card = card
    page.roster_add_player_button = add_player
    page.roster_import_button = import_roster
    page.roster_open_comp_maker_button = comp_maker


def _merge_teams_and_schedule(page, teams_tab: QWidget, schedule_tab: QWidget) -> QWidget:
    wrapper = QWidget()
    root = QVBoxLayout(wrapper)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(8)

    intro = QLabel(
        "Team membership, current focus, and recurring raid schedule live together here."
    )
    intro.setWordWrap(True)
    intro.setProperty("pageSubtitle", True)
    root.addWidget(intro)

    sub_tabs = QTabWidget()
    sub_tabs.addTab(teams_tab, "OVERVIEW")
    sub_tabs.addTab(schedule_tab, "SCHEDULE & MANAGEMENT")
    root.addWidget(sub_tabs, 1)

    page.team_workspace_tabs = sub_tabs
    return wrapper


def _restructure_tabs(page) -> None:
    tabs = page.tabs

    assignments = _tab_by_text(tabs, "ASSIGNMENTS")
    characters = _tab_by_text(tabs, "CHARACTERS")
    personnel = _tab_by_text(tabs, "PERSONNEL")
    teams = _tab_by_text(tabs, "TEAMS")
    schedule = _tab_by_text(tabs, "TEAM SCHEDULE")

    # Fail safe: if another support layer has materially changed the roster
    # composition, leave it alone rather than reparenting the wrong widgets.
    required = (assignments, characters, personnel, teams, schedule)
    if any(widget is None for widget in required):
        return

    assert assignments is not None
    assert characters is not None
    assert personnel is not None
    assert teams is not None
    assert schedule is not None

    _polish_existing_roster_actions(page)

    while tabs.count():
        tabs.removeTab(0)

    teams_workspace = _merge_teams_and_schedule(page, teams, schedule)
    _install_roster_quick_actions(page, personnel)

    tabs.addTab(personnel, "ROSTER")
    tabs.addTab(teams_workspace, "TEAMS")
    tabs.addTab(assignments, "ASSIGNMENTS")
    tabs.addTab(characters, "PEOPLE & BUILDS")
    tabs.setCurrentWidget(personnel)

    header = getattr(page, "header", None)
    if header is not None:
        if hasattr(header, "set_title"):
            header.set_title("Roster")
        elif hasattr(header, "title_label"):
            header.title_label.setText("Roster")
        if hasattr(header, "subtitle_label"):
            header.subtitle_label.setText(
                "People, teams, assignments, schedules, characters, and builds."
            )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original_build_ui = RosterPage._build_ui

    def build_ui_with_roster_workspace(self) -> None:
        original_build_ui(self)
        _restructure_tabs(self)

    RosterPage._build_ui = build_ui_with_roster_workspace
    _INSTALLED = True
