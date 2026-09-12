from __future__ import annotations

"""Navigate from one roster/personnel player to that player's saved builds.

The roster owns raid-personnel records while the canonical build catalog owns
Player -> Character -> Build identity.  This UI bridge navigates by Gamertag
without creating another identity store or copying build state into roster data.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QPushButton

_INSTALLED = False


def _text(value) -> str:
    return str(value or "").strip()


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from ui.main_window import MainWindow
    from ui.themed_roster_page import RosterPage

    original_builds_refresh = BuildsPage._refresh_roster
    original_builds_select = BuildsPage._select_member
    original_roster_build_ui = RosterPage._build_ui
    original_show_page = MainWindow.show_page

    def refresh_roster_for_player(self, *_args) -> None:
        gamertag = _text(getattr(self, "_player_build_filter", ""))
        if not gamertag:
            original_builds_refresh(self, *_args)
            return

        wanted = gamertag.casefold()
        matching_indexes = [
            index
            for index, build in enumerate(self.roster.Members)
            if _text(getattr(build, "Gamertag", "")).casefold() == wanted
        ]

        self.roster_list.blockSignals(True)
        self.roster_list.clear()
        for index in matching_indexes:
            build = self.roster.Members[index]
            character = _text(getattr(build, "Name", "")) or "Unnamed Character"
            build_name = _text(getattr(build, "BuildName", "")) or "Default"
            role = _text(getattr(build, "Role", ""))
            label = f"{character} — {build_name}"
            if role:
                label += f"   {role}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setToolTip(
                f"{_text(getattr(build, 'EsoClass', '')) or 'Class not set'} • @{gamertag}"
            )
            self.roster_list.addItem(item)
        self.roster_list.blockSignals(False)

        if matching_indexes:
            self.selected_index = matching_indexes[0]
            self.roster_list.setCurrentRow(0)
            self._refresh_detail()
            self.status.info(
                f"Showing {len(matching_indexes)} saved build(s) for {gamertag}."
            )
        else:
            self._clear_detail()
            self.status.warning(f"No saved builds found for {gamertag}.")

    def select_member_for_player(self, row: int) -> None:
        gamertag = _text(getattr(self, "_player_build_filter", ""))
        if not gamertag:
            original_builds_select(self, row)
            return
        if row < 0:
            return
        item = self.roster_list.item(row)
        if item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        try:
            index = int(index)
        except (TypeError, ValueError):
            return
        if index < 0 or index >= len(self.roster.Members):
            return
        self.selected_index = index
        self._refresh_detail()

    def show_player_builds(self, gamertag: str) -> None:
        value = _text(gamertag)
        self._player_build_filter = value
        if hasattr(self, "build_tabs"):
            self.build_tabs.setCurrentIndex(0)
        self._refresh_roster()

    def clear_player_build_filter(self) -> None:
        if not _text(getattr(self, "_player_build_filter", "")):
            return
        self._player_build_filter = ""
        self._refresh_roster()

    def roster_build_ui_with_open_builds(self) -> None:
        original_roster_build_ui(self)
        self.open_player_builds_button = QPushButton("Open Builds")
        self.open_player_builds_button.setToolTip(
            "Open this player's saved characters and builds on the Builds page."
        )
        self.open_player_builds_button.clicked.connect(self._open_selected_player_builds)
        if hasattr(self, "actions") and self.actions.layout() is not None:
            self.actions.layout().addWidget(self.open_player_builds_button)
        if hasattr(self, "table"):
            self.table.itemDoubleClicked.connect(
                lambda *_: self._open_selected_player_builds()
            )

    def open_selected_player_builds(self) -> None:
        member_id = self.table.selected_member_id() if hasattr(self, "table") else None
        if member_id is None:
            self.status.warning("Select a personnel record first.")
            return
        member = self.roster_service.get_member(int(member_id))
        if member is None:
            self.status.warning("That personnel record could not be reloaded.")
            return
        gamertag = _text(member.PlayerName)
        if not gamertag:
            self.status.warning("This personnel record does not have a Gamertag / Player Name yet.")
            return
        window = self.window()
        opener = getattr(window, "_open_player_builds", None)
        if not callable(opener):
            self.status.warning("Build navigation is not available from this window.")
            return
        opener(gamertag)

    def open_player_builds(self, gamertag: str) -> None:
        original_show_page(self, "console:2")
        builds_page = self.pages.get("console:2")
        if builds_page is None:
            return
        show_player = getattr(builds_page, "show_player_builds", None)
        if callable(show_player):
            show_player(gamertag)

    def show_page_with_build_filter_reset(self, page_name: str):
        if page_name == "console:2":
            builds_page = self.pages.get("console:2")
            clear_filter = getattr(builds_page, "clear_player_build_filter", None)
            if callable(clear_filter):
                clear_filter()
        return original_show_page(self, page_name)

    BuildsPage._refresh_roster = refresh_roster_for_player
    BuildsPage._select_member = select_member_for_player
    BuildsPage.show_player_builds = show_player_builds
    BuildsPage.clear_player_build_filter = clear_player_build_filter

    RosterPage._build_ui = roster_build_ui_with_open_builds
    RosterPage._open_selected_player_builds = open_selected_player_builds

    MainWindow._open_player_builds = open_player_builds
    MainWindow.show_page = show_page_with_build_filter_reset
    _INSTALLED = True
