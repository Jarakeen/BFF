from __future__ import annotations

"""Personnel alias history and explicit cross-name player merging.

The UI intentionally never guesses that unrelated names belong to the same human.
Raid leads can merge two Personnel records explicitly; the discarded name becomes
an exact reusable alias for future roster imports. Ordinary renames also preserve
the previous name as history.
"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from engine.config import get_data_dir
from services.build_service import BuildService
from services.roster_player_identity_service import RosterPlayerIdentityService


_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_ORIGINAL_LOAD_MEMBER = None
_ORIGINAL_NEW_MEMBER = None
_ORIGINAL_SAVE_MEMBER = None


def _identity_service(page) -> RosterPlayerIdentityService:
    service = getattr(page, "player_identity_service", None)
    if service is None:
        service = RosterPlayerIdentityService(
            page.database,
            BuildService(get_data_dir() / "builds.json"),
        )
        page.player_identity_service = service
    return service


def _refresh_alias_history(page) -> None:
    label = getattr(page, "player_alias_history", None)
    if label is None:
        return
    member_id = getattr(page.record, "member_id", None)
    if member_id is None:
        label.setText("No aliases recorded.")
        return
    aliases = _identity_service(page).aliases_for_member(int(member_id))
    if not aliases:
        label.setText("No aliases recorded.")
        return
    label.setText(" • ".join(alias.alias for alias in aliases))


def _add_alias(page) -> None:
    member_id = getattr(page.record, "member_id", None)
    if member_id is None:
        page.status.warning("Select or save a Personnel record before adding an alias.")
        return
    alias, accepted = QInputDialog.getText(
        page,
        "Add Player Alias",
        "Previous gamertag, Discord name, raid-sheet name, or other known alias:",
    )
    if not accepted or not str(alias or "").strip():
        return
    try:
        added = _identity_service(page).add_alias(
            int(member_id),
            alias,
            source="manual",
        )
        _refresh_alias_history(page)
        if added:
            page.status.success(f"Saved player alias: {str(alias).strip()}.")
        else:
            page.status.info("That alias is already known for this player.")
    except Exception as exc:
        page.status.error(f"Alias save failed: {exc}")


class _MergePlayersDialog(QDialog):
    def __init__(self, *, survivor, candidates, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Merge Players")
        self.setMinimumWidth(480)
        root = QFormLayout(self)

        keep = QLabel(
            f"{survivor.PlayerName}"
            + (f"  ·  {survivor.CharacterName}" if survivor.CharacterName else "")
        )
        keep.setWordWrap(True)
        root.addRow("KEEP", keep)

        self.donor_combo = QComboBox()
        for member in candidates:
            label = member.PlayerName or "Unnamed player"
            if member.CharacterName:
                label += f"  ·  {member.CharacterName}"
            if member.Team:
                label += f"  ·  {member.Team}"
            self.donor_combo.addItem(label, int(member.Id))
        root.addRow("MERGE THIS DUPLICATE", self.donor_combo)

        note = QLabel(
            "The merged record's current name and known aliases are kept as alias history. "
            "Teams and assignment data are preserved, and canonical characters/builds are "
            "moved under the kept player identity."
        )
        note.setWordWrap(True)
        root.addRow("", note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Merge Duplicate")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addRow(buttons)

    @property
    def donor_id(self) -> int | None:
        value = self.donor_combo.currentData()
        return int(value) if value is not None else None


def _merge_players(page) -> None:
    survivor_id = getattr(page.record, "member_id", None)
    if survivor_id is None:
        page.status.warning("Select the Personnel record you want to keep first.")
        return
    survivor = page.roster_service.get_member(int(survivor_id))
    if survivor is None:
        page.status.warning("The selected Personnel record no longer exists.")
        return
    candidates = [
        member
        for member in page.roster_service.list_members()
        if member.Id is not None and int(member.Id) != int(survivor_id)
    ]
    if not candidates:
        page.status.info("There are no other Personnel records to merge.")
        return

    dialog = _MergePlayersDialog(survivor=survivor, candidates=candidates, parent=page)
    if dialog.exec() != QDialog.DialogCode.Accepted or dialog.donor_id is None:
        return
    donor = page.roster_service.get_member(dialog.donor_id)
    if donor is None:
        page.status.warning("The selected duplicate no longer exists.")
        return

    answer = QMessageBox.question(
        page,
        "Confirm Player Merge",
        (
            f"Keep {survivor.PlayerName} and merge {donor.PlayerName} into that player?\n\n"
            f"{donor.PlayerName} will be remembered as an alias. This cannot be undone "
            "from the UI, although backup files are created before the merge."
        ),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return

    try:
        result = _identity_service(page).merge_players(
            survivor_id=int(survivor_id),
            donor_id=int(dialog.donor_id),
            source="manual_merge",
        )
        page.refresh()
        page.table.select_member_id(result.survivor_id)
        page.load_member(result.survivor_id)
        aliases = ", ".join(result.learned_aliases) or donor.PlayerName
        page.status.success(
            f"Merged player records. {survivor.PlayerName} now remembers: {aliases}."
        )
    except Exception as exc:
        page.status.error(f"Player merge failed: {exc}")


def _build_ui_with_alias_controls(self) -> None:
    assert _ORIGINAL_BUILD_UI is not None
    _ORIGINAL_BUILD_UI(self)
    _identity_service(self)  # create alias schema before Personnel starts using it

    alias_host = QWidget()
    alias_row = QHBoxLayout(alias_host)
    alias_row.setContentsMargins(0, 0, 0, 0)
    alias_row.setSpacing(6)
    self.player_alias_history = QLabel("No aliases recorded.")
    self.player_alias_history.setWordWrap(True)
    self.player_alias_history.setProperty("muted", True)
    alias_row.addWidget(self.player_alias_history, 1)
    add_alias_button = QPushButton("Add Alias…")
    add_alias_button.clicked.connect(lambda: _add_alias(self))
    alias_row.addWidget(add_alias_button)
    record_layout = self.record.layout()
    if isinstance(record_layout, QFormLayout):
        record_layout.addRow("Known Aliases", alias_host)

    self.merge_players_button = QPushButton("Merge Duplicate Player…")
    self.merge_players_button.setToolTip(
        "Merge two Personnel records for the same human and keep old names as aliases."
    )
    self.merge_players_button.clicked.connect(lambda: _merge_players(self))
    actions_layout = self.actions.layout()
    if actions_layout is not None:
        actions_layout.addWidget(self.merge_players_button)


def _load_member_with_aliases(self, member_id: int) -> None:
    assert _ORIGINAL_LOAD_MEMBER is not None
    _ORIGINAL_LOAD_MEMBER(self, member_id)
    _refresh_alias_history(self)


def _new_member_with_alias_clear(self) -> None:
    assert _ORIGINAL_NEW_MEMBER is not None
    _ORIGINAL_NEW_MEMBER(self)
    _refresh_alias_history(self)


def _save_member_with_identity_guard(self) -> None:
    assert _ORIGINAL_SAVE_MEMBER is not None
    model = self.record.model
    if not str(model.PlayerName or "").strip():
        _ORIGINAL_SAVE_MEMBER(self)
        return

    identity = _identity_service(self)
    previous = (
        self.roster_service.get_member(int(model.Id))
        if model.Id is not None
        else None
    )
    matches = identity.matching_members(
        model.PlayerName,
        exclude_id=int(model.Id) if model.Id is not None else None,
    )
    if matches:
        if model.Id is None:
            names = ", ".join(member.PlayerName for member in matches)
            self.status.warning(
                f"That name is already known for Personnel: {names}. Select that player instead of creating another record."
            )
            return
        if len(matches) > 1:
            names = ", ".join(member.PlayerName for member in matches)
            self.status.warning(
                f"That identity matches more than one Personnel record ({names}). Use Merge Players to resolve it explicitly."
            )
            return

        target = matches[0]
        answer = QMessageBox.question(
            self,
            "Existing Player Identity",
            (
                f"{model.PlayerName} is already known as {target.PlayerName}.\n\n"
                f"Merge this Personnel record into {target.PlayerName} instead of creating a duplicate? "
                "The current name will be kept as alias history."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            result = identity.merge_players(
                survivor_id=int(target.Id),
                donor_id=int(model.Id),
                source="rename_collision",
            )
            self.refresh()
            self.table.select_member_id(result.survivor_id)
            self.load_member(result.survivor_id)
            self.status.success(f"Merged duplicate Personnel into {target.PlayerName}.")
        except Exception as exc:
            self.status.error(f"Player merge failed: {exc}")
        return

    old_name = str(previous.PlayerName or "").strip() if previous is not None else ""
    _ORIGINAL_SAVE_MEMBER(self)
    current_id = getattr(self.record, "member_id", None)
    if (
        current_id is not None
        and old_name
        and old_name.lstrip("@").casefold()
        != str(model.PlayerName or "").strip().lstrip("@").casefold()
    ):
        try:
            identity.add_alias(
                int(current_id),
                old_name,
                source="personnel_rename",
            )
        except Exception as exc:
            self.status.warning(f"Player saved, but previous-name history could not be recorded: {exc}")
    _refresh_alias_history(self)


def install() -> None:
    global _INSTALLED
    global _ORIGINAL_BUILD_UI, _ORIGINAL_LOAD_MEMBER, _ORIGINAL_NEW_MEMBER, _ORIGINAL_SAVE_MEMBER
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    _ORIGINAL_BUILD_UI = RosterPage._build_ui
    _ORIGINAL_LOAD_MEMBER = RosterPage.load_member
    _ORIGINAL_NEW_MEMBER = RosterPage.new_member
    _ORIGINAL_SAVE_MEMBER = RosterPage.save_member

    RosterPage._build_ui = _build_ui_with_alias_controls
    RosterPage.load_member = _load_member_with_aliases
    RosterPage.new_member = _new_member_with_alias_clear
    RosterPage.save_member = _save_member_with_identity_guard
    _INSTALLED = True


__all__ = ["install"]
