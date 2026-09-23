from __future__ import annotations

"""Application-wide UI safety policy for editable FoundryDock workspaces.

This module installs one shared safety contract across the remaining legacy/page-specific
editors: explicit dirty state, Save/Discard/Stay navigation, guarded context switches,
recoverable Raid Map drafts, destructive confirmations, and disabled impossible actions.

It deliberately does not auto-save committed user data. Drafts and safety snapshots remain
separate from the canonical stores.
"""

import json
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from services.ui_draft_recovery_service import UiDraftRecoveryService
from ui.ui_safety import (
    confirm_destructive_action,
    confirm_unsaved_changes,
    mark_saved,
    mark_save_failed,
    mark_saving,
    set_enabled_reason,
)


_INSTALLED = False


def _model_signature(model) -> dict:
    if model is None:
        return {}
    to_dict = getattr(model, "to_dict", None)
    if callable(to_dict):
        return deepcopy(to_dict())
    return deepcopy(getattr(model, "__dict__", {}) or {})


def _record_signature(page) -> dict:
    record = getattr(page, "record", None)
    if record is None:
        return {}
    signature = _model_signature(record.model)
    aliases = getattr(record, "former_gamertag_values", None)
    if callable(aliases):
        signature["_former_gamertags"] = tuple(aliases())
    return signature


def _capture_roster_baseline(page) -> None:
    page._ui_safety_roster_baseline = _record_signature(page)
    page._ui_safety_roster_member_id = getattr(getattr(page, "record", None), "member_id", None)


def _roster_has_pending(page) -> bool:
    baseline = getattr(page, "_ui_safety_roster_baseline", None)
    if baseline is None:
        _capture_roster_baseline(page)
        return False
    return _record_signature(page) != baseline


def _select_roster_member_without_signal(page, member_id) -> None:
    if member_id is None:
        return
    for name in ("player_detail_table", "table"):
        table = getattr(page, name, None)
        selector = getattr(table, "select_member_id", None)
        if not callable(selector):
            continue
        table.blockSignals(True)
        try:
            selector(int(member_id))
        finally:
            table.blockSignals(False)


def _roster_save_pending(page) -> bool:
    if not _roster_has_pending(page):
        return True
    mark_saving(page)
    save = getattr(page, "_save_player", None)
    if not callable(save):
        save = getattr(page, "save_member", None)
    if not callable(save):
        mark_save_failed(page, "This Roster surface does not expose a save action.")
        return False
    save()
    if _roster_has_pending(page):
        mark_save_failed(page, "The player record is still unsaved.")
        return False
    mark_saved(page)
    return True


def _roster_discard_pending(page) -> bool:
    member_id = getattr(page, "_ui_safety_roster_member_id", None)
    if member_id is None:
        record = getattr(page, "record", None)
        if record is not None:
            record.clear()
    else:
        member = page.roster_service.get_member(int(member_id))
        if member is not None:
            page.record.load(member)
            identity = getattr(page, "identity_service", None)
            if identity is not None and hasattr(page.record, "set_former_gamertags"):
                try:
                    aliases = identity.aliases_for_member(int(member_id))
                    page.record.set_former_gamertags(
                        tuple(alias.alias for alias in aliases)
                    )
                except Exception:
                    pass
    _capture_roster_baseline(page)
    mark_saved(page, "Discarded")
    return True


