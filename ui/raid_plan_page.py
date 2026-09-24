from __future__ import annotations

"""Visible Raid Plan workspace for assembling one trial team.

Raid Plans own trial-specific chair decisions. Personnel remains global player identity,
Characters and Builds remain reusable global records, and a Raid Plan may still contain an
incomplete chair with only class/build planning and no assigned player yet.

This UI deliberately does not invent characters or builds when a new player is saved. An
unknown gamertag may be promoted explicitly into Personnel as a player-only Roster record;
character/build details can be attached later through their canonical workflows.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir, get_user_database_path
from models.raid_plan import RaidPlan, RaidPlanMember
from models.roster_model import ESO_CLASSES, RosterMember
from services.build_service import BuildService
from services.comp_builder_trial_scope import COMP_MAKER_TRIALS
from services.eso_database import EsoDatabase
from services.roster_player_identity_service import RosterPlayerIdentityService
from services.roster_service import RosterService
from services.roster_placeholder_identity import is_personnel_placeholder
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


HOUSE_STACK_ROWS: tuple[tuple[str, ...], ...] = (
    ("DD 5", "DD 6", "DD 7", "DD 8"),
    ("DD 1", "DD 2", "DD 3", "DD 4"),
)

RAID_PLAN_SEATS: tuple[str, ...] = (
    "Tank 1",
    "Tank 2",
    "Healer 1",
    "Healer 2",
    "DD 1",
    "DD 2",
    "DD 3",
    "DD 4",
    "DD 5",
    "DD 6",
    "DD 7",
    "DD 8",
)

def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _slug(value: object) -> str:
    text = _clean(value).casefold()
    return "-".join(part for part in text.replace("'", "").split() if part) or "raid-plan"


def is_seat_placeholder(value: object) -> bool:
    """Compatibility alias for canonical Personnel placeholder detection."""
    return is_personnel_placeholder(value)


def role_for_seat(seat: str) -> str:
    """Derive the functional raid role from the chair label."""
    key = _clean(seat).casefold()
    if "tank" in key:
        return "Tank"
    if "healer" in key:
        return "Healer"
    if key.startswith("dd"):
        return "DD"
    return ""


def personnel_player_names(members) -> tuple[str, ...]:
    """Return unique global player identities in stable case-insensitive order."""
    by_key: dict[str, str] = {}
    for member in tuple(members or ()):
        name = _clean(getattr(member, "PlayerName", ""))
        if name:
            by_key.setdefault(name.casefold(), name)
    return tuple(sorted(by_key.values(), key=str.casefold))


def new_personnel_member(gamertag: str) -> RosterMember:
    """Create the intentionally minimal Personnel record used by Raid Plans."""
    player = _clean(gamertag)
    if not player:
        raise ValueError("gamertag is required before saving a player to Personnel")
    if is_seat_placeholder(player):
        raise ValueError("Raid Plan seat placeholders cannot be saved as Personnel players")
    return RosterMember(PlayerName=player, Status="Active")


def raid_plan_member_from_values(
    *,
    seat_id: str,
    gamertag: str,
    character_name: str = "",
    role: str = "",
    eso_class: str = "",
    selected_build_name: str = "",
) -> RaidPlanMember | None:
    """Create one persisted planning chair when any user-owned chair state exists.

    Seat-derived role alone does not materialize an otherwise empty chair. A selected
    class, character, build, or gamertag does, so Recruit requirements can be planned
    before a player is assigned.
    """
    player = _clean(gamertag)
    character = _clean(character_name)
    selected_class = _clean(eso_class)
    build_name = _clean(selected_build_name)
    if not any((player, character, selected_class, build_name)):
        return None
    return RaidPlanMember(
        seat_id=_slug(seat_id),
        gamertag=player,
        character_name=character or None,
        role=_clean(role) or None,
        eso_class=selected_class or None,
        selected_build_name=build_name or None,
    )


class RaidPlanPage(FoundryPage):
    """Session-scoped editor for one trial's raid plan."""

    pageRequested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        data_dir = get_data_dir()
        self.build_service = BuildService(data_dir / "builds.json")
        self.roster_service = RosterService(EsoDatabase(get_user_database_path()))
        self.saved_builds = []
        self.personnel_members: list[RosterMember] = []
        self._syncing_build_selection = False
        self._build_ui()
        self.refresh_personnel()
        self.refresh_saved_builds()
        self._update_summary()

    @staticmethod
    def _context_field(title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Raid Plans",
            subtitle="Choose the trial, put people in chairs, then assign characters and builds as you learn them.",
            department="RAID ENGINE • PLANS",
            icon="trial",
        )
        self.set_header(self.header)

        self.trial_combo = QComboBox()
        self.trial_combo.addItems(COMP_MAKER_TRIALS)
        rockgrove = self.trial_combo.findText("Rockgrove")
        if rockgrove >= 0:
            self.trial_combo.setCurrentIndex(rockgrove)
        self.trial_combo.setMinimumWidth(180)

        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(("Veteran Hardmode", "Veteran", "Normal"))

        self.plan_name_edit = QLineEdit("New Raid Plan")
        self.plan_name_edit.setMinimumWidth(220)
        self.plan_name_edit.setPlaceholderText("Plan name")

        self.header.add_context_widget(self._context_field("TRIAL", self.trial_combo))
        self.header.add_context_widget(self._context_field("DIFFICULTY", self.difficulty_combo))
        self.plan_name_context = self._context_field("PLAN", self.plan_name_edit)
        self.header.add_context_widget(self.plan_name_context)

        workspace = QWidget()
        root = QVBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        summary_card = FoundryCard("Plan Snapshot", "checklist")
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        summary_card.addWidget(self.summary_label)
        note = QLabel(
            "Type any gamertag into a chair. Known Personnel names autocomplete; unknown names are still legal. "
            "Use Save Player to create only the global player identity. No character or build is invented."
        )
        note.setWordWrap(True)
        note.setProperty("muted", True)
        summary_card.addWidget(note)
        root.addWidget(summary_card)

        team_card = FoundryCard("Team", "team")
        self.team_table = QTableWidget(len(RAID_PLAN_SEATS), 6)
        self.team_table.setHorizontalHeaderLabels(
            ("SEAT", "GAMERTAG", "CHARACTER", "CLASS", "BUILD", "PERSONNEL")
        )
        self.team_table.verticalHeader().setVisible(False)
        self.team_table.horizontalHeader().setStretchLastSection(False)
        self.team_table.setMinimumHeight(430)

        for row, seat in enumerate(RAID_PLAN_SEATS):
            seat_item = QTableWidgetItem(seat)
            seat_item.setFlags(seat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.team_table.setItem(row, 0, seat_item)

            player_combo = QComboBox()
            player_combo.setEditable(True)
            player_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            player_combo.setMinimumWidth(155)
            if player_combo.lineEdit() is not None:
                player_combo.lineEdit().setPlaceholderText(seat)
                player_combo.lineEdit().setClearButtonEnabled(True)
            player_combo.currentTextChanged.connect(
                lambda _text, row_index=row: self._player_text_changed(row_index)
            )
            self.team_table.setCellWidget(row, 1, player_combo)

            self.team_table.setItem(row, 2, QTableWidgetItem(""))

            class_combo = QComboBox()
            class_combo.setEditable(True)
            class_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            class_combo.addItem("")
            class_combo.addItems(ESO_CLASSES)
            if class_combo.lineEdit() is not None:
                class_combo.lineEdit().setPlaceholderText("Type class…")
                class_combo.lineEdit().setClearButtonEnabled(True)
            class_completer = QCompleter(class_combo.model(), class_combo)
            class_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            class_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            class_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            class_combo.setCompleter(class_completer)
            class_combo.currentTextChanged.connect(self._update_summary)
            self.team_table.setCellWidget(row, 3, class_combo)

            build_combo = QComboBox()
            build_combo.addItem("No build selected", None)
            build_combo.currentIndexChanged.connect(
                lambda _index, row_index=row: self._apply_saved_build(row_index)
            )
            self.team_table.setCellWidget(row, 4, build_combo)

            save_player = QPushButton("Save Player")
            save_player.setToolTip(
                "Save this gamertag as a global Personnel player only. Character and build stay blank unless already known."
            )
            save_player.clicked.connect(
                lambda _checked=False, row_index=row: self.save_player_to_personnel(row_index)
            )
            self.team_table.setCellWidget(row, 5, save_player)

        self.team_table.cellChanged.connect(lambda *_: self._update_summary())

        stack_panel = QWidget()
        stack_layout = QGridLayout(stack_panel)
        stack_layout.setContentsMargins(0, 0, 0, 4)
        stack_layout.setHorizontalSpacing(8)
        stack_layout.setVerticalSpacing(4)

        stack_heading = QLabel("HOUSE STACK")
        stack_heading.setProperty("sidebarHeading", True)
        stack_layout.addWidget(stack_heading, 0, 0, 2, 1)

        self.house_stack_labels: dict[str, QLabel] = {}
        for stack_row, seats in enumerate(HOUSE_STACK_ROWS):
            for column, seat in enumerate(seats, start=1):
                label = QLabel()
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setMinimumWidth(100)
                label.setToolTip(
                    f"{seat} house-stack position. The top row is DD 5–8; "
                    "the bottom row is DD 1–4."
                )
                self.house_stack_labels[seat] = label
                stack_layout.addWidget(label, stack_row, column)

        team_card.addWidget(stack_panel)
        team_card.addWidget(self.team_table)
        root.addWidget(team_card, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        refresh_people = QPushButton("Refresh Personnel")
        refresh_people.clicked.connect(self.refresh_personnel)
        actions.addWidget(refresh_people)

        refresh = QPushButton("Refresh Saved Builds")
        refresh.clicked.connect(self.refresh_saved_builds)
        actions.addWidget(refresh)

        clear = QPushButton("Clear Plan")
        clear.clicked.connect(self.clear_plan)
        actions.addWidget(clear)

        actions.addStretch(1)

        self.lower_save_plan_button = FoundryButton(
            "Save",
            role=ButtonRole.PRIMARY,
            compact=True,
        )
        self.lower_save_plan_button.setToolTip(
            "Save the current Raid Plan using the same persistence path as Plan Controls."
        )
        actions.addWidget(self.lower_save_plan_button)

        self.lower_assignments_button = FoundryButton(
            "Assignments →",
            role=ButtonRole.SECONDARY,
            compact=True,
        )
        self.lower_assignments_button.setToolTip(
            "Save this Raid Plan, then continue with the same saved plan in Assignments."
        )
        self.lower_assignments_button.clicked.connect(self._open_assignments)
        actions.addWidget(self.lower_assignments_button)

        root.addLayout(actions)
        self.add_workspace(workspace)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

        self.trial_combo.currentTextChanged.connect(self._update_summary)
        self.difficulty_combo.currentTextChanged.connect(self._update_summary)
        self.plan_name_edit.textChanged.connect(self._update_summary)

    def _open_assignments(self, *_args) -> None:
        """Open Assignments when no persistence-aware subclass owns the handoff."""
        self.pageRequested.emit("assignments")

    def _open_coverage(self, *_args) -> None:
        """Open generic Coverage when no plan-aware subclass owns the handoff."""
        self.pageRequested.emit("console:7")

    @staticmethod
    def _item_text(table: QTableWidget, row: int, column: int) -> str:
        item = table.item(row, column)
        return _clean(item.text() if item is not None else "")

    def _class_text(self, row: int) -> str:
        combo = self.team_table.cellWidget(row, 3)
        return _clean(combo.currentText() if isinstance(combo, QComboBox) else "")

    def _player_text(self, row: int) -> str:
        combo = self.team_table.cellWidget(row, 1)
        return _clean(combo.currentText() if isinstance(combo, QComboBox) else "")

    def _set_player_text(self, row: int, value: object) -> None:
        combo = self.team_table.cellWidget(row, 1)
        if not isinstance(combo, QComboBox):
            return
        text = _clean(value)
        combo.blockSignals(True)
        if text:
            combo.setCurrentText(text)
        else:
            combo.setCurrentIndex(-1)
            if combo.lineEdit() is not None:
                combo.lineEdit().clear()
        combo.blockSignals(False)

    def _set_item_text(self, row: int, column: int, value: object) -> None:
        item = self.team_table.item(row, column)
        if item is None:
            item = QTableWidgetItem()
            self.team_table.setItem(row, column, item)
        item.setText(_clean(value))

    @staticmethod
    def _build_display(build) -> str:
        gamertag = _clean(getattr(build, "Gamertag", ""))
        character = _clean(getattr(build, "Name", ""))
        build_name = _clean(getattr(build, "BuildName", "")) or "Current Build"
        identity = " • ".join(part for part in (gamertag, character, build_name) if part)
        return identity or build_name

    def _personnel_match(self, gamertag: str) -> RosterMember | None:
        key = _clean(gamertag).casefold()
        if not key:
            return None

        exact = [
            member
            for member in self.personnel_members
            if _clean(getattr(member, "PlayerName", "")).casefold() == key
        ]
        if len(exact) == 1:
            return exact[0]

        # Player merges deliberately retain the discarded display name as a durable
        # alias.  Raid Plan chairs may still be showing that old text when Personnel
        # is refreshed after a merge, so resolve the alias back to the survivor
        # instead of treating the chair as an unknown/new player.
        try:
            matches = RosterPlayerIdentityService(
                self.roster_service.db,
                self.build_service,
            ).matching_members(gamertag)
        except Exception:
            return None
        return matches[0] if len(matches) == 1 else None

    def _canonical_personnel_name(self, value: object) -> str:
        text = _clean(value)
        if not text:
            return ""
        match = self._personnel_match(text)
        return _clean(getattr(match, "PlayerName", "")) if match is not None else text

    def refresh_personnel(self) -> None:
        try:
            self.personnel_members = list(self.roster_service.list_members())
        except Exception as exc:
            self.personnel_members = []
            if hasattr(self, "status"):
                self.status.warning(f"Could not load Personnel: {exc}")

        names = personnel_player_names(self.personnel_members)
        for row in range(self.team_table.rowCount()):
            combo = self.team_table.cellWidget(row, 1)
            if not isinstance(combo, QComboBox):
                continue
            current = self._canonical_personnel_name(combo.currentText())
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(names)
            # QComboBox selects item 0 after addItems(). Blank Raid Plan chairs
            # must remain genuinely blank rather than inheriting the first
            # alphabetic Personnel name.
            if current:
                combo.setCurrentText(current)
            else:
                combo.setCurrentIndex(-1)
                if combo.lineEdit() is not None:
                    combo.lineEdit().clear()
            completer = QCompleter(combo.model(), combo)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            combo.setCompleter(completer)
            combo.blockSignals(False)
            self._refresh_personnel_button(row)

        if hasattr(self, "status"):
            self.status.info(f"Raid Plan Personnel picker loaded {len(names)} player(s).")
        self._update_summary()

    def _player_text_changed(self, row: int) -> None:
        self._refresh_personnel_button(row)
        self._update_summary()

    def _refresh_personnel_button(self, row: int) -> None:
        button = self.team_table.cellWidget(row, 5)
        if not isinstance(button, QPushButton):
            return
        gamertag = self._player_text(row)
        known = self._personnel_match(gamertag)
        if not gamertag:
            button.setText("Save Player")
            button.setEnabled(False)
            return
        if is_seat_placeholder(gamertag):
            button.setText("Open Seat")
            button.setEnabled(False)
            button.setToolTip(
                "Recruitment Needed is a planning placeholder, not a Personnel player."
            )
            return
        if known is not None:
            button.setText("In Personnel")
            button.setEnabled(False)
            return
        button.setText("Save Player")
        button.setEnabled(True)

    def save_player_to_personnel(self, row: int) -> None:
        gamertag = self._player_text(row)
        if not gamertag or is_seat_placeholder(gamertag):
            self.status.warning("Type a real gamertag before saving a player to Personnel.")
            return

        existing = self._personnel_match(gamertag)
        if existing is not None:
            self.status.info(f"{existing.PlayerName} is already in Personnel.")
            self._refresh_personnel_button(row)
            return

        try:
            member_id = self.roster_service.create_member(new_personnel_member(gamertag))
        except Exception as exc:
            self.status.error(f"Could not save {gamertag} to Personnel: {exc}")
            return

        self.refresh_personnel()
        self._set_player_text(row, gamertag)
        self._refresh_personnel_button(row)
        self.status.success(
            f"{gamertag} saved to Personnel as player #{member_id}. No character or build was created."
        )

    def refresh_saved_builds(self) -> None:
        try:
            roster = self.build_service.load()
            self.saved_builds = list(getattr(roster, "Members", ()) or ())
        except Exception as exc:
            self.saved_builds = []
            self.status.warning(f"Could not load saved builds: {exc}")

        for row in range(self.team_table.rowCount()):
            combo = self.team_table.cellWidget(row, 4)
            if not isinstance(combo, QComboBox):
                continue
            prior_name = ""
            prior_index = combo.currentData()
            if isinstance(prior_index, int) and 0 <= prior_index < len(self.saved_builds):
                prior_name = _clean(getattr(self.saved_builds[prior_index], "BuildName", ""))

            combo.blockSignals(True)
            combo.clear()
            combo.addItem("No build selected", None)
            for index, build in enumerate(self.saved_builds):
                combo.addItem(self._build_display(build), index)
            combo.blockSignals(False)

            if prior_name:
                for combo_index in range(1, combo.count()):
                    saved_index = combo.itemData(combo_index)
                    if isinstance(saved_index, int):
                        candidate = _clean(getattr(self.saved_builds[saved_index], "BuildName", ""))
                        if candidate.casefold() == prior_name.casefold():
                            combo.setCurrentIndex(combo_index)
                            break

        self.status.info(f"Raid Plan build picker loaded {len(self.saved_builds)} saved build(s).")
        self._update_summary()

    def _apply_saved_build(self, row: int) -> None:
        if self._syncing_build_selection:
            return
        combo = self.team_table.cellWidget(row, 4)
        if not isinstance(combo, QComboBox):
            return
        index = combo.currentData()
        if not isinstance(index, int) or not 0 <= index < len(self.saved_builds):
            self._update_summary()
            return

        build = self.saved_builds[index]
        self._syncing_build_selection = True
        try:
            self._set_player_text(row, getattr(build, "Gamertag", ""))
            self._set_item_text(row, 2, getattr(build, "Name", ""))
            class_combo = self.team_table.cellWidget(row, 3)
            if isinstance(class_combo, QComboBox):
                class_combo.setCurrentText(_clean(getattr(build, "EsoClass", "")))
        finally:
            self._syncing_build_selection = False
        self._refresh_personnel_button(row)
        self._update_summary()

    def current_plan(self) -> RaidPlan:
        members: list[RaidPlanMember] = []
        for row, seat in enumerate(RAID_PLAN_SEATS):
            build_combo = self.team_table.cellWidget(row, 4)
            role = role_for_seat(seat)
            build_name = ""
            if isinstance(build_combo, QComboBox):
                saved_index = build_combo.currentData()
                if isinstance(saved_index, int) and 0 <= saved_index < len(self.saved_builds):
                    build_name = _clean(getattr(self.saved_builds[saved_index], "BuildName", ""))

            member = raid_plan_member_from_values(
                seat_id=seat,
                gamertag=self._player_text(row),
                character_name=self._item_text(self.team_table, row, 2),
                role=role,
                eso_class=self._class_text(row),
                selected_build_name=build_name,
            )
            if member is not None:
                members.append(member)

        trial = _clean(self.trial_combo.currentText()) or "Unknown Trial"
        name = _clean(self.plan_name_edit.text()) or f"{trial} Plan"
        return RaidPlan(
            plan_id=f"{_slug(trial)}-{_slug(name)}",
            trial_id=_slug(trial),
            name=name,
            difficulty=_clean(self.difficulty_combo.currentText()) or None,
            members=tuple(members),
        )

    def _refresh_house_stack_preview(self) -> None:
        labels = getattr(self, "house_stack_labels", {})
        if not labels:
            return
        row_by_seat = {
            seat: row
            for row, seat in enumerate(RAID_PLAN_SEATS)
        }
        for seat, label in labels.items():
            row = row_by_seat[seat]
            number = seat.split()[-1]
            gamertag = self._player_text(row)
            display_name = gamertag if gamertag and not is_seat_placeholder(gamertag) else "Recruit"
            label.setText(f"{number}\n{display_name}")

    def _update_summary(self, *_args) -> None:
        self._refresh_house_stack_preview()
        try:
            plan = self.current_plan()
        except Exception as exc:
            self.summary_label.setText(f"Plan cannot be assembled yet: {exc}")
            return

        characters = sum(member.character_selected for member in plan.members)
        builds = sum(member.build_selected for member in plan.members)
        named_players = sum(
            bool(_clean(member.gamertag))
            and not is_seat_placeholder(member.gamertag)
            for member in plan.members
        )
        known_people = sum(
            bool(_clean(member.gamertag))
            and self._personnel_match(member.gamertag) is not None
            for member in plan.members
        )
        self.summary_label.setText(
            f"{plan.name} • {self.trial_combo.currentText()} • {self.difficulty_combo.currentText()}\n"
            f"{named_players}/12 players named • {known_people}/{named_players or 0} in Personnel • "
            f"{characters}/12 characters selected • {builds}/12 builds selected"
        )

    def clear_plan(self) -> None:
        self.team_table.blockSignals(True)
        try:
            for row in range(self.team_table.rowCount()):
                self._set_player_text(row, "")
                self._set_item_text(row, 2, "")
                class_combo = self.team_table.cellWidget(row, 3)
                if isinstance(class_combo, QComboBox):
                    class_combo.setCurrentText("")
                build_combo = self.team_table.cellWidget(row, 4)
                if isinstance(build_combo, QComboBox):
                    build_combo.setCurrentIndex(0)
                self._refresh_personnel_button(row)
        finally:
            self.team_table.blockSignals(False)
        self._update_summary()
        self.status.info("Raid Plan session draft cleared. Existing Personnel and Roster data were not changed.")


__all__ = [
    "HOUSE_STACK_ROWS",
    "RAID_PLAN_SEATS",
    "RaidPlanPage",
    "is_seat_placeholder",
    "new_personnel_member",
    "personnel_player_names",
    "raid_plan_member_from_values",
    "role_for_seat",
]
