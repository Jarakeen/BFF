from __future__ import annotations

"""Phase 5 safe build deletion for the Builds page."""

from PySide6.QtWidgets import QMessageBox

from ui.components.foundry_button import ButtonRole, FoundryButton

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
    answer = QMessageBox.question(
        page,
        "Delete Build",
        f"Delete {label}?\n\nThe character and Character Progression will be kept.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return

    members.pop(index)
    page.selected_index = min(index, max(0, len(members) - 1))
    page._save()
    page._refresh_roster()
    if not members:
        page._clear_detail()
    page.status.success(f"Deleted build: {label}. Character progression was preserved.")


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    original_build_ui = BuildsPage._build_ui

    def patched_build_ui(self):
        original_build_ui(self)
        parent = self.edit_button.parentWidget()
        layout = parent.layout() if parent is not None else None
        if layout is None:
            return
        # Match the surrounding Builds actions. The confirmation dialog carries
        # the destructive warning, so the toolbar itself stays visually calm.
        self.delete_build_button = FoundryButton("Delete Build", role=ButtonRole.SECONDARY)
        self.delete_build_button.clicked.connect(lambda: _delete_selected(self))
        # Keep destructive action next to Edit but before Save/Export.
        save_index = layout.indexOf(self.save_button)
        layout.insertWidget(save_index if save_index >= 0 else layout.count(), self.delete_build_button)

    BuildsPage._build_ui = patched_build_ui
    _INSTALLED = True
