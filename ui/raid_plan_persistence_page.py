from __future__ import annotations

"""Persistence-aware Raid Plan workspace.

This page adds explicit save/load controls around the existing player-aware planning
surface. Loading a plan restores only RaidPlan-owned choices; Personnel, Characters,
Saved Builds, Team records, and Rotation runtime state remain independently owned.
"""

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from engine.config import get_data_dir
from models.raid_plan import RaidPlan
from services.comp_builder_trial_scope import COMP_MAKER_TRIALS
from services.raid_plan_member_identity_resolution_service import (
    RaidPlanMemberIdentityResolutionService,
)
from services.raid_plan_repository import RaidPlanRepository, RaidPlanRepositoryError
from ui.raid_plan_page import RAID_PLAN_SEATS, _clean, _slug
from ui.raid_plan_stable_identity_selection_page import RaidPlanStableIdentitySelectionPage


def _same_player_identity(prior, visible) -> bool:
    """Prefer stable player ids; use gamertag only for fully legacy rows."""
    prior_id = _clean(getattr(prior, "player_id", ""))
    visible_id = _clean(getattr(visible, "player_id", ""))
    if prior_id or visible_id:
        return bool(prior_id and visible_id and prior_id == visible_id)
    return prior.gamertag.casefold() == visible.gamertag.casefold()


def _same_character_identity(prior, visible) -> bool:
    """Prefer stable character ids; use display name only for fully legacy rows."""
    prior_id = _clean(getattr(prior, "character_id", ""))
    visible_id = _clean(getattr(visible, "character_id", ""))
    if prior_id or visible_id:
        return bool(prior_id and visible_id and prior_id == visible_id)
    return _clean(prior.character_name).casefold() == _clean(visible.character_name).casefold()


def merge_visible_plan_with_loaded_snapshot(visible: RaidPlan, loaded: RaidPlan | None) -> RaidPlan:
    """Preserve plan-owned fields not editable on the current Raid Plan surface.

    Assignments, notes, stable identity references, and triggered responsibilities are
    already legitimate RaidPlan state even though this UI slice does not expose editors
    for all of them yet. Saving a loaded plan must not erase that hidden state.
    """
    if loaded is None or loaded.trial_id.casefold() != visible.trial_id.casefold():
        return visible

    prior_by_seat = {member.seat_id.casefold(): member for member in loaded.members}
    members = []
    for member in visible.members:
        prior = prior_by_seat.get(member.seat_id.casefold())
        if prior is not None and _same_player_identity(prior, member):
            same_character = _same_character_identity(prior, member)
            member = member.with_selection(
                roster_member_id=(
                    member.roster_member_id
                    if member.roster_member_id is not None
                    else prior.roster_member_id if same_character else None
                ),
                player_id=member.player_id or prior.player_id,
                character_id=(
                    member.character_id
                    or (prior.character_id if same_character else None)
                ),
                primary_assignment=prior.primary_assignment,
                secondary_assignment=prior.secondary_assignment,
                notes=prior.notes,
            )
        members.append(member)

    active_seats = {member.seat_id.casefold() for member in members}
    triggered = tuple(
        row
        for row in loaded.triggered_responsibilities
        if row.seat_id.casefold() in active_seats
    )
    return RaidPlan(
        plan_id=visible.plan_id,
        trial_id=visible.trial_id,
        name=visible.name,
        team_name=loaded.team_name,
        difficulty=visible.difficulty,
        plan_note=loaded.plan_note,
        status=loaded.status,
        members=tuple(members),
        triggered_responsibilities=triggered,
    )


