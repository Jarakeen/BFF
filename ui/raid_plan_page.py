from __future__ import annotations

"""Visible Raid Plan workspace for assembling one trial team.

This first UI slice intentionally keeps persistence out of scope. It edits an in-memory
RaidPlan snapshot, reuses saved builds for quick seat assignment, and allows incomplete
chairs where only a gamertag is known. Durable persistence will be added after the new
ownership boundary is proven against the existing roster/team data.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from models.raid_plan import RaidPlan, RaidPlanMember
from services.build_service import BuildService
from services.comp_builder_trial_scope import COMP_MAKER_TRIALS
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


RAID_PLAN_SEATS: tuple[str, ...] = (
    "Main Tank",
    "Off Tank",
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

ROLE_OPTIONS: tuple[str, ...] = (
    "",
    "Tank",
    "Healer",
    "Damage Dealer",
    "Support DD",
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _slug(value: object) -> str:
    text = _clean(value).casefold()
    return "-".join(part for part in text.replace("'", "").split() if part) or "raid-plan"


def raid_plan_member_from_values(
    *,
    seat_id: str,
    gamertag: str,
    character_name: str = "",
    role: str = "",
    eso_class: str = "",
    selected_build_name: str = "",
) -> RaidPlanMember | None:
    """Create one member only when a player identity is present.

    Character, role, class and build deliberately remain optional so a raid lead can
    reserve a chair for a friend before every detail is known.
    """
    player = _clean(gamertag)
    if not player:
        return None
    return RaidPlanMember(
        seat_id=_slug(seat_id),
        gamertag=player,
        character_name=_clean(character_name) or None,
        role=_clean(role) or None,
        eso_class=_clean(eso_class) or None,
        selected_build_name=_clean(selected_build_name) or None,
    )


class RaidPlanPage(FoundryPage):
    """Session-scoped editor for one trial's raid plan."""

    pageRequested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.build_service = BuildService(get_data_dir() / "builds.json")
        self.saved_builds = []
        self._syncing_build_selection = False
        self._build_ui()
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
        self.header.add_context_widget(self._context_field("PLAN", self.plan_name_edit))

        workspace = QWidget()
        root = QVBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        summary_card = FoundryCard("Plan Snapshot", "checklist")
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        summary_card.addWidget(self.summary_label)
        note = QLabel(
            "Only seats with a gamertag become Raid Plan members. Character, role, class and build can stay blank until you know them. "
            "This first remodel slice is a session draft; it does not migrate or overwrite existing Roster data yet."
        )
        note.setWordWrap(True)
        note.setProperty("muted", True)
        summary_card.addWidget(note)
        root.addWidget(summary_card)

        team_card = FoundryCard("Team", "team")
        self.team_table = QTableWidget(len(RAID_PLAN_SEATS), 6)
        self.team_table.setHorizontalHeaderLabels(
            ("SEAT", "GAMERTAG", "CHARACTER", "ROLE", "CLASS", "BUILD")
        )
        self.team_table.verticalHeader().setVisible(False)
        self.team_table.horizontalHeader().setStretchLastSection(True)
        self.team_table.setMinimumHeight(430)

        for row, seat in enumerate(RAID_PLAN_SEATS):
            seat_item = QTableWidgetItem(seat)
            seat_item.setFlags(seat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.team_table.setItem(row, 0, seat_item)
            for column in (1, 2, 4):
                self.team_table.setItem(row, column, QTableWidgetItem(""))

            role_combo = QComboBox()
            role_combo.addItems(ROLE_OPTIONS)
            role_combo.currentTextChanged.connect(self._update_summary)
            self.team_table.setCellWidget(row, 3, role_combo)

            build_combo = QComboBox()
            build_combo.addItem("No build selected", None)
            build_combo.currentIndexChanged.connect(
                lambda _index, row_index=row: self._apply_saved_build(row_index)
            )
            self.team_table.setCellWidget(row, 5, build_combo)

        self.team_table.cellChanged.connect(lambda *_: self._update_summary())
        team_card.addWidget(self.team_table)
        root.addWidget(team_card, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        refresh = QPushButton("Refresh Saved Builds")
        refresh.clicked.connect(self.refresh_saved_builds)
        actions.addWidget(refresh)

        clear = QPushButton("Clear Plan")
        clear.clicked.connect(self.clear_plan)
        actions.addWidget(clear)

        actions.addStretch(1)

        research = FoundryButton("Build Research / Top Gear", role=ButtonRole.SECONDARY, compact=True)
        research.clicked.connect(lambda *_: self.pageRequested.emit("console:3"))
        actions.addWidget(research)

        comp = FoundryButton("Open Comp Maker", role=ButtonRole.SECONDARY, compact=True)
        comp.clicked.connect(lambda *_: self.pageRequested.emit("comp_builder"))
        actions.addWidget(comp)

        coverage = FoundryButton("Open Coverage", role=ButtonRole.SECONDARY, compact=True)
        coverage.clicked.connect(lambda *_: self.pageRequested.emit("console:7"))
        actions.addWidget(coverage)

        adviser = FoundryButton("Open Optimizer", role=ButtonRole.PRIMARY, compact=True)
        adviser.setToolTip("Open the existing optimization workspace while the Adviser remodel is still in progress.")
        adviser.clicked.connect(lambda *_: self.pageRequested.emit("console:6"))
        actions.addWidget(adviser)

        root.addLayout(actions)
        self.add_workspace(workspace)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

        self.trial_combo.currentTextChanged.connect(self._update_summary)
        self.difficulty_combo.currentTextChanged.connect(self._update_summary)
        self.plan_name_edit.textChanged.connect(self._update_summary)

    @staticmethod
    def _item_text(table: QTableWidget, row: int, column: int) -> str:
        item = table.item(row, column)
        return _clean(item.text() if item is not None else "")

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

    def refresh_saved_builds(self) -> None:
        try:
            roster = self.build_service.load()
            self.saved_builds = list(getattr(roster, "Members", ()) or ())
        except Exception as exc:
            self.saved_builds = []
            self.status.warning(f"Could not load saved builds: {exc}")

        for row in range(self.team_table.rowCount()):
            combo = self.team_table.cellWidget(row, 5)
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
        combo = self.team_table.cellWidget(row, 5)
        if not isinstance(combo, QComboBox):
            return
        index = combo.currentData()
        if not isinstance(index, int) or not 0 <= index < len(self.saved_builds):
            self._update_summary()
            return

        build = self.saved_builds[index]
        self._syncing_build_selection = True
        try:
            self._set_item_text(row, 1, getattr(build, "Gamertag", ""))
            self._set_item_text(row, 2, getattr(build, "Name", ""))
            self._set_item_text(row, 4, getattr(build, "EsoClass", ""))
            role_combo = self.team_table.cellWidget(row, 3)
            if isinstance(role_combo, QComboBox):
                role = _clean(getattr(build, "Role", ""))
                match = role_combo.findText(role, Qt.MatchFlag.MatchFixedString)
                if match < 0 and role.casefold() in {"dps", "dd", "damage dealer"}:
                    match = role_combo.findText("Damage Dealer")
                if match >= 0:
                    role_combo.setCurrentIndex(match)
        finally:
            self._syncing_build_selection = False
        self._update_summary()

    def current_plan(self) -> RaidPlan:
        members: list[RaidPlanMember] = []
        for row, seat in enumerate(RAID_PLAN_SEATS):
            role_combo = self.team_table.cellWidget(row, 3)
            build_combo = self.team_table.cellWidget(row, 5)
            role = role_combo.currentText() if isinstance(role_combo, QComboBox) else ""
            build_name = ""
            if isinstance(build_combo, QComboBox):
                saved_index = build_combo.currentData()
                if isinstance(saved_index, int) and 0 <= saved_index < len(self.saved_builds):
                    build_name = _clean(getattr(self.saved_builds[saved_index], "BuildName", ""))

            member = raid_plan_member_from_values(
                seat_id=seat,
                gamertag=self._item_text(self.team_table, row, 1),
                character_name=self._item_text(self.team_table, row, 2),
                role=role,
                eso_class=self._item_text(self.team_table, row, 4),
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

    def _update_summary(self, *_args) -> None:
        try:
            plan = self.current_plan()
        except Exception as exc:
            self.summary_label.setText(f"Plan cannot be assembled yet: {exc}")
            return

        characters = sum(member.character_selected for member in plan.members)
        builds = sum(member.build_selected for member in plan.members)
        self.summary_label.setText(
            f"{plan.name} • {self.trial_combo.currentText()} • {self.difficulty_combo.currentText()}\n"
            f"{len(plan.members)}/12 players named • {characters}/12 characters selected • {builds}/12 builds selected"
        )

    def clear_plan(self) -> None:
        self.team_table.blockSignals(True)
        try:
            for row in range(self.team_table.rowCount()):
                for column in (1, 2, 4):
                    self._set_item_text(row, column, "")
                role_combo = self.team_table.cellWidget(row, 3)
                if isinstance(role_combo, QComboBox):
                    role_combo.setCurrentIndex(0)
                build_combo = self.team_table.cellWidget(row, 5)
                if isinstance(build_combo, QComboBox):
                    build_combo.setCurrentIndex(0)
        finally:
            self.team_table.blockSignals(False)
        self._update_summary()
        self.status.info("Raid Plan session draft cleared. Existing Roster data was not changed.")


__all__ = [
    "RAID_PLAN_SEATS",
    "ROLE_OPTIONS",
    "RaidPlanPage",
    "raid_plan_member_from_values",
]
