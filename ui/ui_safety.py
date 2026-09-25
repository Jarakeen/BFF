from __future__ import annotations

"""Shared UI failsafes for editing, replacement, and destructive actions."""

from datetime import datetime
from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton, QWidget


def _page_title(page) -> str:
    header = getattr(page, "header", None)
    title = getattr(header, "title", None)
    if title is not None and hasattr(title, "text"):
        value = str(title.text() or "").strip()
        if value:
            return value.title()
    return page.__class__.__name__.replace("Page", "").replace("_", " ")


def confirm_unsaved_changes(
    parent: QWidget,
    page,
    *,
    action_text: str = "leave this page",
) -> bool:
    has_pending = getattr(page, "has_pending_changes", None)
    if not callable(has_pending):
        return True
    try:
        if not bool(has_pending()):
            return True
    except Exception as exc:
        mark_save_failed(
            page,
            f"Could not verify whether this page has unsaved changes: {exc}",
        )

    box = QMessageBox(parent)
    box.setWindowTitle("Unsaved Changes")
    box.setText(f"You have unsaved changes to {_page_title(page)}.")
    box.setInformativeText(
        f"Save them before you {action_text}, discard them, or stay here."
    )
    box.setStandardButtons(
        QMessageBox.StandardButton.Save
        | QMessageBox.StandardButton.Discard
        | QMessageBox.StandardButton.Cancel
    )
    box.setDefaultButton(QMessageBox.StandardButton.Save)
    answer = box.exec()

    if answer == QMessageBox.StandardButton.Save:
        save = getattr(page, "save_pending_changes", None)
        if not callable(save):
            mark_save_failed(page, "This page does not expose a safe save action.")
            return False
        try:
            mark_saving(page)
            saved = bool(save())
        except Exception as exc:
            mark_save_failed(page, str(exc))
            return False
        if saved:
            mark_saved(page)
            return True
        mark_save_failed(page, "The page is still reporting unsaved changes after Save.")
        return False

    if answer == QMessageBox.StandardButton.Discard:
        discard = getattr(page, "discard_pending_changes", None)
        if not callable(discard):
            mark_save_failed(
                page,
                "This page cannot safely discard its current edits.",
            )
            return False
        try:
            discarded = discard()
        except Exception as exc:
            mark_save_failed(page, str(exc))
            return False
        if discarded is False:
            mark_save_failed(page, "The page refused to discard its current edits.")
            return False
        mark_saved(page, "Discarded")
        return True

    return False


def confirm_destructive_action(
    parent: QWidget,
    *,
    title: str,
    object_label: str,
    impact: str,
    confirm_text: str = "Delete",
) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setText(object_label)
    box.setInformativeText(impact)
    cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    confirm = box.addButton(confirm_text, QMessageBox.ButtonRole.DestructiveRole)
    box.setDefaultButton(cancel)
    box.exec()
    return box.clickedButton() is confirm


def confirm_replacement(
    parent: QWidget,
    *,
    title: str,
    object_label: str,
    impact: str,
    confirm_text: str = "Replace",
) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setText(object_label)
    box.setInformativeText(impact)
    cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    confirm = box.addButton(confirm_text, QMessageBox.ButtonRole.DestructiveRole)
    box.setDefaultButton(cancel)
    box.exec()
    return box.clickedButton() is confirm


def set_enabled_reason(widget: QWidget, enabled: bool, reason: str = "") -> None:
    widget.setEnabled(bool(enabled))
    if enabled:
        if str(widget.toolTip() or "").startswith("Unavailable: "):
            widget.setToolTip("")
        return
    if reason:
        widget.setToolTip(f"Unavailable: {reason}")


def attach_save_state_badge(page, *, interval_ms: int = 1000) -> QLabel | None:
    existing = getattr(page, "_ui_safety_badge", None)
    if isinstance(existing, QLabel):
        return existing

    header = getattr(page, "header", None)
    add_context = getattr(header, "add_context_widget", None)
    if not callable(add_context):
        return None

    badge = QLabel("Saved")
    badge.setProperty("uiSafetyState", "saved")
    badge.setToolTip("This page has no unsaved changes.")
    add_context(badge)
    page._ui_safety_badge = badge

    timer = QTimer(page)
    timer.setInterval(max(150, int(interval_ms)))

    def refresh() -> None:
        # Some pages assemble their entire plan and resolve database identities
        # in has_pending_changes(). Hidden pages have no badge to update.
        if not page.isVisible():
            return
        failed = str(getattr(page, "_ui_safety_save_error", "") or "").strip()
        if failed:
            label, state, tip = "Save Failed", "failed", failed
        else:
            pending = getattr(page, "has_pending_changes", None)
            dirty = False
            if callable(pending):
                try:
                    dirty = bool(pending())
                except Exception:
                    dirty = True
            if dirty:
                label, state, tip = "Unsaved", "dirty", "This page has unsaved changes."
            else:
                saved_at = str(getattr(page, "_ui_safety_saved_at", "") or "").strip()
                suffix = f" · {saved_at}" if saved_at else ""
                label, state, tip = f"Saved{suffix}", "saved", "This page has no unsaved changes."
        if badge.text() != label:
            badge.setText(label)
        if badge.toolTip() != tip:
            badge.setToolTip(tip)
        if badge.property("uiSafetyState") != state:
            badge.setProperty("uiSafetyState", state)
            badge.style().unpolish(badge)
            badge.style().polish(badge)

    timer.timeout.connect(refresh)
    timer.start()
    page._ui_safety_badge_timer = timer
    refresh()
    return badge


def mark_saving(page) -> None:
    page._ui_safety_save_error = ""
    badge = getattr(page, "_ui_safety_badge", None)
    if isinstance(badge, QLabel):
        badge.setText("Saving…")
        badge.setProperty("uiSafetyState", "saving")
        badge.setToolTip("Saving changes.")
        badge.style().unpolish(badge)
        badge.style().polish(badge)


def mark_saved(page, label: str = "Saved") -> None:
    page._ui_safety_save_error = ""
    page._ui_safety_saved_at = datetime.now().strftime("%I:%M %p").lstrip("0")
    badge = getattr(page, "_ui_safety_badge", None)
    if isinstance(badge, QLabel):
        badge.setText(f"{label} · {page._ui_safety_saved_at}")
        badge.setProperty("uiSafetyState", "saved")


def mark_save_failed(page, message: str) -> None:
    page._ui_safety_save_error = str(message or "Save failed.")
    badge = getattr(page, "_ui_safety_badge", None)
    if isinstance(badge, QLabel):
        badge.setText("Save Failed")
        badge.setProperty("uiSafetyState", "failed")
        badge.setToolTip(page._ui_safety_save_error)


def wire_save_button(
    page,
    button: QPushButton,
    save: Callable[[], object],
) -> None:
    def run() -> None:
        try:
            mark_saving(page)
            result = save()
        except Exception as exc:
            mark_save_failed(page, str(exc))
            status = getattr(page, "status", None)
            if status is not None and callable(getattr(status, "error", None)):
                status.error(f"Save failed: {exc}")
            return
        if result is False or result is None:
            if callable(getattr(page, "has_pending_changes", None)) and page.has_pending_changes():
                mark_save_failed(page, "The save did not complete.")
            return
        mark_saved(page)

    button.clicked.connect(run)


__all__ = [
    "attach_save_state_badge",
    "confirm_destructive_action",
    "confirm_replacement",
    "confirm_unsaved_changes",
    "mark_save_failed",
    "mark_saved",
    "mark_saving",
    "set_enabled_reason",
    "wire_save_button",
]
