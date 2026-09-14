from __future__ import annotations

"""Make repeated roster imports understandable before anything is written.

The import preview now tells the raid lead whether each row is reusing something
FoundryDock already knows or adding a new character/build. Gamertag remains the
player identity; character/build identity stays underneath that player.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

from engine.config import get_data_dir
from services.build_service import BuildService


_INSTALLED = False
_MATCH_COLUMN_TITLE = "Match"


def _identity_key(value: object) -> str:
    return " ".join(str(value or "").strip().split()).lstrip("@").casefold()


def _text_key(value: object) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def _snapshot(parent) -> dict[str, object]:
    roster_service = getattr(parent, "roster_service", None)
    build_service = BuildService(get_data_dir() / "builds.json")
    catalog = build_service.canonical.catalog_service.load()

    players_by_id: dict[str, str] = {}
    known_players: set[str] = set()
    known_characters: set[tuple[str, str]] = set()
    known_builds: set[tuple[str, str, str]] = set()

    for player in catalog.get("players", []):
        if not isinstance(player, dict):
            continue
        player_id = str(player.get("player_id") or "").strip()
        gamertag = str(player.get("gamertag") or "").strip()
        key = _identity_key(gamertag)
        if player_id and key:
            players_by_id[player_id] = key
            known_players.add(key)

    character_owner: dict[str, tuple[str, str]] = {}
    for character in catalog.get("characters", []):
        if not isinstance(character, dict):
            continue
        character_id = str(character.get("character_id") or "").strip()
        player_key = players_by_id.get(str(character.get("player_id") or "").strip(), "")
        character_key = _text_key(character.get("name"))
        if player_key and character_key:
            known_characters.add((player_key, character_key))
            if character_id:
                character_owner[character_id] = (player_key, character_key)

    for build in catalog.get("builds", []):
        if not isinstance(build, dict):
            continue
        owner = character_owner.get(str(build.get("character_id") or "").strip())
        build_key = _text_key(build.get("name"))
        if owner and build_key:
            known_builds.add((owner[0], owner[1], build_key))

    if roster_service is not None:
        for member in roster_service.list_members():
            player_key = _identity_key(getattr(member, "PlayerName", ""))
            character_key = _text_key(getattr(member, "CharacterName", ""))
            if player_key:
                known_players.add(player_key)
            if player_key and character_key:
                known_characters.add((player_key, character_key))

    return {
        "players": known_players,
        "characters": known_characters,
        "builds": known_builds,
    }


def _match_status(member, snapshot: dict[str, object], *, character_override: str | None = None) -> str:
    player_key = _identity_key(getattr(member, "gamertag", ""))
    character_name = (
        character_override
        if character_override is not None
        else str(getattr(member, "character_name", "") or "")
    )
    character_key = _text_key(character_name)

    known_players: set[str] = snapshot["players"]  # type: ignore[assignment]
    known_characters: set[tuple[str, str]] = snapshot["characters"]  # type: ignore[assignment]
    known_builds: set[tuple[str, str, str]] = snapshot["builds"]  # type: ignore[assignment]

    if getattr(member, "builds", None) and not character_key:
        return "Needs Review"

    character_exists = bool(
        player_key and character_key and (player_key, character_key) in known_characters
    )

    # A known person with a different/new toon is still one Personnel player.
    # The preview calls out only the new child identity that will be added.
    if character_key and not character_exists:
        return "New Character"

    if character_exists:
        for candidate in getattr(member, "builds", ()) or ():
            build_key = _text_key(getattr(candidate, "build_name", ""))
            if build_key and (player_key, character_key, build_key) not in known_builds:
                return "New Build"
        return "Existing"

    if player_key in known_players:
        return "Existing"

    return "New Character" if character_key else "Needs Review"


def _set_match_cell(dialog, row: int) -> None:
    column = getattr(dialog, "_match_column", -1)
    if column < 0 or row < 0 or row >= len(dialog.plan.members):
        return
    character_item = dialog.table.item(row, 2)
    character_name = character_item.text().strip() if character_item is not None else ""
    status = _match_status(
        dialog.plan.members[row],
        dialog._match_snapshot,
        character_override=character_name,
    )
    item = QTableWidgetItem(status)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    dialog.table.setItem(row, column, item)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import roster_import_workflow
    from ui.roster_import_variant_persistence_guard_support import (
        install as install_variant_persistence_guard,
    )

    # Install after the context/sparse import layers so this is the final write
    # guard: any variants prepared by those layers must survive the save boundary.
    install_variant_persistence_guard()

    dialog_type = roster_import_workflow.RosterImportPreviewDialog
    original_init = dialog_type.__init__

    def init_with_match_column(self, plan, parent=None):
        original_init(self, plan, parent)
        self._match_snapshot = _snapshot(parent)
        self._match_column = self.table.columnCount()
        self.table.insertColumn(self._match_column)
        self.table.setHorizontalHeaderItem(
            self._match_column,
            QTableWidgetItem(_MATCH_COLUMN_TITLE),
        )
        for row in range(self.table.rowCount()):
            _set_match_cell(self, row)

        def refresh_match(item):
            # Character is the only editable identity column in the base preview.
            if item is not None and item.column() == 2:
                _set_match_cell(self, item.row())

        self.table.itemChanged.connect(refresh_match)
        self.table.resizeColumnsToContents()

    dialog_type.__init__ = init_with_match_column
    _INSTALLED = True


__all__ = ["install", "_match_status"]
