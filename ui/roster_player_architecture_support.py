from __future__ import annotations

"""Present roster-owned user state as Player -> Character -> Build.

The canonical build catalog owns player/character/build identity.  Roster keeps
raid assignments and team schedules.  This layer only composes those authorities
for the raid-lead-facing Characters and Teams tabs; it does not invent identity
from presentation text.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.build_service import BuildService
from ui.components.foundry_card import FoundryCard

_INSTALLED = False
_KIND_ROLE = Qt.ItemDataRole.UserRole
_ID_ROLE = Qt.ItemDataRole.UserRole + 1


def _text(value) -> str:
    return str(value or "").strip()


def _payload_for_build(record: dict) -> dict:
    payload = record.get("payload")
    if isinstance(payload, dict):
        return payload
    legacy = record.get("legacy")
    return legacy if isinstance(legacy, dict) else {}


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original_build_ui = RosterPage._build_ui
    original_refresh = RosterPage.refresh

    def build_ui_with_player_tree(self) -> None:
        original_build_ui(self)
        self.build_library = BuildService(get_data_dir() / "builds.json")

        # Ensure legacy compatibility state has been mirrored into the canonical
        # catalog before the hierarchy is rendered.
        self.build_library.load()

        personnel_tab = self.tabs.widget(1)
        obsolete_overrides = self.tabs.widget(2)

        self.tabs.removeTab(2)
        self.tabs.removeTab(1)
        if obsolete_overrides is not None:
            obsolete_overrides.deleteLater()

        characters_tab = self._build_character_hierarchy_tab()
        teams_tab = self._build_team_overview_tab()

        self.tabs.insertTab(1, characters_tab, "CHARACTERS")
        self.tabs.insertTab(2, personnel_tab, "PERSONNEL")
        self.tabs.insertTab(3, teams_tab, "TEAMS")

    def build_character_hierarchy_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("FIND"))
        self.character_tree_search = QLineEdit()
        self.character_tree_search.setPlaceholderText(
            "Search gamertag, character, build, class, or role..."
        )
        self.character_tree_search.textChanged.connect(self._filter_character_tree)
        search_row.addWidget(self.character_tree_search, 1)
        root.addLayout(search_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        tree_card = FoundryCard("Players, Characters & Builds", "group")
        self.character_tree = QTreeWidget()
        self.character_tree.setHeaderLabels(["Identity", "Class / Role", "Teams"])
        self.character_tree.setRootIsDecorated(True)
        self.character_tree.setAlternatingRowColors(True)
        self.character_tree.setMinimumWidth(430)
        self.character_tree.currentItemChanged.connect(self._character_tree_selection_changed)
        tree_card.addWidget(self.character_tree)
        splitter.addWidget(tree_card)

        self.character_detail_card = FoundryCard("Selection", "feather")
        self.character_detail_body = QWidget()
        self.character_detail_layout = QVBoxLayout(self.character_detail_body)
        self.character_detail_layout.setContentsMargins(0, 0, 0, 0)
        self.character_detail_layout.setSpacing(7)
        self.character_detail_card.addWidget(self.character_detail_body)
        splitter.addWidget(self.character_detail_card)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter, 1)
        return page

    def build_team_overview_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        intro = QLabel(
            "Raid teams at a glance. Current Focus is entered on Team Schedule so this page reports what you actually told FoundryDock, not what it feels like guessing today."
        )
        intro.setWordWrap(True)
        intro.setProperty("pageSubtitle", True)
        root.addWidget(intro)

        self.team_overview_scroll = QScrollArea()
        self.team_overview_scroll.setWidgetResizable(True)
        self.team_overview_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.team_overview_host = QWidget()
        self.team_overview_grid = QGridLayout(self.team_overview_host)
        self.team_overview_grid.setContentsMargins(0, 0, 0, 0)
        self.team_overview_grid.setHorizontalSpacing(10)
        self.team_overview_grid.setVerticalSpacing(10)
        self.team_overview_grid.setColumnStretch(0, 1)
        self.team_overview_grid.setColumnStretch(1, 1)
        self.team_overview_scroll.setWidget(self.team_overview_host)
        root.addWidget(self.team_overview_scroll, 1)
        return page

    def clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            nested = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif nested is not None:
                clear_layout(nested)

    def refresh_character_tree(self) -> None:
        if not hasattr(self, "character_tree"):
            return
        selected_kind = ""
        selected_id = ""
        current = self.character_tree.currentItem()
        if current is not None:
            selected_kind = _text(current.data(0, _KIND_ROLE))
            selected_id = _text(current.data(0, _ID_ROLE))

        catalog = self.build_library.canonical.catalog_service.load()
        players = {
            _text(player.get("player_id")): player
            for player in catalog.get("players", [])
            if isinstance(player, dict) and _text(player.get("player_id"))
        }
        characters_by_player: dict[str, list[dict]] = {}
        for character in catalog.get("characters", []):
            if not isinstance(character, dict):
                continue
            characters_by_player.setdefault(_text(character.get("player_id")), []).append(character)
        builds_by_character: dict[str, list[dict]] = {}
        for build in catalog.get("builds", []):
            if not isinstance(build, dict):
                continue
            builds_by_character.setdefault(_text(build.get("character_id")), []).append(build)
        assignments_by_build: dict[str, list[dict]] = {}
        for assignment in catalog.get("team_assignments", []):
            if not isinstance(assignment, dict):
                continue
            assignments_by_build.setdefault(_text(assignment.get("build_id")), []).append(assignment)

        self.character_tree.blockSignals(True)
        self.character_tree.clear()
        restore_item = None

        for player_id, player in sorted(
            players.items(), key=lambda row: _text(row[1].get("gamertag")).casefold()
        ):
            gamertag = _text(player.get("gamertag")) or "Unnamed Player"
            characters = sorted(
                characters_by_player.get(player_id, []),
                key=lambda row: _text(row.get("name")).casefold(),
            )
            player_build_count = sum(
                len(builds_by_character.get(_text(character.get("character_id")), []))
                for character in characters
            )
            player_item = QTreeWidgetItem(
                [gamertag, f"{len(characters)} character(s)", f"{player_build_count} build(s)"]
            )
            player_item.setData(0, _KIND_ROLE, "player")
            player_item.setData(0, _ID_ROLE, player_id)
            self.character_tree.addTopLevelItem(player_item)

            if selected_kind == "player" and selected_id == player_id:
                restore_item = player_item

            for character in characters:
                character_id = _text(character.get("character_id"))
                builds = sorted(
                    builds_by_character.get(character_id, []),
                    key=lambda row: _text(row.get("name")).casefold(),
                )
                roles = sorted(
                    {
                        _text(_payload_for_build(build).get("Role"))
                        for build in builds
                        if _text(_payload_for_build(build).get("Role"))
                    }
                )
                class_text = _text(character.get("eso_class")) or "Class not set"
                role_text = ", ".join(roles) or _text(character.get("role")) or "Role not set"
                character_item = QTreeWidgetItem(
                    [_text(character.get("name")) or "Unnamed Character", class_text, role_text]
                )
                character_item.setData(0, _KIND_ROLE, "character")
                character_item.setData(0, _ID_ROLE, character_id)
                player_item.addChild(character_item)
                if selected_kind == "character" and selected_id == character_id:
                    restore_item = character_item

                for build in builds:
                    build_id = _text(build.get("build_id"))
                    payload = _payload_for_build(build)
                    assignments = assignments_by_build.get(build_id, [])
                    teams = sorted(
                        {_text(row.get("team_name")) for row in assignments if _text(row.get("team_name"))}
                    )
                    build_item = QTreeWidgetItem(
                        [
                            _text(build.get("name")) or "Default",
                            _text(payload.get("Role")) or "Role not set",
                            ", ".join(teams) or "Unassigned",
                        ]
                    )
                    build_item.setData(0, _KIND_ROLE, "build")
                    build_item.setData(0, _ID_ROLE, build_id)
                    character_item.addChild(build_item)
                    if selected_kind == "build" and selected_id == build_id:
                        restore_item = build_item

        self.character_tree.expandToDepth(1)
        self.character_tree.resizeColumnToContents(0)
        self.character_tree.blockSignals(False)
        self._filter_character_tree()
        if restore_item is not None:
            self.character_tree.setCurrentItem(restore_item)
        elif self.character_tree.topLevelItemCount():
            self.character_tree.setCurrentItem(self.character_tree.topLevelItem(0))
        else:
            self._show_character_detail(None)

    def filter_character_tree(self, *_args) -> None:
        if not hasattr(self, "character_tree"):
            return
        query = self.character_tree_search.text().strip().casefold()

        def apply(item: QTreeWidgetItem) -> bool:
            child_match = False
            for index in range(item.childCount()):
                child_match = apply(item.child(index)) or child_match
            own = " ".join(item.text(column) for column in range(item.columnCount())).casefold()
            matched = not query or query in own or child_match
            item.setHidden(not matched)
            if query and child_match:
                item.setExpanded(True)
            return matched

        for index in range(self.character_tree.topLevelItemCount()):
            apply(self.character_tree.topLevelItem(index))

    def character_tree_selection_changed(self, current, _previous=None) -> None:
        self._show_character_detail(current)

    def show_character_detail(self, item) -> None:
        clear_layout(self.character_detail_layout)
        if item is None:
            self.character_detail_card.set_title("Selection")
            self.character_detail_layout.addWidget(QLabel("No player, character, or build is selected."))
            self.character_detail_layout.addStretch(1)
            return

        kind = _text(item.data(0, _KIND_ROLE))
        identity = _text(item.data(0, _ID_ROLE))
        catalog_service = self.build_library.canonical.catalog_service

        if kind == "player":
            player = catalog_service.get_player(identity) or {}
            characters = catalog_service.characters_for_player(identity)
            build_count = sum(
                len(catalog_service.builds_for_character(_text(character.get("character_id"))))
                for character in characters
            )
            gamertag = _text(player.get("gamertag")) or "Unnamed Player"
            self.character_detail_card.set_title(gamertag)
            lines = [
                f"Characters: {len(characters)}",
                f"Saved builds: {build_count}",
                f"Status: {_text(player.get('status')) or 'Active'}",
            ]
            self.character_detail_layout.addWidget(QLabel("\n".join(lines)))

        elif kind == "character":
            character = catalog_service.get_character(identity) or {}
            player = catalog_service.player_for_character(identity) or {}
            builds = catalog_service.builds_for_character(identity)
            name = _text(character.get("name")) or "Unnamed Character"
            self.character_detail_card.set_title(name)
            self.character_detail_layout.addWidget(
                QLabel(
                    f"Player: {_text(player.get('gamertag')) or 'Unknown'}\n"
                    f"Class: {_text(character.get('eso_class')) or 'Not set'}\n"
                    f"Race: {_text(character.get('race')) or 'Not set'}\n"
                    f"Alliance: {_text(character.get('alliance')) or 'Not set'}\n"
                    f"Saved builds: {len(builds)}"
                )
            )

        elif kind == "build":
            build = catalog_service.get_build(identity) or {}
            payload = _payload_for_build(build)
            character = catalog_service.get_character(_text(build.get("character_id"))) or {}
            player = catalog_service.player_for_character(_text(build.get("character_id"))) or {}
            assignments = catalog_service.assignments_for_build(identity)
            name = _text(build.get("name")) or "Default"
            self.character_detail_card.set_title(name)
            self.character_detail_layout.addWidget(
                QLabel(
                    f"Player: {_text(player.get('gamertag')) or 'Unknown'}\n"
                    f"Character: {_text(character.get('name')) or 'Unknown'}\n"
                    f"Role: {_text(payload.get('Role')) or 'Not set'}\n"
                    f"Class: {_text(character.get('eso_class')) or _text(payload.get('EsoClass')) or 'Not set'}"
                )
            )
            heading = QLabel("TEAM ASSIGNMENTS")
            heading.setProperty("sidebarHeading", True)
            self.character_detail_layout.addWidget(heading)
            if assignments:
                for assignment in assignments:
                    team = _text(assignment.get("team_name"))
                    role = _text(assignment.get("raid_role"))
                    slot = _text(assignment.get("slot_name"))
                    details = " · ".join(piece for piece in (role, slot) if piece)
                    self.character_detail_layout.addWidget(
                        QLabel(f"{team}{'  ·  ' + details if details else ''}")
                    )
            else:
                unassigned = QLabel("Not assigned to a team yet.")
                unassigned.setProperty("muted", True)
                self.character_detail_layout.addWidget(unassigned)

        self.character_detail_layout.addStretch(1)

    def refresh_team_cards(self) -> None:
        if not hasattr(self, "team_overview_grid"):
            return
        clear_layout(self.team_overview_grid)
        schedules = self.roster_service.list_team_schedules()
        if not schedules:
            empty = FoundryCard("No Teams Yet", "group")
            note = QLabel(
                "Create a team on Team Schedule. It will appear here with its current focus and raid times."
            )
            note.setWordWrap(True)
            empty.addWidget(note)
            self.team_overview_grid.addWidget(empty, 0, 0, 1, 2)
            return

        catalog_service = self.build_library.canonical.catalog_service
        for index, schedule in enumerate(schedules):
            card = FoundryCard(schedule.TeamName, "group").set_watermark("compass", 0.035)

            focus_label = QLabel(schedule.CurrentFocus or "Current focus not set")
            focus_label.setWordWrap(True)
            focus_label.setProperty("overviewGoalName", True)
            card.addWidget(focus_label)

            schedule_label = QLabel(schedule.display_text)
            schedule_label.setWordWrap(True)
            schedule_label.setProperty("muted", True)
            card.addWidget(schedule_label)

            assignments = catalog_service.assignments_for_team(schedule.TeamName)
            legacy_people = [
                member
                for member in self.members
                if schedule.TeamName.casefold()
                in {part.strip().casefold() for part in _text(member.Team).split(",") if part.strip()}
            ]
            counts = QLabel(
                f"Build assignments: {len(assignments)}\n"
                f"Personnel records: {len(legacy_people)}"
            )
            counts.setProperty("muted", True)
            card.addWidget(counts)

            if assignments:
                card.addWidget(QLabel("Assigned builds"))
                for assignment in assignments[:6]:
                    build = catalog_service.get_build(_text(assignment.get("build_id"))) or {}
                    character = catalog_service.get_character(_text(build.get("character_id"))) or {}
                    player = catalog_service.player_for_character(_text(build.get("character_id"))) or {}
                    label = " / ".join(
                        piece
                        for piece in (
                            _text(player.get("gamertag")),
                            _text(character.get("name")),
                            _text(build.get("name")) or "Default",
                        )
                        if piece
                    )
                    card.addWidget(QLabel(f"• {label}"))
                if len(assignments) > 6:
                    more = QLabel(f"+ {len(assignments) - 6} more assignment(s)")
                    more.setProperty("muted", True)
                    card.addWidget(more)

            row, column = divmod(index, 2)
            self.team_overview_grid.addWidget(card, row, column)

        rows = (len(schedules) + 1) // 2
        self.team_overview_grid.setRowStretch(rows, 1)

    def refresh_with_player_architecture(self) -> None:
        original_refresh(self)
        if hasattr(self, "build_library"):
            # Existing Builds edits may have changed the compatibility mirror;
            # loading through the bridge keeps the canonical catalog synchronized.
            self.build_library.load()
            self._refresh_character_tree()
            self._refresh_team_cards()

    RosterPage._build_ui = build_ui_with_player_tree
    RosterPage._build_character_hierarchy_tab = build_character_hierarchy_tab
    RosterPage._build_team_overview_tab = build_team_overview_tab
    RosterPage._refresh_character_tree = refresh_character_tree
    RosterPage._filter_character_tree = filter_character_tree
    RosterPage._character_tree_selection_changed = character_tree_selection_changed
    RosterPage._show_character_detail = show_character_detail
    RosterPage._refresh_team_cards = refresh_team_cards
    RosterPage.refresh = refresh_with_player_architecture

    _INSTALLED = True
