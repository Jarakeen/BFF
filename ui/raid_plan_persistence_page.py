from __future__ import annotations

"""Persistence-aware Raid Plan workspace.

This page adds explicit save/load controls around the existing player-aware planning
surface. Loading a plan restores only RaidPlan-owned choices; Personnel, Characters,
Saved Builds, Team records, and Rotation runtime state remain independently owned.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from engine.config import get_data_dir
from models.raid_plan import RaidPlan
from services.comp_builder_trial_scope import COMP_MAKER_TRIALS
from services.raid_plan_repository import RaidPlanRepository, RaidPlanRepositoryError
from ui.raid_plan_character_selection_page import RaidPlanCharacterSelectionPage
from ui.raid_plan_page import RAID_PLAN_SEATS, _clean, _slug


class RaidPlanPersistencePage(RaidPlanCharacterSelectionPage):
    """Raid Plan editor with durable named-plan save/load controls."""

    def __init__(self, parent=None) -> None:
        self.plan_repository = RaidPlanRepository(get_data_dir() / "raid_plans.json")
        self._loading_plan = False
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
        self.refresh_saved_plan_picker()
        if deleted:
            self.status.info("Saved Raid Plan deleted. Personnel and saved builds were unchanged.")
        else:
            self.status.warning("That saved Raid Plan no longer exists.")

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
                    if member and member.selected_build_name:
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

        self.refresh_saved_plan_picker(select_plan_id=plan.plan_id)
        self._update_summary()


__all__ = ["RaidPlanPersistencePage"]
