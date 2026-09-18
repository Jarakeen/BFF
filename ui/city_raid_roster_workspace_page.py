from __future__ import annotations

"""Urban Wilderness Roster entry point and final composition polish.

The underlying themed roster page owns canonical data and actions. This wrapper keeps
those data owners intact while presenting the approved single-window Roster flow: six
summary cards across the top, then either the dashboard or the selected roster detail
workspace directly underneath. No modal editor windows are used on this surface.

Roster visual contract:
- summary cards use the dedicated Urban Wilderness Roster badge sheet, never assets/icons;
- detail navigation uses the dedicated bronze back-arrow art at the middle-left edge;
- decorative assets never determine page/card geometry;
- Players always retains a visible people table;
- Character details remain a compact human-facing profile surface;
- canonical database IDs stay out of the visible profile card.
"""

from pathlib import Path
import shutil

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir, get_resource_path
from ui.components.foundry_card import FoundryCard
from ui.raid_roster_workspace_page import RaidRosterWorkspacePage, _clean
from ui.themed_raid_roster_workspace_page import ThemedRaidRosterWorkspacePage
from ui.urban_wilderness_accessibility_polish import install as install_urban_wilderness_accessibility_polish
from widgets.roster_actions import RosterActions
from widgets.roster_record import RosterRecord
from widgets.roster_table import RosterTable


_ROSTER_BADGE_SHEET = ("assets", "themes", "bff", "urban_wilderness", "roster", "roster_badges.png")
_ROSTER_BACK_ARROW = ("assets", "themes", "bff", "urban_wilderness", "roster", "back_arrow.png")


def _trim_transparent(pixmap: QPixmap) -> QPixmap:
    if pixmap.isNull():
        return pixmap
    image = pixmap.toImage()
    left, top = image.width(), image.height()
    right = bottom = -1
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() <= 12:
                continue
            left = min(left, x)
            top = min(top, y)
            right = max(right, x)
            bottom = max(bottom, y)
    if right < left or bottom < top:
        return pixmap
    return pixmap.copy(QRect(left, top, right - left + 1, bottom - top + 1))


