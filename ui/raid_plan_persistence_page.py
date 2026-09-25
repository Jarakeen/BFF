from __future__ import annotations

"""Persistence-aware Raid Plan workspace.

This page adds explicit save/load controls around the existing player-aware planning
surface. Loading a plan restores only RaidPlan-owned choices; Personnel, Characters,
Saved Builds, Team records, and Rotation runtime state remain independently owned.
"""

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFileDialog, QComboBox, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from engine.config import get_data_dir, get_user_data_dir, get_user_database_path, get_settings_path
from models.raid_plan import RaidPlan
from services.comp_builder_trial_scope import COMP_MAKER_TRIALS
from services.finch_shared_provenance_service import format_shared_timestamp
from services.finch_shared_import_service import (
    import_shared_raid_plan_from_finch,
    list_shared_raid_plans_from_finch,
)
from services.finch_shared_publish_service import publish_raid_plan_to_finch
from services.raid_plan_member_identity_resolution_service import (
    RaidPlanMemberIdentityResolutionService,
)
from services.raid_plan_backup_service import (
    RaidPlanBackupError,
    export_raid_plan_backup,
    load_raid_plan_backup,
)
from services.raid_plan_repository import RaidPlanRepository, RaidPlanRepositoryError
from services.ui_draft_recovery_service import UiDraftRecoveryService
from services.user_safety_snapshot_service import UserSafetySnapshotService
from ui.raid_plan_page import (
    RAID_PLAN_SEATS,
    _clean,
    _slug,
    is_seat_placeholder,
    new_personnel_member,
)
from ui.raid_plan_stable_identity_selection_page import RaidPlanStableIdentitySelectionPage
from ui.ui_safety import (
    confirm_destructive_action,
    confirm_unsaved_changes,
    mark_save_failed,
    mark_saved,
    set_enabled_reason,
)


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
        # A loaded Raid Plan keeps its stable persisted identity even when visible
        # identity text changes through an explicit Rename operation. Recomputing
        # plan_id from the display name would fork the plan into a duplicate row.
        plan_id=loaded.plan_id,
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
    raidMapRequested = Signal(str)

    def __init__(self, parent=None) -> None:
        self.plan_repository = RaidPlanRepository(get_user_database_path())
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
        self._draft_service = UiDraftRecoveryService()
        self._safety_snapshots = UserSafetySnapshotService()
        self._draft_timer = QTimer(self)
        self._draft_timer.setInterval(2000)
        self._draft_timer.timeout.connect(self._autosave_recovery_draft)
        self._draft_timer.start()
        lower_save = getattr(self, "lower_save_plan_button", None)
        if lower_save is not None:
            lower_save.clicked.connect(self.save_current_plan)
        self.refresh_saved_plan_picker()
        self._navigation_baseline_plan = self.current_plan()
        self._refresh_action_availability()

    def _draft_key(self, plan_id: str | None = None) -> str:
        explicit = _clean(plan_id)
        if explicit:
            return f"raid-plan-{explicit}"
        loaded = getattr(self, "_loaded_plan_snapshot", None)
        loaded_id = _clean(getattr(loaded, "plan_id", "")) if loaded is not None else ""
        return f"raid-plan-{loaded_id or 'new'}"

    def _autosave_recovery_draft(self) -> None:
        if not self.has_pending_changes():
            return
        try:
            plan = self.current_plan()
            self._draft_service.save(
                self._draft_key(plan.plan_id),
                {"kind": "raid_plan", "plan": asdict(plan)},
            )
        except Exception:
            # Draft creation is a safety net, never a reason to interrupt editing.
            return

    def _discard_recovery_draft(self, plan_id: str | None = None) -> None:
        self._draft_service.discard(self._draft_key(plan_id))

    def _offer_recovery_draft(self, saved_plan: RaidPlan) -> RaidPlan:
        draft = self._draft_service.load(self._draft_key(saved_plan.plan_id))
        payload = draft.get("payload") if isinstance(draft, dict) else None
        raw_plan = payload.get("plan") if isinstance(payload, dict) else None
        if not isinstance(raw_plan, dict):
            return saved_plan
        try:
            recovered = self.plan_repository._decode_plan(raw_plan)
        except Exception:
            return saved_plan
        if recovered == saved_plan:
            self._discard_recovery_draft(saved_plan.plan_id)
            return saved_plan

        box = QMessageBox(self)
        box.setWindowTitle("Recovered Raid Plan Draft")
        box.setText(f'FoundryDock recovered unsaved changes for "{saved_plan.name}".')
        box.setInformativeText(
            "Restore the recovered draft, use the last saved version, or cancel loading."
        )
        restore = box.addButton("Restore Draft", QMessageBox.ButtonRole.AcceptRole)
        saved = box.addButton("Use Saved Version", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(saved)
        box.exec()
        clicked = box.clickedButton()
        if clicked is cancel:
            raise RaidPlanRepositoryError("Raid Plan load cancelled.")
        if clicked is saved:
            self._discard_recovery_draft(saved_plan.plan_id)
            return saved_plan
        return recovered

    def showEvent(self, event) -> None:
        """Reconcile this long-lived page with the latest persisted Raid Plan.

        Roles, Assignments, Comp Maker, Builds, and Readiness are separate page
        instances. When another page saves the shared Raid Plan, reopening this
        page must hydrate that newer snapshot instead of continuing to show stale
        chair/build state. Unsaved local edits are never overwritten.
        """
        super().showEvent(event)
        loaded = getattr(self, "_loaded_plan_snapshot", None)
        if loaded is None:
            return
        try:
            if self.has_pending_changes():
                return
            latest = self.plan_repository.get(loaded.plan_id)
            if latest is not None and latest != loaded:
                self.apply_plan(latest)
                self.status.info(f"Reloaded latest saved Raid Plan: {latest.name}")
        except Exception as exc:
            self.status.warning(
                f"Could not refresh the latest Raid Plan on page entry: {type(exc).__name__}: {exc}"
            )

    def _build_ui(self) -> None:
        super()._build_ui()

        self.saved_plan_combo = QComboBox()
        self.saved_plan_combo.setMinimumWidth(230)
        self.saved_plan_combo.addItem("New Plan…", "__new_plan__")
        self.saved_plan_combo.addItem("No saved plan", None)
        self.saved_plan_combo.activated.connect(self._saved_plan_activated)
        self.saved_plan_combo.currentIndexChanged.connect(self._saved_plan_selection_changed)

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

        self.load_plan_button = QPushButton("Load")
        self.load_plan_button.clicked.connect(self.load_selected_plan)
        row.addWidget(self.load_plan_button)

        self.save_plan_button = QPushButton("Save")
        self.save_plan_button.clicked.connect(self.save_current_plan)
        row.addWidget(self.save_plan_button)

        self.backup_plan_button = QPushButton("Backup…")
        self.backup_plan_button.setToolTip(
            "Write this Raid Plan to a small portable JSON backup file."
        )
        self.backup_plan_button.clicked.connect(self.export_raid_plan_backup)
        row.addWidget(self.backup_plan_button)

        self.restore_plan_backup_button = QPushButton("Restore Backup…")
        self.restore_plan_backup_button.setToolTip(
            "Restore one Raid Plan from a portable JSON backup. Other user data is untouched."
        )
        self.restore_plan_backup_button.clicked.connect(self.restore_raid_plan_backup)
        row.addWidget(self.restore_plan_backup_button)

        self.open_raid_map_button = QPushButton("Open Raid Map")
        self.open_raid_map_button.setToolTip("Open the Raid Map editor scoped to this saved Raid Plan.")
        self.open_raid_map_button.clicked.connect(self._open_saved_plan_raid_map)
        row.addWidget(self.open_raid_map_button)

        self.publish_plan_finch_button = QPushButton("Publish")
        self.publish_plan_finch_button.setToolTip(
            "Publish this saved Raid Plan outline to Finch. Unsaved edits must be saved first."
        )
        self.publish_plan_finch_button.clicked.connect(self._publish_saved_plan_to_finch)
        row.addWidget(self.publish_plan_finch_button)

        self.get_shared_plans_button = QPushButton("Get Shared Plans")
        self.get_shared_plans_button.setToolTip(
            "Browse Raid Plans published to Finch. Copy to Local creates a new local Raid Plan outline with shared assignments and build summaries, and never replaces an existing plan."
        )
        self.get_shared_plans_button.clicked.connect(self._get_shared_raid_plans)
        row.addWidget(self.get_shared_plans_button)

        self.archive_plan_button = QPushButton("Archive")
        self.archive_plan_button.setToolTip(
            "Archive this Raid Plan without deleting Personnel, Builds, maps, or the plan itself."
        )
        self.archive_plan_button.clicked.connect(self.toggle_archive_selected_plan)
        row.addWidget(self.archive_plan_button)

        self.delete_plan_button = QPushButton("Delete")
        self.delete_plan_button.clicked.connect(self.delete_selected_plan)
        row.addWidget(self.delete_plan_button)

        layout.addLayout(row)
        self.saved_plan_controls = controls
        self.header.add_context_widget(controls)
        self._plan_name_context = getattr(self, "plan_name_context", None)
        self._set_plan_name_visible(
            self.saved_plan_combo.currentData() == "__new_plan__"
        )

    def _set_plan_name_visible(self, visible: bool) -> None:
        container = getattr(self, "_plan_name_context", None)
        if container is not None:
            container.setVisible(bool(visible))
        else:
            self.plan_name_edit.setVisible(bool(visible))

    def _saved_plan_selection_changed(self, _index: int) -> None:
        """Show the Plan-name field only while explicitly creating a new plan."""
        self._set_plan_name_visible(
            self.saved_plan_combo.currentData() == "__new_plan__"
        )

    def _saved_plan_activated(self, index: int) -> None:
        if self.saved_plan_combo.itemData(index) != "__new_plan__":
            return
        self._loaded_plan_snapshot = None
        super().clear_plan()
        self.plan_name_edit.setText("New Raid Plan")
        self._set_plan_name_visible(True)
        self.plan_name_edit.setFocus()
        self.plan_name_edit.selectAll()
        self.status.info("New Raid Plan: name it, choose the trial, then save when ready.")

    @staticmethod
    def _backup_filename(plan: RaidPlan) -> str:
        stem = _slug(plan.name or plan.plan_id or "raid-plan") or "raid-plan"
        return f"{stem}.raidplan.json"

    def export_raid_plan_backup(self) -> None:
        try:
            plan = self.current_plan()
        except Exception as exc:
            self.status.error(f"Could not assemble Raid Plan backup: {exc}")
            return

        backup_dir = get_user_data_dir() / "raid_plan_backups"
        default_path = backup_dir / self._backup_filename(plan)
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Raid Plan Backup",
            str(default_path),
            "FoundryDock Raid Plan Backup (*.raidplan.json *.json)",
        )
        if not filename:
            return
        try:
            destination = export_raid_plan_backup(plan, filename)
        except (OSError, TypeError, ValueError) as exc:
            self.status.error(f"Raid Plan backup failed: {exc}")
            return
        self.status.success(f"Raid Plan backup written: {destination}")

    def restore_raid_plan_backup(self) -> None:
        backup_dir = get_user_data_dir() / "raid_plan_backups"
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Restore Raid Plan Backup",
            str(backup_dir),
            "FoundryDock Raid Plan Backup (*.raidplan.json *.json)",
        )
        if not filename:
            return
        try:
            plan = load_raid_plan_backup(filename)
        except RaidPlanBackupError as exc:
            self.status.error(f"Could not open Raid Plan backup: {exc}")
            return

        if self.has_pending_changes() and not confirm_unsaved_changes(
            self,
            self,
            action_text="restore a Raid Plan backup",
        ):
            return

        occupied = sum(
            1
            for member in plan.members
            if _clean(member.gamertag) or _clean(member.character_name)
        )
        existing = self.plan_repository.get(plan.plan_id)
        impact = (
            f'Backup: "{plan.name}" • {self._trial_display_for(plan)} • '
            f"{occupied} occupied seat(s). "
        )
        if existing is not None:
            impact += (
                "This will replace the currently saved version of this Raid Plan only. "
            )
        else:
            impact += "This will create this Raid Plan from the backup. "
        impact += (
            "Personnel, Teams, Characters, Builds, other Raid Plans, and ESO reference data "
            "will not be changed. A full database safety snapshot is created first."
        )
        if not confirm_destructive_action(
            self,
            title="Restore Raid Plan Backup",
            object_label=f'Restore "{plan.name}" from this backup?',
            impact=impact,
            confirm_text="Restore Backup",
        ):
            return

        checkpoint = self._safety_snapshots.create(
            f"before-raid-plan-backup-restore-{plan.plan_id}"
        )
        if checkpoint is None and get_user_database_path().is_file():
            self.status.error(
                "Raid Plan backup was not restored because the pre-restore safety snapshot failed."
            )
            return

        try:
            self.plan_repository.save(plan)
            persisted = self.plan_repository.get(plan.plan_id)
            if persisted is None or persisted != plan:
                raise RaidPlanRepositoryError(
                    "restored Raid Plan did not round-trip exactly"
                )
        except Exception as exc:
            self.status.error(f"Could not restore Raid Plan backup: {exc}")
            return

        self._discard_recovery_draft(plan.plan_id)
        self.apply_plan(persisted)
        self.refresh_saved_plan_picker(select_plan_id=persisted.plan_id)
        mark_saved(self)
        self.status.success(
            f"Restored Raid Plan backup: {persisted.name} • {occupied} occupied seat(s)."
        )

    def _open_saved_plan_raid_map(self) -> None:
        plan_id = self.saved_plan_combo.currentData()
        if not isinstance(plan_id, str) or not plan_id.strip():
            loaded = getattr(self, "_loaded_plan_snapshot", None)
            plan_id = str(getattr(loaded, "plan_id", "") or "").strip()
        if not plan_id:
            self.status.warning("Save or load a Raid Plan before opening its Raid Map.")
            return
        self.raidMapRequested.emit(plan_id)

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
            database_path=get_user_database_path(),
            raid_plans_path=get_user_database_path(),
            plan_id=plan_id,
            settings_path=get_settings_path(),
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
            database_path=get_user_database_path(),
            raid_plans_path=get_user_database_path(),
            settings_path=get_settings_path(),
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
                    + f" • {row.published_by or 'Unknown publisher'}"
                    + f" • {format_shared_timestamp(row.updated_at)}"
                    + f" • {row.provenance}"
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
                    f"Published by: {preview.published_by or 'Unknown'}\n"
                    f"Updated: {format_shared_timestamp(preview.updated_at)}\n"
                    f"Status: {preview.provenance}\n\n"
                    "This creates a separate local plan outline with shared seat/player/character/class/role, assignment, and lightweight build-summary data only. "
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
                database_path=get_user_database_path(),
                raid_plans_path=get_user_database_path(),
                settings_path=get_settings_path(),
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

    def _replacement_build_for_stale_member(self, member):
        """Return one exact saved Build that can replace a dead BuildId.

        Rebinding is intentionally conservative: player/character/build display
        identity must agree, and ambiguous matches remain unresolved/planned rather
        than letting a refresh silently choose somebody else's Build.
        """
        wanted_name = _clean(member.selected_build_name).casefold()
        wanted_player = _clean(member.gamertag).casefold()
        wanted_character = _clean(member.character_name).casefold()
        candidates = []
        for build in tuple(getattr(self, "saved_builds", ()) or ()):
            build_id = _clean(getattr(build, "BuildId", ""))
            if not build_id:
                continue
            if wanted_name and _clean(getattr(build, "BuildName", "")).casefold() != wanted_name:
                continue
            build_player = _clean(getattr(build, "Gamertag", "")).casefold()
            if wanted_player and build_player and build_player != wanted_player:
                # Allow exact Personnel aliases to resolve to the canonical player.
                match = self._personnel_match(member.gamertag)
                canonical = (
                    _clean(getattr(match, "PlayerName", "")).casefold()
                    if match is not None
                    else wanted_player
                )
                if build_player != canonical:
                    continue
            build_character = _clean(getattr(build, "Name", "")).casefold()
            if wanted_character and build_character and build_character != wanted_character:
                continue
            candidates.append(build)
        return candidates[0] if len(candidates) == 1 else None

    def _repair_loaded_snapshot_after_missing_builds(self) -> None:
        """Remove or rebind dead selected BuildIds before Raid Plan validation.

        A Comp/template refresh may legitimately replace a Build record while the
        saved Raid Plan still carries the old stable BuildId. That stale reference
        must not make Roles impossible to save or navigate away from. Preserve all
        planned gear/skills/assignments; only the dead stable reference is repaired.
        """
        loaded = getattr(self, "_loaded_plan_snapshot", None)
        if loaded is None:
            return
        catalog = self.build_service.canonical.catalog_service
        changed = False
        repaired_members = []
        for member in loaded.members:
            build_id = _clean(member.selected_build_id)
            if not build_id or catalog.get_build(build_id) is not None:
                repaired_members.append(member)
                continue

            replacement = self._replacement_build_for_stale_member(member)
            replacement_id = (
                _clean(getattr(replacement, "BuildId", ""))
                if replacement is not None
                else ""
            )
            repaired = member.with_selection(
                selected_build_id=replacement_id or None,
            )
            repaired_members.append(repaired)
            changed = changed or repaired != member

        if changed:
            self._loaded_plan_snapshot = replace(
                loaded,
                members=tuple(repaired_members),
            )

    def _repair_loaded_snapshot_after_player_merges(self) -> None:
        """Self-heal a loaded plan whose Personnel player was explicitly merged.

        A merge deletes only the donor Personnel row and records the donor name as
        an exact alias on the survivor. Older in-memory/saved plan snapshots may
        still carry the deleted roster_member_id/player_id. Resolve that exact
        alias to the survivor before the ordinary save merge so assignments,
        planned gear, build references, notes, and character state are preserved.
        """
        loaded = getattr(self, "_loaded_plan_snapshot", None)
        if loaded is None:
            return

        changed = False
        repaired_members = []
        catalog = self.build_service.canonical.catalog_service
        for member in loaded.members:
            roster_id = member.roster_member_id
            roster_row = (
                self.roster_service.get_member(int(roster_id))
                if roster_id is not None
                else None
            )
            player_exists = bool(
                not _clean(member.player_id)
                or catalog.get_player(_clean(member.player_id)) is not None
            )
            if roster_row is not None and player_exists:
                repaired_members.append(member)
                continue

            survivor = self._personnel_match(member.gamertag)
            if survivor is None or survivor.Id is None:
                repaired_members.append(member)
                continue

            repaired = member.with_selection(
                gamertag=_clean(survivor.PlayerName),
                roster_member_id=int(survivor.Id),
                player_id=_clean(survivor.CanonicalPlayerId) or None,
            )
            repaired_members.append(repaired)
            changed = changed or repaired != member

        if changed:
            self._loaded_plan_snapshot = replace(
                loaded,
                members=tuple(repaired_members),
            )

    def current_plan(self) -> RaidPlan:
        self._repair_loaded_snapshot_after_player_merges()
        self._repair_loaded_snapshot_after_missing_builds()
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
        self.saved_plan_combo.addItem("New Plan…", "__new_plan__")
        self.saved_plan_combo.addItem("No saved plan", None)
        selected_index = 1
        for plan in plans:
            trial = self._trial_display_for(plan)
            archived = " • Archived" if _clean(plan.status).casefold() == "archived" else ""
            label = f"{plan.name} • {trial}{archived}"
            self.saved_plan_combo.addItem(label, plan.plan_id)
            if wanted and plan.plan_id.casefold() == wanted:
                selected_index = self.saved_plan_combo.count() - 1
        self.saved_plan_combo.setCurrentIndex(selected_index)
        self.saved_plan_combo.blockSignals(False)
        self._saved_plan_selection_changed(self.saved_plan_combo.currentIndex())
        self._refresh_action_availability()

    def _refresh_action_availability(self) -> None:
        plan_id = self.saved_plan_combo.currentData() if hasattr(self, "saved_plan_combo") else None
        saved = isinstance(plan_id, str) and bool(plan_id.strip()) and plan_id != "__new_plan__"
        set_enabled_reason(
            self.load_plan_button,
            saved,
            "Choose a saved Raid Plan first.",
        )
        set_enabled_reason(
            self.delete_plan_button,
            saved,
            "Choose a saved Raid Plan first.",
        )
        set_enabled_reason(
            self.archive_plan_button,
            saved,
            "Choose a saved Raid Plan first.",
        )
        selected_plan = (
            self.plan_repository.get(str(plan_id))
            if saved
            else None
        )
        archived = bool(
            selected_plan is not None
            and _clean(selected_plan.status).casefold() == "archived"
        )
        self.archive_plan_button.setText("Restore" if archived else "Archive")
        set_enabled_reason(
            self.open_raid_map_button,
            saved,
            "Save or load a Raid Plan first.",
        )
        set_enabled_reason(
            self.publish_plan_finch_button,
            saved and not self.has_pending_changes(),
            "Save Raid Plan changes before publishing to Finch."
            if saved else "Save or load a Raid Plan first.",
        )

    @staticmethod
    def _trial_display_for(plan: RaidPlan) -> str:
        wanted = plan.trial_id.casefold()
        return next((name for name in COMP_MAKER_TRIALS if _slug(name) == wanted), plan.trial_id)

    def _active_team_name(self) -> str:
        team_combo = getattr(self, "team_combo", None)
        if isinstance(team_combo, QComboBox):
            return _clean(team_combo.currentData())
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
            # Save only the plan. Personnel/Team promotion is an explicit user
            # action through Save Player to Personnel and must never be a hidden
            # side effect of saving Assignments or a shared Finch copy.
            plan = self.current_plan()
            checkpoint = self._safety_snapshots.create(
                f"save-raid-plan-{plan.plan_id}"
            )
            if checkpoint is None and get_user_database_path().is_file():
                raise RaidPlanRepositoryError(
                    "could not create the pre-save database checkpoint"
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
        except Exception as exc:
            mark_save_failed(self, str(exc))
            self.status.error(f"Could not save Raid Plan: {exc}")
            return None

        self._loaded_plan_snapshot = persisted
        self._navigation_baseline_plan = persisted
        self._discard_recovery_draft(persisted.plan_id)
        mark_saved(self)

        # A successful Save is a persistence checkpoint, not a page reload.
        # Keep the live assignment controls intact. The picker refresh is cosmetic
        # and must never turn a durable save into a crash.
        try:
            self.refresh_saved_plan_picker(select_plan_id=persisted.plan_id)
        except Exception as exc:
            self.status.warning(
                f"Raid Plan saved, but the saved-plan picker could not refresh: {exc}"
            )

        characters = sum(1 for member in persisted.members if member.character_name)
        roles = sum(1 for member in persisted.members if member.role)
        planned = sum(
            1
            for member in persisted.members
            if member.selected_build_name or member.planned_gear_sets
        )
        self.status.success(
            f"Saved Raid Plan: {persisted.name} • "
            f"{len(persisted.members)} player(s) • {characters} character(s) • "
            f"{roles} role(s) • {planned} planned build(s)"
        )
        return persisted

    def _open_assignments(self, *_args) -> None:
        """Open Assignments without silently committing visible Raid Plan edits."""
        if self.has_pending_changes() and not confirm_unsaved_changes(
            self,
            self,
            action_text="open Assignments",
        ):
            return
        persisted = getattr(self, "_loaded_plan_snapshot", None)
        if persisted is None:
            self.status.warning("Save the Raid Plan before opening Assignments.")
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
        loaded = getattr(self, "_loaded_plan_snapshot", None)
        if (
            loaded is not None
            and loaded.plan_id.casefold() != plan_id.casefold()
            and not confirm_unsaved_changes(
                self,
                self,
                action_text="load another Raid Plan",
            )
        ):
            self.refresh_saved_plan_picker(select_plan_id=loaded.plan_id)
            return
        try:
            saved_plan = self.plan_repository.get(plan_id)
            plan = (
                self._offer_recovery_draft(saved_plan)
                if saved_plan is not None
                else None
            )
        except RaidPlanRepositoryError as exc:
            if str(exc) != "Raid Plan load cancelled.":
                self.status.error(f"Could not load Raid Plan: {exc}")
            return
        if plan is None:
            self.status.warning("That saved Raid Plan no longer exists.")
            self.refresh_saved_plan_picker()
            return
        self.apply_plan(plan)
        if saved_plan is not None and plan != saved_plan:
            # A recovered draft is reviewable unsaved state, never the new clean
            # authority. Keep its full snapshot for merge/current-plan behavior,
            # but compare navigation/save safety against the durable saved plan.
            self._navigation_baseline_plan = saved_plan
            self.status.warning(
                f"Recovered unsaved Raid Plan draft: {plan.name}. "
                "The last saved version remains authoritative until you explicitly Save."
            )
        else:
            self.status.success(f"Loaded Raid Plan: {plan.name}")

    def toggle_archive_selected_plan(self) -> None:
        plan_id = self.saved_plan_combo.currentData()
        if not isinstance(plan_id, str) or not plan_id.strip():
            self.status.warning("Choose a saved Raid Plan to archive or restore.")
            return
        if self.has_pending_changes() and not confirm_unsaved_changes(
            self,
            self,
            action_text="archive or restore this Raid Plan",
        ):
            return

        plan = self.plan_repository.get(plan_id)
        if plan is None:
            self.status.warning("That saved Raid Plan no longer exists.")
            self.refresh_saved_plan_picker()
            return

        restoring = _clean(plan.status).casefold() == "archived"
        updated = replace(
            plan,
            status="Active" if restoring else "Archived",
        )
        try:
            self.plan_repository.save(updated)
        except RaidPlanRepositoryError as exc:
            self.status.error(f"Could not update Raid Plan archive state: {exc}")
            return

        self._loaded_plan_snapshot = updated
        self._navigation_baseline_plan = updated
        self.refresh_saved_plan_picker(select_plan_id=updated.plan_id)
        self.apply_plan(updated)
        mark_saved(self)
        if restoring:
            self.status.success(f"Restored Raid Plan: {updated.name}")
        else:
            self.status.info(
                f"Archived Raid Plan: {updated.name}. It was not deleted and can be restored."
            )

    def delete_selected_plan(self) -> None:
        plan_id = self.saved_plan_combo.currentData()
        if not isinstance(plan_id, str) or not plan_id.strip():
            self.status.warning("Choose a saved Raid Plan to delete.")
            return
        plan = self.plan_repository.get(plan_id)
        label = plan.name if plan is not None else plan_id
        if not confirm_destructive_action(
            self,
            title="Delete Raid Plan",
            object_label=f'Delete Raid Plan "{label}"?',
            impact=(
                "This removes the saved Raid Plan and its plan-specific decisions. "
                "Personnel, Teams, Characters, and saved Builds are kept. "
                "A recoverable database snapshot is created first."
            ),
            confirm_text="Delete Raid Plan",
        ):
            return
        self._safety_snapshots.create(f"delete-raid-plan-{plan_id}")
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
        if not confirm_unsaved_changes(
            self,
            self,
            action_text="start a new Raid Plan",
        ):
            return
        self._loaded_plan_snapshot = None
        super().clear_plan()
        self._set_plan_name_visible(True)
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
            self._set_plan_name_visible(False)

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

                            # Exact canonical BuildId outranks display-name filters.
                            # After player merges/import cleanup the build can still
                            # be valid even when its legacy Gamertag/Character text
                            # differs from the chair. Make that exact build visible
                            # rather than silently dropping the Roles selection.
                            if not matched:
                                exact_saved_index = next(
                                    (
                                        index
                                        for index, saved in enumerate(self.saved_builds)
                                        if _clean(getattr(saved, "BuildId", "")).casefold()
                                        == wanted_id
                                    ),
                                    None,
                                )
                                if exact_saved_index is not None:
                                    saved = self.saved_builds[exact_saved_index]
                                    build_combo.addItem(
                                        self._build_display(saved),
                                        exact_saved_index,
                                    )
                                    build_combo.setCurrentIndex(build_combo.count() - 1)
                                    matched = True
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
                            and (
                                member.planned_gear_sets
                                or member.planned_skills
                                or member.planned_mundus
                                or member.candidate_id
                                or member.build_source_kind
                                or member.selected_build_name
                            )
                        ):
                            planned_sets = " + ".join(member.planned_gear_sets[:2])
                            planned_name = (
                                member.selected_build_name
                                or member.build_source_name
                                or "Comp Maker package"
                            )
                            planned_label = (
                                f"Planned • {planned_sets}"
                                if planned_sets
                                else f"Planned • {planned_name}"
                            )
                            build_combo.addItem(
                                planned_label,
                                f"planned:{member.seat_id}",
                            )
                            build_combo.setItemData(
                                build_combo.count() - 1,
                                " • ".join(member.planned_gear_sets)
                                or member.selected_build_name
                                or member.build_source_name
                                or "Comp Maker package",
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
