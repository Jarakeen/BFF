from __future__ import annotations

"""Urban Wilderness Roster entry point and final composition polish.

The underlying themed roster page owns canonical data and actions. This wrapper keeps
those data owners intact while presenting the approved single-window Roster flow: six
summary cards across the top, then either the dashboard or the selected roster detail
workspace directly underneath. No modal editor windows are used on this surface.

Roster visual contract:
- summary cards use the dedicated teal/bronze Roster medallions without ordinals;
- decorative assets never determine page/card geometry;
- Players always retains a visible people table;
- Character details remain a compact human-facing profile surface;
- canonical database IDs stay out of the visible profile card.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_card import FoundryCard
from ui.raid_roster_workspace_page import RaidRosterWorkspacePage, _clean
from ui.themed_raid_roster_workspace_page import ThemedRaidRosterWorkspacePage
from ui.urban_wilderness_accessibility_polish import install as install_urban_wilderness_accessibility_polish
from ui.ux_icons import icon
from widgets.roster_actions import RosterActions
from widgets.roster_record import RosterRecord
from widgets.roster_table import RosterTable


_BADGES = {
    "players": "roster-players",
    "characters": "roster-characters",
    "teams": "roster-teams",
    "availability": "roster-availability",
    "recruitment": "roster-recruitment",
    "archive": "roster-archive",
}


class CityRaidRosterWorkspacePage(ThemedRaidRosterWorkspacePage):
    """Compatibility route name for the single Urban Wilderness Roster dashboard."""

    def __init__(self, parent=None) -> None:
        install_urban_wilderness_accessibility_polish()
        self._embedded_detail_indexes: dict[str, int] = {}
        self._embedded_stack: QStackedWidget | None = None
        super().__init__(parent)
        self._remove_legacy_city_art()
        self._polish_urban_wilderness_roster()
        self._embed_detail_workspaces()

    # ------------------------------------------------------------------
    # Detail workspaces
    # ------------------------------------------------------------------

    def _build_detail_workspaces(self) -> None:
        """Build detail pages with a real Players list instead of a form-only dead end."""
        self.record = RosterRecord()
        self.actions = RosterActions()

        player_page = QWidget()
        player_layout = QVBoxLayout(player_page)
        player_layout.setContentsMargins(8, 8, 8, 8)
        player_layout.setSpacing(8)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)

        people_card = FoundryCard("Players", "group")
        self.player_detail_table = RosterTable()
        self.player_detail_table.memberSelected.connect(self.load_member)
        people_card.addWidget(self.player_detail_table)
        split.addWidget(people_card)

        record_card = FoundryCard("Player Record", "person")
        record_card.addWidget(self.record)
        record_card.addStretch(1)
        split.addWidget(record_card)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)

        player_layout.addWidget(split, 1)
        player_layout.addWidget(self.actions)

        self._install_detail_dialog("players", "Players", player_page, (1180, 760))

        character_page = RaidRosterWorkspacePage._build_characters_tab(self)
        self._install_character_profile_shell()
        self._install_detail_dialog("characters", "Characters", character_page, (1180, 760))

        self._install_detail_dialog(
            "teams", "Teams", RaidRosterWorkspacePage._build_teams_tab(self), (1120, 760)
        )
        self._install_detail_dialog(
            "availability",
            "Availability",
            RaidRosterWorkspacePage._build_availability_tab(self),
            (1250, 720),
        )
        self._install_detail_dialog(
            "recruitment",
            "Recruitment",
            RaidRosterWorkspacePage._build_recruitment_tab(self),
            (1180, 760),
        )
        self._install_detail_dialog(
            "archive", "Archive", RaidRosterWorkspacePage._build_archive_tab(self), (1050, 680)
        )

    def _install_character_profile_shell(self) -> None:
        """Give the nested character browser a stable portrait slot and profile composition."""
        if not hasattr(self, "character_detail") or not hasattr(self, "character_detail_body"):
            return

        layout = self.character_detail.body_layout
        layout.removeWidget(self.character_detail_body)

        profile = QWidget()
        profile.setProperty("rosterCharacterProfile", True)
        profile_layout = QHBoxLayout(profile)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(12)

        self.character_detail_avatar = QLabel()
        self.character_detail_avatar.setProperty("rosterProfileImage", True)
        self.character_detail_avatar.setFixedSize(92, 92)
        self.character_detail_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.character_detail_avatar.setToolTip(
            "Character portrait. Default themed portraits can be assigned here later."
        )
        self.character_detail_avatar.setStyleSheet(
            "background:#0A1D22; border:2px solid #4D8291; border-radius:46px; padding:8px;"
        )
        profile_layout.addWidget(self.character_detail_avatar, 0, Qt.AlignmentFlag.AlignTop)

        self.character_detail_body.setWordWrap(True)
        profile_layout.addWidget(self.character_detail_body, 1)
        layout.insertWidget(0, profile)
        self._set_profile_avatar("character")

    def _set_profile_avatar(self, kind: str) -> None:
        avatar = getattr(self, "character_detail_avatar", None)
        if avatar is None:
            return
        icon_name = {
            "player": "person",
            "character": "character",
            "build": "builds",
        }.get(kind, "character")
        value = icon(icon_name)
        avatar.clear()
        if not value.isNull():
            avatar.setPixmap(value.pixmap(70, 70))
            avatar.setProperty("semanticIconName", icon_name)

    def refresh(self) -> None:
        super().refresh()
        if hasattr(self, "player_detail_table"):
            selected_id = self.player_detail_table.selected_member_id()
            self.player_detail_table.load_members(self.members)
            if selected_id is not None:
                self.player_detail_table.select_member_id(selected_id)

    # ------------------------------------------------------------------
    # Dashboard visual contract
    # ------------------------------------------------------------------

    def _remove_legacy_city_art(self) -> None:
        """Retire the two old roster filler panels without affecting page geometry."""
        for attribute in ("quote_art", "team_art"):
            old = getattr(self, attribute, None)
            if old is None:
                continue
            parent = old.parentWidget()
            layout = parent.layout() if parent is not None else None
            if layout is not None:
                layout.removeWidget(old)
            old.hide()
            old.deleteLater()
            setattr(self, attribute, None)

    def _polish_urban_wilderness_roster(self) -> None:
        """Keep the roster compact, stable, and readable at normal desktop widths."""
        self.header.subtitle.setText("People. Characters. Teams. Ready for what's next.")
        self.header._set_icon("feather")

        for key, card in self.metric_cards.items():
            card.setMinimumWidth(0)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            card.setMinimumHeight(132)
            card.setMaximumHeight(148)

            badge = next(
                (
                    label
                    for label in card.findChildren(QLabel)
                    if bool(label.property("rosterMetricIcon"))
                ),
                None,
            )
            if badge is not None:
                badge.clear()
                badge.setFixedSize(QSize(72, 72))
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setPixmap(icon(_BADGES.get(key, "compass")).pixmap(68, 68))
                badge.setProperty("rosterMetricBadge", True)

            # The medallion itself owns the identity now. No duplicate 1–6 ordinal.
            ordinal = next(
                (
                    label
                    for label in card.findChildren(QLabel)
                    if bool(label.property("rosterMetricOrdinal"))
                ),
                None,
            )
            if ordinal is not None:
                ordinal.clear()
                ordinal.hide()
                ordinal.setFixedSize(QSize(0, 0))

        if hasattr(self, "table"):
            self._polish_roster_table(self.table)
        if hasattr(self, "player_detail_table"):
            self._polish_roster_table(self.player_detail_table)

        if hasattr(self, "team_snapshot_label"):
            self.team_snapshot_label.setToolTip(
                "Good people make hard things possible. Same people. Better records."
            )

    @staticmethod
    def _polish_roster_table(table: RosterTable) -> None:
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column, width in enumerate((190, 165, 110, 120, 120, 130, 105)):
            table.setColumnWidth(column, width)
        table.setMinimumWidth(660)

    # ------------------------------------------------------------------
    # Character profile presentation
    # ------------------------------------------------------------------

    def _show_character_detail(self, item, _previous=None) -> None:
        """Present player/character/build identity as a compact human-facing profile card."""
        if item is None:
            self.character_detail.set_title("Character")
            self._set_profile_avatar("character")
            self.character_detail_body.setText("Select a player, character, or build.")
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, tuple) or len(data) != 2:
            self.character_detail_body.setText(item.text(0))
            return

        kind, identity = data
        catalog = self.build_library.canonical.catalog_service
        self.character_detail_body.setTextFormat(Qt.TextFormat.RichText)
        self._set_profile_avatar(kind)

        if kind == "player":
            player = catalog.get_player(identity) or {}
            characters = catalog.characters_for_player(identity)
            gamertag = _clean(player.get("gamertag")) or "Player"
            roster = next(
                (member for member in self.members if _clean(member.PlayerName).casefold() == gamertag.casefold()),
                None,
            )
            self.character_detail.set_title(gamertag)
            self.character_detail_body.setText(
                self._profile_html(
                    heading=gamertag,
                    rows=(
                        ("Profile", "Player"),
                        ("Characters", str(len(characters))),
                        ("Teams", _clean(roster.Team) if roster else "Not assigned"),
                        ("Status", _clean(roster.Status) if roster else "Active"),
                    ),
                )
            )
            return

        if kind == "character":
            character = catalog.get_character(identity) or {}
            player = catalog.player_for_character(identity) or {}
            builds = catalog.builds_for_character(identity)
            name = _clean(character.get("name")) or "Character"
            gamertag = _clean(player.get("gamertag")) or "Unknown"
            roster = next(
                (
                    member
                    for member in self.members
                    if _clean(member.PlayerName).casefold() == gamertag.casefold()
                    or _clean(member.CharacterName).casefold() == name.casefold()
                ),
                None,
            )
            role = _clean(roster.PrimaryRole) if roster else "Not set"
            self.character_detail.set_title(name)
            self.character_detail_body.setText(
                self._profile_html(
                    heading=name,
                    subheading=f"Player: {gamertag}",
                    rows=(
                        ("Class", _clean(character.get("eso_class")) or "Not set"),
                        ("Race", _clean(character.get("race")) or "Not set"),
                        ("Role", role),
                        ("Teams", _clean(roster.Team) if roster else "Not assigned"),
                        ("Readiness", _clean(roster.Status) if roster else "Active"),
                        ("Saved builds", str(len(builds))),
                    ),
                )
            )
            return

        build = catalog.get_build(identity) or {}
        payload = build.get("payload") if isinstance(build.get("payload"), dict) else {}
        character = catalog.get_character(_clean(build.get("character_id"))) or {}
        name = _clean(build.get("name")) or "Build"
        self.character_detail.set_title(name)
        self.character_detail_body.setText(
            self._profile_html(
                heading=name,
                subheading=f"Character: {_clean(character.get('name')) or 'Unknown'}",
                rows=(
                    ("Profile", "Saved Build"),
                    ("Role", _clean(payload.get("Role")) or "Not set"),
                    ("Class", _clean(character.get("eso_class")) or "Not set"),
                    ("Race", _clean(character.get("race")) or "Not set"),
                ),
            )
        )

    @staticmethod
    def _profile_html(
        *,
        heading: str,
        rows: tuple[tuple[str, str], ...],
        subheading: str = "",
    ) -> str:
        pieces = [
            '<div style="padding:6px 2px;">',
            f'<div style="font-size:20px; font-weight:700; margin-bottom:2px;">{heading}</div>',
        ]
        if subheading:
            pieces.append(
                f'<div style="opacity:.78; margin-bottom:10px;">{subheading}</div>'
            )
        pieces.append('<table cellspacing="0" cellpadding="6" width="100%">')
        for label, value in rows:
            pieces.append(
                "<tr>"
                f'<td width="32%" style="opacity:.72; border-bottom:1px solid #314247;">{label}</td>'
                f'<td style="border-bottom:1px solid #314247;"><b>{value}</b></td>'
                "</tr>"
            )
        pieces.append("</table></div>")
        return "".join(pieces)

    # ------------------------------------------------------------------
    # Embedded navigation
    # ------------------------------------------------------------------

    def _embed_detail_workspaces(self) -> None:
        """Move dialog-owned editors into one in-page stack beneath the card bar."""
        if self.workspace_layout.count() < 2:
            return

        dashboard_item = self.workspace_layout.takeAt(1)
        dashboard = dashboard_item.widget()
        if dashboard is None:
            return

        stack = QStackedWidget()
        stack.setProperty("rosterEmbeddedWorkspace", True)
        stack.addWidget(dashboard)
        self._embedded_stack = stack

        for key, dialog in list(self._detail_dialogs.items()):
            dialog_layout = dialog.layout()
            if dialog_layout is None or dialog_layout.count() == 0:
                continue
            item = dialog_layout.takeAt(0)
            page = item.widget()
            if page is None:
                continue
            page.setParent(None)

            shell = QWidget()
            shell_layout = QVBoxLayout(shell)
            shell_layout.setContentsMargins(0, 0, 0, 0)
            shell_layout.setSpacing(4)

            nav = QHBoxLayout()
            nav.setContentsMargins(2, 0, 0, 0)
            back = QToolButton()
            back.setProperty("rosterBackButton", True)
            back.setToolTip("Back to Roster")
            back.setAutoRaise(True)
            back.setFixedSize(34, 30)
            back.setIcon(icon("roster-back"))
            back.setIconSize(QSize(28, 28))
            back.setStyleSheet(
                "QToolButton { background: transparent; border: none; padding: 0; } "
                "QToolButton:hover { background: rgba(200,164,106,28); border-radius: 4px; }"
            )
            back.clicked.connect(self._show_dashboard)
            nav.addWidget(back)
            nav.addStretch(1)
            shell_layout.addLayout(nav)
            shell_layout.addWidget(page, 1)

            index = stack.addWidget(shell)
            self._embedded_detail_indexes[key] = index
            dialog.close()
            dialog.deleteLater()

        self._detail_dialogs.clear()
        self.workspace_layout.insertWidget(1, stack, 1)
        stack.setCurrentIndex(0)

        if hasattr(self, "player_detail_table"):
            self._polish_roster_table(self.player_detail_table)

    def _show_dashboard(self) -> None:
        if self._embedded_stack is not None:
            self._embedded_stack.setCurrentIndex(0)

    def _show_detail(self, key: str) -> None:
        """Open Players/Characters/Teams/etc. in-page instead of as a pop-up."""
        if self._embedded_stack is not None:
            index = self._embedded_detail_indexes.get(key)
            if index is not None:
                self._embedded_stack.setCurrentIndex(index)
                return
        super()._show_detail(key)


__all__ = ["CityRaidRosterWorkspacePage"]
