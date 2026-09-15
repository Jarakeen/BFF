from __future__ import annotations

"""Stable identity item-data for RaidPlan player and character pickers.

Visible labels remain editable planning text. Canonical ids are attached only when
explicit Personnel or Build Catalog evidence identifies exactly one stable identity.
No equivalence is inferred from similar names.
"""

from dataclasses import replace

from PySide6.QtWidgets import QComboBox

from ui.raid_plan_character_selection_page import RaidPlanCharacterSelectionPage
from ui.raid_plan_page import RAID_PLAN_SEATS, _clean, _slug


def stable_player_id_for_name(personnel_members, gamertag: str) -> str | None:
    """Return one explicit Personnel canonical player id for an exact display name."""
    key = _clean(gamertag).casefold()
    if not key:
        return None
    player_ids = {
        _clean(getattr(member, "CanonicalPlayerId", ""))
        for member in tuple(personnel_members or ())
        if _clean(getattr(member, "PlayerName", "")).casefold() == key
        and _clean(getattr(member, "CanonicalPlayerId", ""))
    }
    if len(player_ids) != 1:
        return None
    return next(iter(player_ids))


def stable_character_id_for_name(
    saved_builds,
    personnel_members,
    gamertag: str,
    character_name: str,
    *,
    player_id: str | None = None,
    catalog_service=None,
) -> str | None:
    """Return one explicit canonical character id for the selected player/name pair.

    The visible name only selects among already-known records. It never creates identity.
    Conflicting explicit ids deliberately collapse to unresolved rather than first-match.
    """
    player_key = _clean(gamertag).casefold()
    character_key = _clean(character_name).casefold()
    canonical_player_id = _clean(player_id)
    if not player_key or not character_key:
        return None

    character_ids: set[str] = set()

    if canonical_player_id and catalog_service is not None:
        for character in catalog_service.characters_for_player(canonical_player_id):
            if _clean(character.get("name")).casefold() != character_key:
                continue
            character_id = _clean(character.get("character_id"))
            if character_id:
                character_ids.add(character_id)

    for member in tuple(personnel_members or ()):
        if _clean(getattr(member, "PlayerName", "")).casefold() != player_key:
            continue
        if _clean(getattr(member, "CharacterName", "")).casefold() != character_key:
            continue
        character_id = _clean(getattr(member, "CanonicalCharacterId", ""))
        if not character_id:
            continue
        if catalog_service is not None:
            character = catalog_service.get_character(character_id)
            if character is None:
                continue
            owner_id = _clean(character.get("player_id"))
            if canonical_player_id and owner_id != canonical_player_id:
                continue
        character_ids.add(character_id)

    for build in tuple(saved_builds or ()):
        if _clean(getattr(build, "Gamertag", "")).casefold() != player_key:
            continue
        if _clean(getattr(build, "Name", "")).casefold() != character_key:
            continue
        character_id = _clean(getattr(build, "CharacterId", ""))
        if not character_id:
            continue
        if catalog_service is not None:
            character = catalog_service.get_character(character_id)
            if character is None:
                continue
            owner_id = _clean(character.get("player_id"))
            if canonical_player_id and owner_id != canonical_player_id:
                continue
        character_ids.add(character_id)

    if len(character_ids) != 1:
        return None
    return next(iter(character_ids))


class RaidPlanStableIdentitySelectionPage(RaidPlanCharacterSelectionPage):
    """Attach stable ids to existing editable RaidPlan picker choices."""

    @staticmethod
    def _selected_item_data(combo: QComboBox) -> str | None:
        index = combo.currentIndex()
        if index < 0:
            return None
        if _clean(combo.itemText(index)).casefold() != _clean(combo.currentText()).casefold():
            return None
        value = _clean(combo.itemData(index))
        return value or None

    def _selected_player_id(self, row: int) -> str | None:
        combo = self.team_table.cellWidget(row, 1)
        if not isinstance(combo, QComboBox):
            return None
        return self._selected_item_data(combo)

    def _selected_character_id(self, row: int) -> str | None:
        combo = self._character_combo(row)
        if combo is None:
            return None
        return self._selected_item_data(combo)

    def _apply_player_item_data(self) -> None:
        if not hasattr(self, "team_table"):
            return
        for row in range(self.team_table.rowCount()):
            combo = self.team_table.cellWidget(row, 1)
            if not isinstance(combo, QComboBox):
                continue
            for index in range(combo.count()):
                player_id = stable_player_id_for_name(
                    self.personnel_members,
                    combo.itemText(index),
                )
                combo.setItemData(index, player_id)

    def _refresh_character_options(self, row: int) -> None:
        super()._refresh_character_options(row)
        combo = self._character_combo(row)
        if combo is None:
            return
        player_id = self._selected_player_id(row)
        catalog = self.build_service.canonical.catalog_service
        for index in range(combo.count()):
            character_id = stable_character_id_for_name(
                self.saved_builds,
                self.personnel_members,
                self._player_text(row),
                combo.itemText(index),
                player_id=player_id,
                catalog_service=catalog,
            )
            combo.setItemData(index, character_id)

    def refresh_personnel(self) -> None:
        super().refresh_personnel()
        self._apply_player_item_data()
        if not hasattr(self, "team_table"):
            return
        # Player item data was assigned after the base refresh. Rebind character
        # item data once so canonical player ownership can participate immediately.
        for row in range(self.team_table.rowCount()):
            self._refresh_character_options(row)

    def current_plan(self):
        visible = super().current_plan()
        row_by_seat = {
            _slug(seat).casefold(): row
            for row, seat in enumerate(RAID_PLAN_SEATS)
        }
        members = []
        for member in visible.members:
            row = row_by_seat.get(member.seat_id.casefold())
            if row is None:
                members.append(member)
                continue
            members.append(
                member.with_selection(
                    player_id=self._selected_player_id(row),
                    character_id=self._selected_character_id(row),
                )
            )
        return replace(visible, members=tuple(members))


__all__ = [
    "RaidPlanStableIdentitySelectionPage",
    "stable_character_id_for_name",
    "stable_player_id_for_name",
]