def _roster_badge_sprite(index: int) -> QPixmap:
    """Extract one medallion from the dedicated six-badge Roster sheet."""
    path = get_resource_path(*_ROSTER_BADGE_SHEET)
    if not Path(path).is_file() or not 0 <= index < 6:
        return QPixmap()
    sheet = QImage(str(path)).convertToFormat(QImage.Format.Format_ARGB32)
    if sheet.isNull():
        return QPixmap()

    cell_width = max(1, sheet.width() // 6)
    cell = sheet.copy(QRect(index * cell_width, 0, cell_width, sheet.height()))

    # Generated sheets use black negative space. Make that transparent so the
    # medallion sits naturally on the card instead of carrying a black rectangle.
    for y in range(cell.height()):
        for x in range(cell.width()):
            color = cell.pixelColor(x, y)
            if color.red() < 18 and color.green() < 18 and color.blue() < 18:
                color.setAlpha(0)
                cell.setPixelColor(x, y, color)

    trimmed = _trim_transparent(QPixmap.fromImage(cell))
    if trimmed.isNull():
        return trimmed

    # roster_badges.png includes a title plaque beneath each medallion. The
    # card already owns its title, so display only the medallion art here.
    medallion_height = max(1, round(trimmed.height() * 0.74))
    return _trim_transparent(trimmed.copy(QRect(0, 0, trimmed.width(), medallion_height)))


def _roster_back_icon() -> QIcon:
    path = get_resource_path(*_ROSTER_BACK_ARROW)
    return QIcon(str(path)) if Path(path).is_file() else QIcon()


_AVATAR_ROOT = ("assets", "avatar")
_AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _avatar_default_files() -> tuple[Path, ...]:
    root = get_resource_path(*_AVATAR_ROOT)
    if not root.is_dir():
        return ()
    return tuple(
        sorted(
            (
                path
                for path in root.iterdir()
                if path.is_file() and path.suffix.casefold() in _AVATAR_EXTENSIONS
            ),
            key=lambda path: path.name.casefold(),
        )
    )


def _avatar_path(reference: str) -> Path | None:
    value = str(reference or "").strip()
    if not value:
        return None
    normalized = value.replace("\\", "/")
    if normalized.startswith("assets/avatar/"):
        relative = normalized[len("assets/avatar/") :]
        candidate = get_resource_path("assets", "avatar", relative)
        return candidate if candidate.is_file() else None
    candidate = Path(value)
    return candidate if candidate.is_file() else None


def _circular_avatar_pixmap(path: Path, size: int = 92) -> QPixmap:
    source = QPixmap(str(path))
    if source.isNull():
        return QPixmap()
    scaled = source.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - size) // 2)
    y = max(0, (scaled.height() - size) // 2)
    cropped = scaled.copy(x, y, size, size)

    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    path_clip = QPainterPath()
    path_clip.addEllipse(0, 0, size, size)
    painter.setClipPath(path_clip)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return result


class _CharacterAvatarDialog(QDialog):
    """Pick one bundled default avatar or import a custom local portrait."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_reference = ""
        self.setWindowTitle("Choose Player Avatar")
        self.setModal(True)
        self.setMinimumWidth(560)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        heading = QLabel("Default avatars")
        heading.setProperty("cardTitle", True)
        root.addWidget(heading)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        defaults = _avatar_default_files()
        if defaults:
            for index, path in enumerate(defaults):
                button = QToolButton()
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                button.setText(path.stem.replace("_", " ").replace("-", " ").title())
                button.setIcon(QIcon(_circular_avatar_pixmap(path, 72)))
                button.setIconSize(QSize(72, 72))
                button.setFixedSize(150, 110)
                reference = f"assets/avatar/{path.name}"
                button.clicked.connect(
                    lambda _checked=False, value=reference: self._choose(value)
                )
                grid.addWidget(button, index // 3, index % 3)
        else:
            empty = QLabel("No default avatars found in assets/avatar yet.")
            empty.setProperty("muted", True)
            grid.addWidget(empty, 0, 0, 1, 3)
        root.addLayout(grid)

        actions = QHBoxLayout()
        clear = QPushButton("Clear Avatar")
        browse = QPushButton("Choose Custom Image…")
        cancel = QPushButton("Cancel")
        clear.clicked.connect(lambda: self._choose(""))
        browse.clicked.connect(self._browse_custom)
        cancel.clicked.connect(self.reject)
        actions.addWidget(clear)
        actions.addStretch(1)
        actions.addWidget(browse)
        actions.addWidget(cancel)
        root.addLayout(actions)

    def _choose(self, reference: str) -> None:
        self.selected_reference = str(reference or "").strip()
        self.accept()

    def _browse_custom(self) -> None:
        path_text, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Choose Player Avatar",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if not path_text:
            return
        source = Path(path_text)
        target_root = get_data_dir() / "avatar"
        target_root.mkdir(parents=True, exist_ok=True)
        target = target_root / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        self._choose(str(target))


class CityRaidRosterWorkspacePage(ThemedRaidRosterWorkspacePage):
    """Compatibility route name for the single Urban Wilderness Roster dashboard."""

    def __init__(self, parent=None) -> None:
        install_urban_wilderness_accessibility_polish()
        self._embedded_detail_indexes: dict[str, int] = {}
        self._embedded_stack: QStackedWidget | None = None
        self._active_avatar_player_id: str = ""
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
        self.actions.configure_player_editor()

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
        record_card.addWidget(self.actions)
        split.addWidget(record_card)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)

        player_layout.addWidget(split, 1)

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
            "Click to choose this player's avatar. The choice is shared by all of their characters and builds."
        )
        self.character_detail_avatar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.character_detail_avatar.setStyleSheet(
            "background:#0A1D22; border:2px solid #4D8291; border-radius:46px; padding:0px;"
        )
        self.character_detail_avatar.mousePressEvent = self._avatar_mouse_press
        profile_layout.addWidget(self.character_detail_avatar, 0, Qt.AlignmentFlag.AlignTop)

        self.character_detail_body.setWordWrap(True)
        profile_layout.addWidget(self.character_detail_body, 1)
        layout.insertWidget(0, profile)
        self._set_profile_avatar("character")

    def _set_profile_avatar(self, kind: str, reference: str = "") -> None:
        avatar = getattr(self, "character_detail_avatar", None)
        if avatar is None:
            return
        avatar.clear()
        avatar.setProperty("semanticIconName", "")
        path = _avatar_path(reference)
        if path is not None:
            pixmap = _circular_avatar_pixmap(path, 88)
            if not pixmap.isNull():
                avatar.setPixmap(pixmap)
                avatar.setText("")
                return
        avatar.setPixmap(QPixmap())
        avatar.setText(
            {
                "player": "PLAYER\nIMAGE",
                "character": "CHARACTER\nIMAGE",
                "build": "BUILD\nIMAGE",
            }.get(kind, "CHARACTER\nIMAGE")
        )

    def _avatar_mouse_press(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._edit_character_avatar()
            event.accept()
            return
        event.ignore()

    def _edit_character_avatar(self) -> None:
        player_id = str(getattr(self, "_active_avatar_player_id", "") or "").strip()
        if not player_id:
            return
        dialog = _CharacterAvatarDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        catalog = self.build_library.canonical.catalog_service
        updated = catalog.set_player_avatar(
            player_id=player_id,
            avatar_path=dialog.selected_reference,
        )
        if updated is None:
            return
        self._set_profile_avatar("character", str(updated.get("avatar_path") or ""))

    def _connect_signals(self) -> None:
        super()._connect_signals()
        self.actions.cancelRequested.connect(self._cancel_player_edit)

    def _cancel_player_edit(self) -> None:
        selected_id = (
            self.player_detail_table.selected_member_id()
            if hasattr(self, "player_detail_table")
            else None
        )
        if selected_id is None:
            self.record.clear()
            self.status.info("Player edit cancelled.")
            return

        member = self.roster_service.get_member(int(selected_id))
        if member is None:
            self.record.clear()
            self.status.info("Player edit cancelled.")
            return

        self.record.load(member)
        self.status.info(f"Discarded unsaved changes for {_clean(member.PlayerName)}.")

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

        for index, (_key, card) in enumerate(self.metric_cards.items()):
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
                badge.setFixedSize(QSize(76, 76))
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                sprite = _roster_badge_sprite(index)
                if not sprite.isNull():
                    badge.setPixmap(
                        sprite.scaled(
                            74,
                            74,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                badge.setProperty("rosterMetricBadge", True)

            # The medallion owns the visual identity now. No duplicate 1–6 ordinal.
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
            self._active_avatar_player_id = ""
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

        if kind == "player":
            player = catalog.get_player(identity) or {}
            self._active_avatar_player_id = str(identity or "").strip()
            self._set_profile_avatar("player", str(player.get("avatar_path") or ""))
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
            self._active_avatar_player_id = str(player.get("player_id") or "").strip()
            self._set_profile_avatar(
                "character",
                str(player.get("avatar_path") or character.get("avatar_path") or ""),
            )
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
        character_id = _clean(build.get("character_id"))
        character = catalog.get_character(character_id) or {}
        player = catalog.player_for_character(character_id) or {}
        self._active_avatar_player_id = str(player.get("player_id") or "").strip()
        self._set_profile_avatar(
            "build",
            str(player.get("avatar_path") or character.get("avatar_path") or ""),
        )
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
            shell_layout = QHBoxLayout(shell)
            shell_layout.setContentsMargins(0, 0, 0, 0)
            shell_layout.setSpacing(4)

            # Keep navigation beside the leftmost detail surface, vertically centered.
            # It no longer consumes a row beneath the six Roster summary cards.
            nav_rail = QVBoxLayout()
            nav_rail.setContentsMargins(0, 0, 0, 0)
            nav_rail.setSpacing(0)
            nav_rail.addStretch(1)

            back = QToolButton()
            back.setProperty("rosterBackButton", True)
            back.setToolTip("Back to Roster")
            back.setAutoRaise(True)
            back.setFixedSize(52, 52)
            back.setIcon(_roster_back_icon())
            back.setIconSize(QSize(46, 46))
            back.setStyleSheet(
                "QToolButton { background: transparent; border: none; padding: 0; } "
                "QToolButton:hover { background: rgba(200,164,106,20); border-radius: 6px; }"
            )
            back.clicked.connect(self._show_dashboard)
            nav_rail.addWidget(back, 0, Qt.AlignmentFlag.AlignHCenter)
            nav_rail.addStretch(1)

            shell_layout.addLayout(nav_rail)
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
