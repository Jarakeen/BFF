from __future__ import annotations

"""Urban Wilderness Roster entry point and final composition polish.

The underlying themed roster page owns canonical data and actions. This wrapper keeps
those data owners intact while presenting the approved single-window Roster flow: six
summary cards across the top, then either the dashboard or the selected roster detail
workspace directly underneath. No modal editor windows are used on this surface.

Roster visual contract:
- decorative city/raven filler art is not used;
- full-color artwork is never placed on parchment cards;
- decorative assets never determine page/card geometry;
- Players always retains a visible people table;
- Character details remain a compact profile surface rather than another editor maze.
"""

from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_resource_path
from ui.components.foundry_card import FoundryCard
from ui.raid_roster_workspace_page import RaidRosterWorkspacePage, _clean
from ui.themed_raid_roster_workspace_page import ThemedRaidRosterWorkspacePage
from ui.urban_wilderness_accessibility_polish import install as install_urban_wilderness_accessibility_polish
from ui.ux_icons import icon, set_button_icon
from widgets.roster_actions import RosterActions
from widgets.roster_record import RosterRecord
from widgets.roster_table import RosterTable


_BADGES = {
    "players": "users",
    "characters": "character",
    "teams": "users",
    "availability": "stopwatch",
    "recruitment": "person",
    "archive": "archive",
}


def _trim_transparent(pixmap: QPixmap) -> QPixmap:
    """Trim transparent sprite padding so collectible numbers read at card scale."""
    if pixmap.isNull():
        return pixmap
    image = pixmap.toImage()
    left, top = image.width(), image.height()
    right = bottom = -1
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() <= 16:
                continue
            left = min(left, x)
            top = min(top, y)
            right = max(right, x)
            bottom = max(bottom, y)
    if right < left or bottom < top:
        return pixmap
    padding = max(1, min(image.width(), image.height()) // 40)
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(image.width() - 1, right + padding)
    bottom = min(image.height() - 1, bottom + padding)
    return pixmap.copy(QRect(left, top, right - left + 1, bottom - top + 1))


def _number_sprite(index: int) -> QPixmap:
    """Return one cropped numbered Collectibles sprite for the Roster card corner."""
    path = get_resource_path("assets", "themes", "bff", "collectibles", "numbers.png")
    sheet = QPixmap(str(path)) if Path(path).is_file() else QPixmap()
    if sheet.isNull() or not 0 <= index < 24:
        return QPixmap()

    columns, rows = 6, 4
    cell_width = max(1, sheet.width() // columns)
    cell_height = max(1, sheet.height() // rows)
    column = index % columns
    row = index // columns
    sprite = sheet.copy(QRect(column * cell_width, row * cell_height, cell_width, cell_height))
    return _trim_transparent(sprite)


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
        self._install_detail_dialog(
            "characters",
            "Characters",
            RaidRosterWorkspacePage._build_characters_tab(self),
            (1180, 760),
        )
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
        """Remove the raven/street filler panels entirely instead of swapping pictures."""
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

        for ordinal, (key, card) in enumerate(self.metric_cards.items()):
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
                badge.setFixedSize(QSize(58, 58))
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setPixmap(icon(_BADGES.get(key, "compass")).pixmap(44, 44))
                badge.setProperty("rosterMetricBadge", True)

            number = next(
                (
                    label
                    for label in card.findChildren(QLabel)
                    if bool(label.property("rosterMetricOrdinal"))
                ),
                None,
            )
            if number is not None:
                sprite = _number_sprite(ordinal)
                number.setText("")
                number.setFixedSize(QSize(46, 46))
                number.setAlignment(Qt.AlignmentFlag.AlignCenter)
                number.setStyleSheet(
                    "background: transparent; border: none; border-radius: 0; padding: 0;"
                )
                if not sprite.isNull():
                    number.setPixmap(
                        sprite.scaled(
                            42,
                            42,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                else:
                    number.setText(str(ordinal + 1))
                    number.setStyleSheet(
                        "background: transparent; border: none; border-radius: 0; padding: 0; "
                        "color: #C49A5A; font-size: 22px; font-weight: 700;"
                    )

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
        """Present player/character/build identity as a compact profile card."""
        if item is None:
            self.character_detail.set_title("Character")
            self.character_detail_body.setText("Select a player, character, or build.")
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, tuple) or len(data) != 2:
            self.character_detail_body.setText(item.text(0))
            return

        kind, identity = data
        catalog = self.build_library.canonical.catalog_service
        self.character_detail_body.setTextFormat(Qt.TextFormat.RichText)

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
                        ("Canonical ID", identity),
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
                        ("Status", _clean(roster.Status) if roster else "Active"),
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
                    ("Role", _clean(payload.get("Role")) or "Not set"),
                    ("Class", _clean(character.get("eso_class")) or "Not set"),
                    ("Race", _clean(character.get("race")) or "Not set"),
                    ("Build ID", identity),
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
            '<div style="padding:8px 4px;">',
            f'<div style="font-size:20px; font-weight:700; margin-bottom:2px;">{heading}</div>',
        ]
        if subheading:
            pieces.append(
                f'<div style="opacity:.78; margin-bottom:12px;">{subheading}</div>'
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
            shell_layout.setSpacing(8)

            nav = QHBoxLayout()
            back = QPushButton("Back to Roster")
            set_button_icon(back, "back")
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