class RaidPlanPersistencePage(RaidPlanStableIdentitySelectionPage):
    """Raid Plan editor with durable named-plan save/load controls."""

    def __init__(self, parent=None) -> None:
        self.plan_repository = RaidPlanRepository(get_data_dir() / "raid_plans.json")
        self._loading_plan = False
        self._loaded_plan_snapshot: RaidPlan | None = None
        super().__init__(parent)
        self.refresh_saved_plan_picker()

    def _build_ui(self) -> None:
        super()._build_ui()

        self.saved_plan_combo = QComboBox()
        self.saved_plan_combo.setMinimumWidth(230)
        self.saved_plan_combo.addItem("No saved plan", None)

        controls = QWidget()
        layout = QVBoxLayout(controls)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel("SAVED PLAN")
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(self.saved_plan_combo, 1)

        load_button = QPushButton("Load")
        load_button.clicked.connect(self.load_selected_plan)
        row.addWidget(load_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_current_plan)
        row.addWidget(save_button)

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.delete_selected_plan)
        row.addWidget(delete_button)

        layout.addLayout(row)
        self.header.add_context_widget(controls)

    def _selected_build_ids_by_seat(self) -> dict[str, str]:
        """Read stable BuildIds from the exact saved-build rows selected in the UI."""
        selected: dict[str, str] = {}
        for row, seat in enumerate(RAID_PLAN_SEATS):
            combo = self.team_table.cellWidget(row, 5)
            if not isinstance(combo, QComboBox):
                continue
            saved_index = combo.currentData()
            if not isinstance(saved_index, int) or not 0 <= saved_index < len(self.saved_builds):
                continue
            build_id = _clean(getattr(self.saved_builds[saved_index], "BuildId", ""))
            if build_id:
                selected[_slug(seat).casefold()] = build_id
        return selected

    def _stable_identity_resolver(self) -> RaidPlanMemberIdentityResolutionService:
        return RaidPlanMemberIdentityResolutionService(
            self.roster_service.db,
            self.build_service,
        )

    @staticmethod
    def _resolved_member(member, resolution):
        if resolution.unresolved:
            details = "; ".join(resolution.unresolved)
            raise ValueError(
                f"Raid Plan seat {member.seat_id!r} has contradictory stable identity: {details}"
            )
        return member.with_selection(
            roster_member_id=resolution.roster_member_id,
            player_id=resolution.player_id,
            character_id=resolution.character_id,
            selected_build_id=resolution.selected_build_id,
        )

    def current_plan(self) -> RaidPlan:
        visible = super().current_plan()
        selected_ids = self._selected_build_ids_by_seat()
        resolver = self._stable_identity_resolver()

        members = []
        for member in visible.members:
            candidate = member.with_selection(
                selected_build_id=selected_ids.get(member.seat_id.casefold())
            )
            members.append(self._resolved_member(candidate, resolver.resolve(candidate)))
        visible = replace(visible, members=tuple(members))

        merged = merge_visible_plan_with_loaded_snapshot(
            visible,
            self._loaded_plan_snapshot,
        )
        validated = tuple(
            self._resolved_member(member, resolver.resolve(member))
            for member in merged.members
        )
        return replace(merged, members=validated)

    def refresh_saved_plan_picker(self, *, select_plan_id: str | None = None) -> None:
        if not hasattr(self, "saved_plan_combo"):
            return
        wanted = _clean(select_plan_id).casefold()
        current = self.saved_plan_combo.currentData()
        if not wanted and isinstance(current, str):
            wanted = current.casefold()

        try:
            plans = self.plan_repository.list_plans()
        except RaidPlanRepositoryError as exc:
            self.status.error(f"Could not load saved Raid Plans: {exc}")
            return

        self.saved_plan_combo.blockSignals(True)
        self.saved_plan_combo.clear()
        self.saved_plan_combo.addItem("No saved plan", None)
        selected_index = 0
        for plan in plans:
            trial = self._trial_display_for(plan)
            label = f"{plan.name} • {trial}"
            self.saved_plan_combo.addItem(label, plan.plan_id)
            if wanted and plan.plan_id.casefold() == wanted:
                selected_index = self.saved_plan_combo.count() - 1
        self.saved_plan_combo.setCurrentIndex(selected_index)
        self.saved_plan_combo.blockSignals(False)

    @staticmethod
    def _trial_display_for(plan: RaidPlan) -> str:
        wanted = plan.trial_id.casefold()
        return next((name for name in COMP_MAKER_TRIALS if _slug(name) == wanted), plan.trial_id)

    def save_current_plan(self) -> None:
        try:
            plan = self.current_plan()
            self.plan_repository.save(plan)
        except (RaidPlanRepositoryError, ValueError, TypeError) as exc:
            self.status.error(f"Could not save Raid Plan: {exc}")
            return
        self._loaded_plan_snapshot = plan
        self.refresh_saved_plan_picker(select_plan_id=plan.plan_id)
        self.status.success(f"Saved Raid Plan: {plan.name}")

    def load_selected_plan(self) -> None:
        plan_id = self.saved_plan_combo.currentData()
        if not isinstance(plan_id, str) or not plan_id.strip():
            self.status.warning("Choose a saved Raid Plan to load.")
            return
        try:
            plan = self.plan_repository.get(plan_id)
        except RaidPlanRepositoryError as exc:
            self.status.error(f"Could not load Raid Plan: {exc}")
            return
        if plan is None:
            self.status.warning("That saved Raid Plan no longer exists.")
            self.refresh_saved_plan_picker()
            return
        self.apply_plan(plan)
        self.status.success(f"Loaded Raid Plan: {plan.name}")

    def delete_selected_plan(self) -> None:
        plan_id = self.saved_plan_combo.currentData()
        if not isinstance(plan_id, str) or not plan_id.strip():
            self.status.warning("Choose a saved Raid Plan to delete.")
            return
        try:
            deleted = self.plan_repository.delete(plan_id)
        except RaidPlanRepositoryError as exc:
            self.status.error(f"Could not delete Raid Plan: {exc}")
            return
        if (
            deleted
            and self._loaded_plan_snapshot is not None
            and self._loaded_plan_snapshot.plan_id.casefold() == plan_id.casefold()
        ):
            self._loaded_plan_snapshot = None
        self.refresh_saved_plan_picker()
        if deleted:
            self.status.info("Saved Raid Plan deleted. Personnel and saved builds were unchanged.")
        else:
            self.status.warning("That saved Raid Plan no longer exists.")

    def clear_plan(self) -> None:
        self._loaded_plan_snapshot = None
        super().clear_plan()
        self.refresh_saved_plan_picker(select_plan_id=None)

    def apply_plan(self, plan: RaidPlan) -> None:
        """Restore one persisted planning snapshot without mutating global identity."""
        if not isinstance(plan, RaidPlan):
            raise TypeError("plan must be a RaidPlan")

        self._loading_plan = True
        self.team_table.blockSignals(True)
        try:
            trial_display = self._trial_display_for(plan)
            trial_index = self.trial_combo.findText(trial_display, Qt.MatchFlag.MatchFixedString)
            if trial_index >= 0:
                self.trial_combo.setCurrentIndex(trial_index)
            if plan.difficulty:
                difficulty_index = self.difficulty_combo.findText(
                    plan.difficulty, Qt.MatchFlag.MatchFixedString
                )
                if difficulty_index >= 0:
                    self.difficulty_combo.setCurrentIndex(difficulty_index)
            self.plan_name_edit.setText(plan.name)

            members_by_seat = {member.seat_id.casefold(): member for member in plan.members}
            for row, seat in enumerate(RAID_PLAN_SEATS):
                member = members_by_seat.get(_slug(seat).casefold())
                self._set_player_text(row, member.gamertag if member else "")
                self._refresh_character_options(row)
                self._set_item_text(row, 2, member.character_name if member else "")
                self._apply_character_class(row)

                role_combo = self.team_table.cellWidget(row, 3)
                if isinstance(role_combo, QComboBox):
                    role_combo.setCurrentIndex(0)
                    if member and member.role:
                        role_index = role_combo.findText(member.role, Qt.MatchFlag.MatchFixedString)
                        if role_index < 0 and member.role.casefold() in {"dd", "dps", "damage dealer"}:
                            role_index = role_combo.findText("Damage Dealer")
                        if role_index >= 0:
                            role_combo.setCurrentIndex(role_index)

                self._set_item_text(row, 4, member.eso_class if member else "")
                self._refresh_build_options(row)
                build_combo = self.team_table.cellWidget(row, 5)
                if isinstance(build_combo, QComboBox):
                    build_combo.setCurrentIndex(0)
                    if member:
                        matched = False
                        if member.selected_build_id:
                            wanted_id = member.selected_build_id.casefold()
                            for combo_index in range(1, build_combo.count()):
                                saved_index = build_combo.itemData(combo_index)
                                if not isinstance(saved_index, int) or not 0 <= saved_index < len(self.saved_builds):
                                    continue
                                build_id = _clean(getattr(self.saved_builds[saved_index], "BuildId", ""))
                                if build_id.casefold() == wanted_id:
                                    build_combo.setCurrentIndex(combo_index)
                                    matched = True
                                    break
                        if not matched and member.selected_build_name:
                            for combo_index in range(1, build_combo.count()):
                                saved_index = build_combo.itemData(combo_index)
                                if not isinstance(saved_index, int) or not 0 <= saved_index < len(self.saved_builds):
                                    continue
                                build_name = _clean(getattr(self.saved_builds[saved_index], "BuildName", ""))
                                if build_name.casefold() == member.selected_build_name.casefold():
                                    build_combo.setCurrentIndex(combo_index)
                                    break
                self._refresh_personnel_button(row)
        finally:
            self.team_table.blockSignals(False)
            self._loading_plan = False

        self._loaded_plan_snapshot = plan
        self.refresh_saved_plan_picker(select_plan_id=plan.plan_id)
        self._update_summary()


__all__ = ["RaidPlanPersistencePage", "merge_visible_plan_with_loaded_snapshot"]
