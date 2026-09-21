from __future__ import annotations

"""Persistence-aware Raid Plan workspace.

This page adds explicit save/load controls around the existing player-aware planning
surface. Loading a plan restores only RaidPlan-owned choices; Personnel, Characters,
Saved Builds, Team records, and Rotation runtime state remain independently owned.
"""

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from engine.config import get_data_dir
from models.raid_plan import RaidPlan
from services.comp_builder_trial_scope import COMP_MAKER_TRIALS
from services.finch_shared_import_service import (
    import_shared_raid_plan_from_finch,
    list_shared_raid_plans_from_finch,
)
from services.finch_shared_publish_service import publish_raid_plan_to_finch
from services.raid_plan_member_identity_resolution_service import (
    RaidPlanMemberIdentityResolutionService,
)
from services.raid_plan_repository import RaidPlanRepository, RaidPlanRepositoryError
from ui.raid_plan_page import (
    RAID_PLAN_SEATS,
    _clean,
    _slug,
    is_seat_placeholder,
    new_personnel_member,
)
from ui.raid_plan_stable_identity_selection_page import RaidPlanStableIdentitySelectionPage


_FINCH_PLAN_PUBLISH_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="finch-plan-publish",
)
_FINCH_PLAN_READ_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="finch-plan-read",
)


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
                gamertag=member.gamertag,
                character_name=member.character_name,
                role=member.role,
                eso_class=member.eso_class,
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
                selected_build_id=member.selected_build_id or prior.selected_build_id,
                selected_build_name=member.selected_build_name or prior.selected_build_name,
                build_source_kind=prior.build_source_kind,
                build_source_name=prior.build_source_name,
                build_source_url=prior.build_source_url,
                candidate_id=prior.candidate_id,
                planned_gear_sets=prior.planned_gear_sets,
                planned_skills=prior.planned_skills,
                planned_mundus=prior.planned_mundus,
                primary_assignment=prior.primary_assignment,
                secondary_assignment=prior.secondary_assignment,
                utility_assignments=prior.utility_assignments,
                comp_locked_fields=prior.comp_locked_fields,
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

    assignmentsRequested = Signal(str)

    def __init__(self, parent=None) -> None:
        self.plan_repository = RaidPlanRepository(get_data_dir() / "raid_plans.json")
        self._loading_plan = False
        self._loaded_plan_snapshot: RaidPlan | None = None
        self._finch_plan_publish_future: Future | None = None
        super().__init__(parent)
        self._finch_plan_publish_timer = QTimer(self)
        self._finch_plan_publish_timer.setInterval(100)
        self._finch_plan_publish_timer.timeout.connect(self._poll_raid_plan_publish)
        self._finch_plan_read_future: Future | None = None
        self._finch_plan_read_mode = ""
        self._finch_plan_read_timer = QTimer(self)
        self._finch_plan_read_timer.setInterval(100)
        self._finch_plan_read_timer.timeout.connect(self._poll_shared_plan_read)
        lower_save = getattr(self, "lower_save_plan_button", None)
        if lower_save is not None:
            lower_save.clicked.connect(self.save_current_plan)
        self.refresh_saved_plan_picker()
        self._navigation_baseline_plan = self.current_plan()

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

        self.publish_plan_finch_button = QPushButton("Publish")
        self.publish_plan_finch_button.setToolTip(
            "Publish this saved Raid Plan outline to Finch. Unsaved edits must be saved first."
        )
        self.publish_plan_finch_button.clicked.connect(self._publish_saved_plan_to_finch)
        row.addWidget(self.publish_plan_finch_button)

        self.get_shared_plans_button = QPushButton("Get Shared Plans")
        self.get_shared_plans_button.setToolTip(
            "Browse Raid Plans published to Finch. Copy to Local creates a new local Raid Plan outline and never replaces an existing plan."
        )
        self.get_shared_plans_button.clicked.connect(self._get_shared_raid_plans)
        row.addWidget(self.get_shared_plans_button)

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.delete_selected_plan)
        row.addWidget(delete_button)

        layout.addLayout(row)
        self.header.add_context_widget(controls)

    def _publish_saved_plan_to_finch(self) -> None:
        if self.has_pending_changes():
            self.status.warning("Save Raid Plan changes before publishing to Finch.")
            return

        plan_id = self.saved_plan_combo.currentData()
        if not isinstance(plan_id, str) or not plan_id.strip():
            loaded = getattr(self, "_loaded_plan_snapshot", None)
            plan_id = str(getattr(loaded, "plan_id", "") or "").strip()
        if not plan_id:
            self.status.warning("Save this Raid Plan before publishing to Finch.")
            return

        if (
            self._finch_plan_publish_future is not None
            and not self._finch_plan_publish_future.done()
        ):
            self.status.info("A Finch Raid Plan publish is already running.")
            return

        self.publish_plan_finch_button.setEnabled(False)
        self.status.info("Publishing saved Raid Plan to Finch…")
        self._finch_plan_publish_future = _FINCH_PLAN_PUBLISH_EXECUTOR.submit(
            publish_raid_plan_to_finch,
            database_path=Path(get_data_dir()) / "eso.db",
            raid_plans_path=Path(get_data_dir()) / "raid_plans.json",
            plan_id=plan_id,
            settings_path=Path("settings.json"),
        )
        self._finch_plan_publish_timer.start()

    def _poll_raid_plan_publish(self) -> None:
        future = self._finch_plan_publish_future
        if future is None or not future.done():
            return

        self._finch_plan_publish_timer.stop()
        self._finch_plan_publish_future = None
        self.publish_plan_finch_button.setEnabled(True)
        try:
            result = future.result()
        except Exception as exc:
            self.status.error(f"Finch Raid Plan publish failed: {exc}")
            return
        self.status.success(
            f"Published Raid Plan to Finch: {result.snapshot_key}"
        )

    def _get_shared_raid_plans(self) -> None:
        if self._finch_plan_read_future is not None and not self._finch_plan_read_future.done():
            self.status.info("A Finch shared Raid Plan request is already running.")
            return
        self.get_shared_plans_button.setEnabled(False)
        self._finch_plan_read_mode = "list"
        self.status.info("Fetching shared Raid Plans from Finch…")
        self._finch_plan_read_future = _FINCH_PLAN_READ_EXECUTOR.submit(
            list_shared_raid_plans_from_finch,
            database_path=Path(get_data_dir()) / "eso.db",
            raid_plans_path=Path(get_data_dir()) / "raid_plans.json",
            settings_path=Path("settings.json"),
        )
        self._finch_plan_read_timer.start()

    def _poll_shared_plan_read(self) -> None:
        future = self._finch_plan_read_future
        if future is None or not future.done():
            return

        mode = self._finch_plan_read_mode
        self._finch_plan_read_future = None
        self._finch_plan_read_mode = ""

        try:
            result = future.result()
        except Exception as exc:
            self._finch_plan_read_timer.stop()
            self.get_shared_plans_button.setEnabled(True)
            self.status.error(f"Finch shared Raid Plan request failed: {exc}")
            return

        if mode == "list":
            previews = tuple(result)
            if not previews:
                self._finch_plan_read_timer.stop()
                self.get_shared_plans_button.setEnabled(True)
                self.status.info("Finch has no shared Raid Plans yet.")
                return
            labels = [
                (
                    f"{row.name} • {row.trial_id}"
                    + (f" • {row.team_name}" if row.team_name else "")
                    + f" • {row.member_count} seat(s)"
                )
                for row in previews
            ]
            selected, ok = QInputDialog.getItem(
                self,
                "Shared Raid Plans on Finch",
                "Copy shared Raid Plan to Local:",
                labels,
                0,
                False,
            )
            if not ok:
                self._finch_plan_read_timer.stop()
                self.get_shared_plans_button.setEnabled(True)
                self.status.info("Shared Raid Plan copy cancelled.")
                return
            index = labels.index(selected)
            preview = previews[index]
            answer = QMessageBox.question(
                self,
                "Copy Shared Raid Plan to Local",
                (
                    f'Copy "{preview.name}" from Finch into a new local Raid Plan?\n\n'
                    "This creates a separate local plan outline with shared seat/player/character/class/role data only. "
                    "It never replaces an existing plan and does not create Personnel or saved builds."
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self._finch_plan_read_timer.stop()
                self.get_shared_plans_button.setEnabled(True)
                self.status.info("Shared Raid Plan import cancelled.")
                return
            self._finch_plan_read_mode = "import"
            self._finch_plan_read_future = _FINCH_PLAN_READ_EXECUTOR.submit(
                import_shared_raid_plan_from_finch,
                snapshot_key=preview.snapshot_key,
                database_path=Path(get_data_dir()) / "eso.db",
                raid_plans_path=Path(get_data_dir()) / "raid_plans.json",
                settings_path=Path("settings.json"),
            )
            return

        self._finch_plan_read_timer.stop()
        self.get_shared_plans_button.setEnabled(True)
        plan = result
        self.refresh_saved_plan_picker(select_plan_id=plan.plan_id)
        self.status.success(
            f"Copied shared Raid Plan from Finch into local plan: {plan.name}."
        )

    def _selected_build_ids_by_seat(self) -> dict[str, str]:
        """Read stable BuildIds from the exact saved-build rows selected in the UI."""
        selected: dict[str, str] = {}
        for row, seat in enumerate(RAID_PLAN_SEATS):
            combo = self.team_table.cellWidget(row, 4)
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

    def has_pending_changes(self) -> bool:
        """Return whether visible Raid Plan state differs from the last clean snapshot."""
        baseline = getattr(self, "_navigation_baseline_plan", None)
        if baseline is None:
            return False
        try:
            return self.current_plan() != baseline
        except Exception:
            # A page that cannot currently assemble its plan should not silently
            # allow navigation and lose whatever the user was editing.
            return True

    def save_pending_changes(self) -> bool:
        self.save_current_plan()
        return not self.has_pending_changes()

    def discard_pending_changes(self) -> bool:
        loaded = getattr(self, "_loaded_plan_snapshot", None)
        if loaded is not None:
            self.apply_plan(loaded)
        else:
            super().clear_plan()
            self.refresh_saved_plan_picker(select_plan_id=None)
            self._navigation_baseline_plan = self.current_plan()
        return True

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

    def _active_team_name(self) -> str:
        loaded = getattr(self, "_loaded_plan_snapshot", None)
        return _clean(getattr(loaded, "team_name", "")) if loaded is not None else ""

    def _ensure_named_players_in_personnel(self) -> int:
        """Promote typed Raid Plan gamertags and attach them to the plan's Team."""
        created = 0
        team_name = self._active_team_name()
        for row in range(self.team_table.rowCount()):
            gamertag = self._player_text(row)
            if not gamertag or is_seat_placeholder(gamertag):
                continue
            existing = self._personnel_match(gamertag)
            if existing is None:
                member_id = self.roster_service.create_member(new_personnel_member(gamertag))
                created += 1
            else:
                member_id = int(existing.Id) if existing.Id is not None else 0
            if team_name and member_id > 0:
                self.roster_service.add_member_to_team(member_id, team_name)

        # Do not refresh Raid Plan widgets here. Character/build refresh can
        # legitimately auto-fill from Personnel, but Save must snapshot the user's
        # visible chair edits before any such UI normalization runs.
        return created

    def save_player_to_personnel(self, row: int) -> None:
        """Save one player and, when this plan owns a Team, add that player to it."""
        gamertag = self._player_text(row)
        if is_seat_placeholder(gamertag):
            self.status.warning("Raid Plan seat placeholders cannot be saved as players.")
            return
        super().save_player_to_personnel(row)
        member = self._personnel_match(gamertag)
        team_name = self._active_team_name()
        if member is None or member.Id is None or not team_name:
            return
        try:
            self.roster_service.add_member_to_team(int(member.Id), team_name)
            self.refresh_personnel()
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self.status.error(f"Player saved, but Team membership could not be updated: {exc}")
            return
        self.status.success(f"{gamertag} is in Personnel and on Team {team_name}.")

    def save_current_plan(self) -> RaidPlan | None:
        try:
            # Capture the visible Raid Plan before Personnel synchronization can
            # rebuild character/build widgets or auto-derive class values.
            visible_before_sync = super().current_plan()
            created_players = self._ensure_named_players_in_personnel()

            # Re-run the persistence/stable-identity layer after Personnel creation,
            # but restore the captured visible chair values as authoritative.
            plan = self.current_plan()
            captured_by_seat = {
                member.seat_id.casefold(): member
                for member in visible_before_sync.members
            }
            plan = replace(
                plan,
                members=tuple(
                    member.with_selection(
                        gamertag=captured_by_seat.get(
                            member.seat_id.casefold(), member
                        ).gamertag,
                        character_name=captured_by_seat.get(
                            member.seat_id.casefold(), member
                        ).character_name,
                        role=captured_by_seat.get(
                            member.seat_id.casefold(), member
                        ).role,
                        eso_class=captured_by_seat.get(
                            member.seat_id.casefold(), member
                        ).eso_class,
                        selected_build_name=captured_by_seat.get(
                            member.seat_id.casefold(), member
                        ).selected_build_name,
                    )
                    for member in plan.members
                ),
            )
            self.plan_repository.save(plan)
            persisted = self.plan_repository.get(plan.plan_id)
            if persisted is None:
                raise RaidPlanRepositoryError(
                    f"saved plan {plan.plan_id!r} could not be read back"
                )
            if persisted != plan:
                raise RaidPlanRepositoryError(
                    "saved Raid Plan did not round-trip exactly; refusing to report success"
                )
        except (RaidPlanRepositoryError, ValueError, TypeError) as exc:
            self.status.error(f"Could not save Raid Plan: {exc}")
            return None

        self._loaded_plan_snapshot = persisted

        # Personnel can be refreshed safely only after the durable snapshot exists.
        # Reapply that snapshot afterward so autocomplete/source-backed defaults
        # cannot alter the just-saved chair values.
        self.refresh_personnel()
        self.apply_plan(persisted)
        self.refresh_saved_plan_picker(select_plan_id=persisted.plan_id)

        characters = sum(1 for member in persisted.members if member.character_name)
        roles = sum(1 for member in persisted.members if member.role)
        planned = sum(
            1
            for member in persisted.members
            if member.selected_build_name or member.planned_gear_sets
        )
        created_note = (
            f" • {created_players} new player(s) added to Personnel"
            if created_players
            else ""
        )
        self.status.success(
            f"Saved Raid Plan: {persisted.name} • "
            f"{len(persisted.members)} player(s) • {characters} character(s) • "
            f"{roles} role(s) • {planned} planned build(s){created_note}"
        )
        return persisted

    def _open_assignments(self, *_args) -> None:
        """Persist this plan, then explicitly hand its stable id to Assignments."""
        persisted = self.save_current_plan()
        if persisted is None:
            return
        self.assignmentsRequested.emit(persisted.plan_id)

    def load_plan_by_id(self, plan_id: str) -> bool:
        """Load one exact saved Raid Plan without relying on navigation history."""
        wanted = _clean(plan_id)
        if not wanted:
            return False
        self.refresh_saved_plan_picker(select_plan_id=wanted)
        index = self.saved_plan_combo.findData(wanted)
        if index < 0:
            self.status.warning("That saved Raid Plan is no longer available.")
            return False
        self.saved_plan_combo.setCurrentIndex(index)
        self.load_selected_plan()
        loaded = getattr(self, "_loaded_plan_snapshot", None)
        return bool(
            loaded is not None
            and loaded.plan_id.casefold() == wanted.casefold()
        )

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

                class_combo = self.team_table.cellWidget(row, 3)
                if isinstance(class_combo, QComboBox):
                    class_combo.setCurrentText(member.eso_class if member and member.eso_class else "")
                self._refresh_build_options(row)
                build_combo = self.team_table.cellWidget(row, 4)
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
                                    matched = True
                                    break
                        if (
                            not matched
                            and member.selected_build_name
                            and (
                                member.planned_gear_sets
                                or member.planned_skills
                                or member.planned_mundus
                                or member.candidate_id
                                or member.build_source_kind
                            )
                        ):
                            planned_sets = " + ".join(member.planned_gear_sets[:2])
                            planned_label = (
                                f"Planned • {planned_sets}"
                                if planned_sets
                                else f"Planned • {member.selected_build_name}"
                            )
                            build_combo.addItem(
                                planned_label,
                                f"planned:{member.seat_id}",
                            )
                            build_combo.setItemData(
                                build_combo.count() - 1,
                                " • ".join(member.planned_gear_sets)
                                or member.selected_build_name,
                                Qt.ItemDataRole.ToolTipRole,
                            )
                            build_combo.setCurrentIndex(build_combo.count() - 1)
                self._refresh_personnel_button(row)
        finally:
            self.team_table.blockSignals(False)
            self._loading_plan = False

        self._loaded_plan_snapshot = plan
        self.refresh_saved_plan_picker(select_plan_id=plan.plan_id)
        self._update_summary()
        self._navigation_baseline_plan = self.current_plan()


__all__ = ["RaidPlanPersistencePage", "merge_visible_plan_with_loaded_snapshot"]