def _install_roster_safety(cls) -> None:
    if getattr(cls, "_ui_safety_installed", False):
        return

    original_init = cls.__init__
    original_load = getattr(cls, "load_member", None)
    original_new = getattr(cls, "_new_player", None) or getattr(cls, "new_member", None)
    original_save = getattr(cls, "_save_player", None) or getattr(cls, "save_member", None)

    def init_with_safety(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _capture_roster_baseline(self)

    cls.__init__ = init_with_safety
    cls.has_pending_changes = lambda self: _roster_has_pending(self)
    cls.save_pending_changes = lambda self: _roster_save_pending(self)
    cls.discard_pending_changes = lambda self: _roster_discard_pending(self)

    if callable(original_load):
        def load_member_with_guard(self, member_id):
            current_id = getattr(getattr(self, "record", None), "member_id", None)
            if (
                current_id is not None
                and int(current_id) != int(member_id)
                and _roster_has_pending(self)
                and not confirm_unsaved_changes(
                    self,
                    self,
                    action_text="open another player",
                )
            ):
                _select_roster_member_without_signal(self, current_id)
                return
            original_load(self, member_id)
            _capture_roster_baseline(self)

        cls.load_member = load_member_with_guard

    if callable(original_new):
        method_name = "_new_player" if hasattr(cls, "_new_player") else "new_member"

        def new_with_guard(self, *args, **kwargs):
            if _roster_has_pending(self) and not confirm_unsaved_changes(
                self,
                self,
                action_text="start a new player",
            ):
                return
            result = original_new(self, *args, **kwargs)
            _capture_roster_baseline(self)
            return result

        setattr(cls, method_name, new_with_guard)

    if callable(original_save):
        method_name = "_save_player" if hasattr(cls, "_save_player") else "save_member"

        def save_with_state(self, *args, **kwargs):
            mark_saving(self)
            result = original_save(self, *args, **kwargs)
            _capture_roster_baseline(self)
            if _roster_has_pending(self):
                mark_save_failed(self, "The player record is still unsaved.")
            else:
                mark_saved(self)
            return result

        setattr(cls, method_name, save_with_state)

    cls._ui_safety_installed = True


def _build_editor_changed(page) -> bool:
    editor = getattr(page, "_build_editor", None)
    index = getattr(page, "_build_editor_index", None)
    members = getattr(getattr(page, "roster", None), "Members", ())
    if editor is not None and isinstance(index, int) and 0 <= index < len(members):
        try:
            current = deepcopy(editor.model)
            original = members[index]
            preserve = getattr(page, "_preserve_non_editor_build_state", None)
            if callable(preserve):
                current = preserve(original, current)
            if hasattr(current, "to_dict") and hasattr(original, "to_dict"):
                if current.to_dict() != original.to_dict():
                    return True
        except Exception:
            return True

    panel = getattr(page, "_progression_panel", None)
    character_id = str(getattr(page, "_progression_character_id", "") or "").strip()
    if panel is not None and character_id:
        try:
            character = page.build_service.canonical.catalog_service.get_character(character_id) or {}
            if tuple(panel.owned_skill_lines) != tuple(character.get("owned_skill_lines", ()) or ()):
                return True
            if dict(panel.passive_ranks) != dict(character.get("passive_ranks", {}) or {}):
                return True
            if dict(panel.passive_cp_points) != dict(character.get("passive_cp_points", {}) or {}):
                return True
        except Exception:
            return True

    scribed_index = getattr(page, "_scribed_index", None)
    choices = getattr(page, "scribed_skill_choices", None)
    if choices is not None and isinstance(scribed_index, int) and 0 <= scribed_index < len(members):
        try:
            selected = tuple(
                choices.item(i).text().strip()
                for i in range(choices.count())
                if choices.item(i).checkState().value == 2
            )
            saved = tuple(
                str(name).strip()
                for name in getattr(members[scribed_index], "ScribedSkills", ())
                if str(name).strip()
            )
            if selected != saved:
                return True
        except Exception:
            return True

    return False


def _builds_save_pending(page) -> bool:
    if not _build_editor_changed(page):
        return True
    mark_saving(page)
    try:
        editor = getattr(page, "_build_editor", None)
        index = getattr(page, "_build_editor_index", None)
        members = getattr(getattr(page, "roster", None), "Members", ())
        if editor is not None and isinstance(index, int) and 0 <= index < len(members):
            save_edit = getattr(page, "_save_edit_tab", None)
            if callable(save_edit):
                save_edit()

        if _build_editor_changed(page):
            save_progression = getattr(page, "_save_progression_tab", None)
            if callable(save_progression) and getattr(page, "_progression_panel", None) is not None:
                save_progression()

        if _build_editor_changed(page):
            save_scribed = getattr(page, "_save_scribed_tab", None)
            if callable(save_scribed) and getattr(page, "_scribed_index", None) is not None:
                save_scribed()
    except Exception as exc:
        mark_save_failed(page, str(exc))
        return False

    if _build_editor_changed(page):
        mark_save_failed(page, "Some Build changes are still unsaved.")
        return False
    mark_saved(page)
    return True


def _builds_discard_pending(page) -> bool:
    try:
        cancel = getattr(page, "_cancel_edit_tab", None)
        if callable(cancel) and getattr(page, "_build_editor", None) is not None:
            cancel()
        progression_index = getattr(page, "_progression_index", None)
        load_progression = getattr(page, "_load_progression_tab", None)
        if callable(load_progression) and isinstance(progression_index, int):
            page._progression_panel = None
            load_progression(progression_index)
        scribed_index = getattr(page, "_scribed_index", None)
        load_scribed = getattr(page, "_load_scribed_tab", None)
        if callable(load_scribed) and isinstance(scribed_index, int):
            page._scribed_index = None
            load_scribed(scribed_index)
    except Exception as exc:
        mark_save_failed(page, str(exc))
        return False
    mark_saved(page, "Discarded")
    return True


def _install_builds_safety(cls) -> None:
    if getattr(cls, "_ui_safety_installed", False):
        return
    cls.has_pending_changes = lambda self: _build_editor_changed(self)
    cls.save_pending_changes = lambda self: _builds_save_pending(self)
    cls.discard_pending_changes = lambda self: _builds_discard_pending(self)

    original_selector = getattr(cls, "_build_selector_changed", None)
    if callable(original_selector):
        def selector_with_guard(self, combo, tab_index):
            target = combo.currentData()
            current = {
                1: getattr(self, "_build_editor_index", None),
                2: getattr(self, "_progression_index", None),
                3: getattr(self, "_scribed_index", None),
            }.get(tab_index)
            try:
                target_index = int(target)
            except (TypeError, ValueError):
                target_index = None
            if (
                current is not None
                and target_index is not None
                and int(current) != target_index
                and _build_editor_changed(self)
                and not confirm_unsaved_changes(
                    self,
                    self,
                    action_text="open another build",
                )
            ):
                combo.blockSignals(True)
                try:
                    old = combo.findData(current)
                    combo.setCurrentIndex(old if old >= 0 else -1)
                finally:
                    combo.blockSignals(False)
                return
            return original_selector(self, combo, tab_index)

        cls._build_selector_changed = selector_with_guard

    cls._ui_safety_installed = True


def _board_payload(board) -> dict:
    tokens = board._token_items()
    payload = {
        "version": 2,
        "boss_count": 2 if board.boss_mode.currentIndex() == 1 else 1,
        "items": [item.to_dict() for item in tokens if item.kind != "mini_boss"],
        "mini_bosses": [item.to_dict() for item in tokens if item.kind == "mini_boss"],
        "zones": [zone.to_dict() for zone in board._zone_items()],
        "raid_plan_id": str(getattr(board, "raid_plan_id", "") or "").strip(),
        "reference_points_locked": bool(
            getattr(board, "_reference_points_locked", False)
        ),
    }
    return payload


def _apply_board_payload(board, payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    # Reuse the canonical loader rather than maintaining a second map parser.
    draft_root = UiDraftRecoveryService().root
    draft_root.mkdir(parents=True, exist_ok=True)
    path = draft_root / ".raid-map-restore.json"
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return bool(board.load_state_from(path))
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def _capture_board_baseline(page) -> None:
    board = getattr(page, "encounter_board", None)
    if board is None:
        return
    page._ui_safety_map_baseline = _board_payload(board)


def _map_has_pending(page) -> bool:
    board = getattr(page, "encounter_board", None)
    baseline = getattr(page, "_ui_safety_map_baseline", None)
    if board is None or baseline is None:
        return False
    try:
        return _board_payload(board) != baseline
    except Exception:
        return True


def _map_draft_key(page) -> str:
    plan = str(getattr(getattr(page, "raid_plan_combo", None), "currentData", lambda: "")() or "").strip()
    boss = str(getattr(getattr(page, "boss_combo", None), "currentData", lambda: "")() or "").strip()
    return f"raid-map-{plan or 'template'}-{boss or 'unscoped'}"


def _save_map_draft(page) -> None:
    if not _map_has_pending(page):
        return
    try:
        UiDraftRecoveryService().save(
            _map_draft_key(page),
            {"kind": "raid_map", "map": _board_payload(page.encounter_board)},
        )
    except Exception:
        pass


def _discard_map_draft(page) -> None:
    UiDraftRecoveryService().discard(_map_draft_key(page))


def _map_save_pending(page) -> bool:
    board = getattr(page, "encounter_board", None)
    if board is None:
        return True
    try:
        mark_saving(page)
        board.save_state()
        _capture_board_baseline(page)
        _discard_map_draft(page)
        mark_saved(page)
        status = getattr(page, "status", None)
        if status is not None:
            status.success("Raid Map layout saved.")
        return True
    except Exception as exc:
        mark_save_failed(page, str(exc))
        return False


def _map_discard_pending(page) -> bool:
    baseline = getattr(page, "_ui_safety_map_baseline", None)
    if baseline is None:
        return True
    try:
        if not _apply_board_payload(page.encounter_board, baseline):
            raise RuntimeError("The saved Raid Map layout could not be restored.")
        _discard_map_draft(page)
        mark_saved(page, "Discarded")
        return True
    except Exception as exc:
        mark_save_failed(page, str(exc))
        return False


def _offer_map_recovery(page) -> None:
    service = UiDraftRecoveryService()
    draft = service.load(_map_draft_key(page))
    payload = draft.get("payload") if isinstance(draft, dict) else None
    raw = payload.get("map") if isinstance(payload, dict) else None
    if not isinstance(raw, dict):
        return
    baseline = getattr(page, "_ui_safety_map_baseline", None)
    if raw == baseline:
        service.discard(_map_draft_key(page))
        return

    box = QMessageBox(page)
    box.setWindowTitle("Recovered Raid Map Draft")
    box.setText("FoundryDock recovered unsaved Raid Map changes.")
    box.setInformativeText(
        "Restore the draft for review, or continue with the last saved layout."
    )
    restore = box.addButton("Restore Draft", QMessageBox.ButtonRole.AcceptRole)
    saved = box.addButton("Use Saved Layout", QMessageBox.ButtonRole.DestructiveRole)
    box.setDefaultButton(restore)
    box.exec()
    if box.clickedButton() is restore:
        if _apply_board_payload(page.encounter_board, raw):
            status = getattr(page, "status", None)
            if status is not None:
                status.warning("Recovered unsaved Raid Map draft. Review and Save Layout.")
    elif box.clickedButton() is saved:
        service.discard(_map_draft_key(page))


def _refresh_map_actions(page) -> None:
    if not hasattr(page, "save_raid_map_to_plan_button"):
        return
    plan_id = str(page.raid_plan_combo.currentData() or "").strip() if hasattr(page, "raid_plan_combo") else ""
    boss_id = str(page.boss_combo.currentData() or "").strip() if hasattr(page, "boss_combo") else ""
    valid_plan = bool(plan_id and page.raid_plan_repository.get(plan_id) is not None)
    valid_boss = bool(boss_id)
    set_enabled_reason(
        page.save_raid_map_to_plan_button,
        valid_plan and valid_boss,
        "Select a saved Raid Plan and boss first.",
    )
    set_enabled_reason(
        page.save_raid_map_to_finch_button,
        valid_plan and valid_boss,
        "Select a saved Raid Plan and boss first.",
    )
    set_enabled_reason(
        page.remove_raid_map_from_finch_button,
        valid_plan and valid_boss,
        "Select a saved Raid Plan and boss first.",
    )
    attach = getattr(page, "attach_raid_map_button", None)
    if attach is not None:
        set_enabled_reason(
            attach,
            valid_boss,
            "Select a boss first.",
        )


def _install_encounters_safety(cls) -> None:
    if getattr(cls, "_ui_safety_installed", False):
        return

    original_init = cls.__init__
    original_boss_changed = cls._boss_changed
    original_context_changed = getattr(cls, "_raid_plan_context_changed", None)
    original_remove_finch = getattr(cls, "_remove_raid_map_from_finch", None)

    def init_with_safety(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _capture_board_baseline(self)
        self._ui_safety_boss_index = self.boss_combo.currentIndex() if hasattr(self, "boss_combo") else -1
        timer = QTimer(self)
        timer.setInterval(2000)
        timer.timeout.connect(lambda: _save_map_draft(self))
        timer.start()
        self._ui_safety_map_draft_timer = timer
        if hasattr(self, "raid_plan_combo"):
            self.raid_plan_combo.currentIndexChanged.connect(lambda *_: _refresh_map_actions(self))
        if hasattr(self, "boss_combo"):
            self.boss_combo.currentIndexChanged.connect(lambda *_: _refresh_map_actions(self))
        QTimer.singleShot(0, lambda: (_refresh_map_actions(self), _offer_map_recovery(self)))

    cls.__init__ = init_with_safety
    cls.has_pending_changes = lambda self: _map_has_pending(self)
    cls.save_pending_changes = lambda self: _map_save_pending(self)
    cls.discard_pending_changes = lambda self: _map_discard_pending(self)

    def boss_changed_with_guard(self, index):
        previous = getattr(self, "_ui_safety_boss_index", -1)
        if (
            previous >= 0
            and index != previous
            and _map_has_pending(self)
            and not confirm_unsaved_changes(
                self,
                self,
                action_text="switch bosses",
            )
        ):
            self.boss_combo.blockSignals(True)
            try:
                self.boss_combo.setCurrentIndex(previous)
            finally:
                self.boss_combo.blockSignals(False)
            return
        result = original_boss_changed(self, index)
        self._ui_safety_boss_index = index
        _capture_board_baseline(self)
        _refresh_map_actions(self)
        QTimer.singleShot(0, lambda: _offer_map_recovery(self))
        return result

    cls._boss_changed = boss_changed_with_guard

    if callable(original_context_changed):
        def context_changed_with_guard(self, *args):
            current = str(getattr(self.encounter_board, "raid_plan_id", "") or "").strip()
            target = str(self.raid_plan_combo.currentData() or "").strip()
            if (
                current != target
                and _map_has_pending(self)
                and not confirm_unsaved_changes(
                    self,
                    self,
                    action_text="switch Raid Plans",
                )
            ):
                self.raid_plan_combo.blockSignals(True)
                try:
                    index = self.raid_plan_combo.findData(current)
                    if index >= 0:
                        self.raid_plan_combo.setCurrentIndex(index)
                finally:
                    self.raid_plan_combo.blockSignals(False)
                return
            result = original_context_changed(self, *args)
            _capture_board_baseline(self)
            _refresh_map_actions(self)
            QTimer.singleShot(0, lambda: _offer_map_recovery(self))
            return result

        cls._raid_plan_context_changed = context_changed_with_guard

    if callable(original_remove_finch):
        def remove_finch_with_confirmation(self, *args, **kwargs):
            plan_id = str(self.raid_plan_combo.currentData() or "").strip()
            encounter_name = str(self.boss_combo.currentText() or "").strip() or "this encounter"
            if not plan_id:
                return original_remove_finch(self, *args, **kwargs)
            if not confirm_destructive_action(
                self,
                title="Remove Raid Map from Finch",
                object_label=f'Remove the published Raid Map for "{encounter_name}"?',
                impact=(
                    "This removes only the Finch preview link for this Raid Plan encounter. "
                    "The local editable map, boss template, and Raid Plan remain intact."
                ),
                confirm_text="Remove from Finch",
            ):
                return
            return original_remove_finch(self, *args, **kwargs)

        cls._remove_raid_map_from_finch = remove_finch_with_confirmation

    cls._ui_safety_installed = True


def _install_board_delete_confirmation(board_cls) -> None:
    if getattr(board_cls, "_ui_safety_delete_installed", False):
        return
    original_delete = board_cls.delete_selected

    def delete_with_confirmation(self):
        selected = [
            item
            for item in self.scene.selectedItems()
            if getattr(item, "kind", "") != "boss"
        ]
        if not selected:
            return
        labels = [
            str(getattr(item, "label", "") or getattr(item, "kind", "") or "map item")
            for item in selected
        ]
        preview = ", ".join(labels[:3])
        if len(labels) > 3:
            preview += f" + {len(labels) - 3} more"
        if not confirm_destructive_action(
            self,
            title="Delete Raid Map Item",
            object_label=f"Delete {len(selected)} selected map item(s)?",
            impact=f"{preview}. This changes only the editable Raid Map until you save it.",
            confirm_text="Delete Selected",
        ):
            return
        return original_delete(self)

    board_cls.delete_selected = delete_with_confirmation
    board_cls._ui_safety_delete_installed = True


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.roster_page import RosterPage as BaseRosterPage
    from ui.raid_roster_workspace_page import RaidRosterWorkspacePage
    from ui.builds_page import BuildsPage
    from ui.encounters_page import EncountersPage
    from ui.components.encounter_board import EncounterBoard

    _install_roster_safety(BaseRosterPage)
    _install_roster_safety(RaidRosterWorkspacePage)
    _install_builds_safety(BuildsPage)
    _install_encounters_safety(EncountersPage)
    _install_board_delete_confirmation(EncounterBoard)

    _INSTALLED = True


__all__ = ["install"]
