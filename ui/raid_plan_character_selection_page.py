from __future__ import annotations

"""Player-aware character/build selection for the visible Raid Plan workspace.

RaidPlanPage owns the trial-chair draft. This subclass only improves how reusable global
Character and Build identities are selected for a chair: selecting a known player narrows
character choices to that player, and selecting a character narrows build choices again.
No character or build is created here and no Raid Plan decision is persisted into the
reusable build catalog.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
)

from ui.raid_plan_page import RaidPlanPage, _clean


def known_character_names(saved_builds, personnel_members, gamertag: str) -> tuple[str, ...]:
    """Return reviewed/reusable character names already associated with one player."""
    player_key = _clean(gamertag).casefold()
    if not player_key:
        return ()

    by_key: dict[str, str] = {}
    for build in tuple(saved_builds or ()):
        if _clean(getattr(build, "Gamertag", "")).casefold() != player_key:
            continue
        name = _clean(getattr(build, "Name", ""))
        if name:
            by_key.setdefault(name.casefold(), name)

    for member in tuple(personnel_members or ()):
        if _clean(getattr(member, "PlayerName", "")).casefold() != player_key:
            continue
        name = _clean(getattr(member, "CharacterName", ""))
        if name:
            by_key.setdefault(name.casefold(), name)

    return tuple(sorted(by_key.values(), key=str.casefold))


def matching_saved_build_indices(saved_builds, gamertag: str, character_name: str = "") -> tuple[int, ...]:
    """Return exact saved-build candidates for one player and optional character."""
    player_key = _clean(gamertag).casefold()
    character_key = _clean(character_name).casefold()
    if not player_key:
        return ()

    matches: list[int] = []
    for index, build in enumerate(tuple(saved_builds or ())):
        if _clean(getattr(build, "Gamertag", "")).casefold() != player_key:
            continue
        if character_key and _clean(getattr(build, "Name", "")).casefold() != character_key:
            continue
        matches.append(index)
    return tuple(matches)


def known_character_classes(saved_builds, personnel_members, gamertag: str, character_name: str) -> tuple[str, ...]:
    """Return source-backed class identities for one exact player/character pair."""
    player_key = _clean(gamertag).casefold()
    character_key = _clean(character_name).casefold()
    if not player_key or not character_key:
        return ()

    by_key: dict[str, str] = {}
    for build in tuple(saved_builds or ()):
        if _clean(getattr(build, "Gamertag", "")).casefold() != player_key:
            continue
        if _clean(getattr(build, "Name", "")).casefold() != character_key:
            continue
        eso_class = _clean(getattr(build, "EsoClass", ""))
        if eso_class:
            by_key.setdefault(eso_class.casefold(), eso_class)

    for member in tuple(personnel_members or ()):
        if _clean(getattr(member, "PlayerName", "")).casefold() != player_key:
            continue
        if _clean(getattr(member, "CharacterName", "")).casefold() != character_key:
            continue
        eso_class = _clean(getattr(member, "EsoClass", ""))
        if eso_class:
            by_key.setdefault(eso_class.casefold(), eso_class)

    return tuple(sorted(by_key.values(), key=str.casefold))


def raid_plan_stretch_columns() -> tuple[int, ...]:
    """Columns that should consume the available Raid Plan workspace width."""
    return (1, 2, 3, 4)


class RaidPlanCharacterSelectionPage(RaidPlanPage):
    """Raid Plan page with player-scoped character and build selectors."""

    def _build_ui(self) -> None:
        super()._build_ui()

        # Raid Plans are a wide working surface. Let the workspace and table consume
        # the available stacked-page area instead of honoring child size hints that
        # make the plan open as a narrow, scrunched-up strip.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.workspace_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.workspace_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.team_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.team_table.setMinimumWidth(0)

        header = self.team_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(70)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        for column in raid_plan_stretch_columns():
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)

        for row in range(self.team_table.rowCount()):
            combo = QComboBox()
            combo.setEditable(True)
            combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            combo.setMinimumWidth(0)
            combo.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            if combo.lineEdit() is not None:
                combo.lineEdit().setPlaceholderText("Choose or type character…")
                combo.lineEdit().setClearButtonEnabled(True)
            combo.currentTextChanged.connect(
                lambda _text, row_index=row: self._character_text_changed(row_index)
            )
            self.team_table.setCellWidget(row, 2, combo)

    @staticmethod
    def _item_text(table: QTableWidget, row: int, column: int) -> str:
        if column == 2:
            widget = table.cellWidget(row, column)
            if isinstance(widget, QComboBox):
                return _clean(widget.currentText())
        return RaidPlanPage._item_text(table, row, column)

    def _set_item_text(self, row: int, column: int, value: object) -> None:
        if column == 2:
            combo = self.team_table.cellWidget(row, column)
            if isinstance(combo, QComboBox):
                combo.blockSignals(True)
                combo.setCurrentText(_clean(value))
                combo.blockSignals(False)
                return
        super()._set_item_text(row, column, value)

    def _character_combo(self, row: int) -> QComboBox | None:
        combo = self.team_table.cellWidget(row, 2)
        return combo if isinstance(combo, QComboBox) else None

    def _refresh_character_options(self, row: int) -> None:
        combo = self._character_combo(row)
        if combo is None:
            return

        current = _clean(combo.currentText())
        names = known_character_names(
            self.saved_builds,
            self.personnel_members,
            self._player_text(row),
        )
        known_player = self._personnel_match(self._player_text(row)) is not None
        name_keys = {name.casefold() for name in names}
        if current and known_player and current.casefold() not in name_keys:
            current = ""

        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        combo.addItems(names)
        if current:
            combo.setCurrentText(current)
        elif len(names) == 1:
            combo.setCurrentText(names[0])

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)
        combo.blockSignals(False)

        self._apply_character_class(row)

    def _refresh_build_options(self, row: int) -> None:
        combo = self.team_table.cellWidget(row, 4)
        if not isinstance(combo, QComboBox):
            return

        prior_index = combo.currentData()
        prior_build = (
            self.saved_builds[prior_index]
            if isinstance(prior_index, int) and 0 <= prior_index < len(self.saved_builds)
            else None
        )
        prior_build_id = (
            _clean(getattr(prior_build, "BuildId", ""))
            if prior_build is not None
            else ""
        )
        prior_identity = (
            _clean(getattr(prior_build, "Gamertag", "")).casefold(),
            _clean(getattr(prior_build, "Name", "")).casefold(),
            _clean(getattr(prior_build, "BuildName", "")).casefold(),
        ) if prior_build is not None else None

        matches = matching_saved_build_indices(
            self.saved_builds,
            self._player_text(row),
            self._item_text(self.team_table, row, 2),
        )

        # A Raid Plan owns an explicit stable BuildId. Exact stable identity is
        # stronger evidence than display-text filters, especially after player
        # merges/aliases or character-name cleanup. Keep the selected canonical
        # Build available even when the current player/character text would have
        # filtered it out of the picker.
        if prior_build_id:
            exact_index = next(
                (
                    index
                    for index, build in enumerate(self.saved_builds)
                    if _clean(getattr(build, "BuildId", "")) == prior_build_id
                ),
                None,
            )
            if exact_index is not None and exact_index not in matches:
                matches.append(exact_index)

        combo.blockSignals(True)
        combo.clear()
        combo.addItem("No build selected", None)
        selected_combo_index = 0
        for saved_index in matches:
            build = self.saved_builds[saved_index]
            combo.addItem(self._build_display(build), saved_index)
            identity = (
                _clean(getattr(build, "Gamertag", "")).casefold(),
                _clean(getattr(build, "Name", "")).casefold(),
                _clean(getattr(build, "BuildName", "")).casefold(),
            )
            if prior_identity is not None and identity == prior_identity:
                selected_combo_index = combo.count() - 1
        combo.setCurrentIndex(selected_combo_index)
        combo.blockSignals(False)

    def _apply_character_class(self, row: int) -> None:
        character = self._item_text(self.team_table, row, 2)
        classes = known_character_classes(
            self.saved_builds,
            self.personnel_members,
            self._player_text(row),
            character,
        )
        if len(classes) == 1:
            class_combo = self.team_table.cellWidget(row, 3)
            if isinstance(class_combo, QComboBox):
                class_combo.setCurrentText(classes[0])
        elif character:
            # Do not preserve a class from the prior player's character when the
            # selected identity has no single source-backed class.
            class_combo = self.team_table.cellWidget(row, 3)
            if isinstance(class_combo, QComboBox):
                class_combo.setCurrentText("")

    def _character_text_changed(self, row: int) -> None:
        self._apply_character_class(row)
        self._refresh_build_options(row)
        self._update_summary()

    def _player_text_changed(self, row: int) -> None:
        super()._player_text_changed(row)
        self._refresh_character_options(row)
        self._refresh_build_options(row)

    def refresh_personnel(self) -> None:
        super().refresh_personnel()
        if not hasattr(self, "team_table"):
            return
        for row in range(self.team_table.rowCount()):
            self._refresh_character_options(row)
            self._refresh_build_options(row)

    def refresh_saved_builds(self) -> None:
        super().refresh_saved_builds()
        if not hasattr(self, "team_table"):
            return
        for row in range(self.team_table.rowCount()):
            self._refresh_character_options(row)
            self._refresh_build_options(row)

    def _apply_saved_build(self, row: int) -> None:
        super()._apply_saved_build(row)
        self._refresh_character_options(row)
        self._refresh_build_options(row)
        self._refresh_personnel_button(row)
        self._update_summary()


__all__ = [
    "RaidPlanCharacterSelectionPage",
    "known_character_classes",
    "known_character_names",
    "matching_saved_build_indices",
    "raid_plan_stretch_columns",
]
