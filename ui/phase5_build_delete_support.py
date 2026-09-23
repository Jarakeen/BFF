from __future__ import annotations

"""Safe build deletion helpers for the Builds page.

Deletion is composed onto the concrete themed BuildsPage instance instead of replacing
BuildsPage._build_ui at runtime. The legacy install() entry point remains temporarily
because app.py still invokes the Phase 5 startup installers.
"""

from services.user_safety_snapshot_service import UserSafetySnapshotService
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.ui_safety import confirm_destructive_action

_INSTALLED = False


def _label_for(build) -> str:
    build_name = str(getattr(build, "BuildName", "") or "").strip()
    character = str(getattr(build, "Name", "") or "").strip()
    if build_name and character:
        return f"{character} — {build_name}"
    return build_name or character or "selected build"


def _delete_selected(page) -> None:
    members = getattr(getattr(page, "roster", None), "Members", None)
    index = int(getattr(page, "selected_index", -1))
    if not isinstance(members, list) or index < 0 or index >= len(members):
        return

    build = members[index]
    label = _label_for(build)
    if not confirm_destructive_action(
        page,
        title="Delete Build",
        object_label=f'Delete build "{label}"?',
        impact=(
            "The character and shared Character Progression are kept. "
            "A recoverable database snapshot is created before the build is removed."
        ),
        confirm_text="Delete Build",
    ):
        return

    build_id = str(getattr(build, "BuildId", "") or label).strip()
    UserSafetySnapshotService().create(f"delete-build-{build_id}")
    members.pop(index)
    page.selected_index = min(index, max(0, len(members) - 1))
    page._save()
    page._refresh_roster()
    if not members:
        page._clear_detail()
    page.status.success(f"Deleted build: {label}. Character progression was preserved.")


def attach_delete_build_action(page) -> FoundryButton | None:
    """Attach the destructive build action to one constructed Builds page."""
    existing = getattr(page, "delete_build_button", None)
    if isinstance(existing, FoundryButton):
        return existing

    edit_button = getattr(page, "edit_button", None)
    parent = edit_button.parentWidget() if edit_button is not None else None
    layout = parent.layout() if parent is not None else None
    if layout is None:
        return None

    button = FoundryButton("Delete Build", role=ButtonRole.DANGER)
    button.clicked.connect(lambda: _delete_selected(page))
    page.delete_build_button = button
    # Destructive action is deliberately last in the fixed page action row.
    layout.addWidget(button)
    return button


def install() -> None:
    """Retained startup compatibility; page composition is now explicit."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True


__all__ = ["attach_delete_build_action", "install"]
