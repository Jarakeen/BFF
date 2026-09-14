from __future__ import annotations

"""Keep the long-lived Rotation dashboard synchronized with saved Builds state.

The main window constructs Rotations once at application startup. Builds can be
edited, copied, templated, imported, or replaced afterward. Re-entering Rotations
must therefore reload the canonical saved-build roster instead of continuing to
hold stale in-memory PlayerBuild objects from startup.
"""

_INSTALLED = False


def _restore_selection(page, character_name: str, build_name: str) -> None:
    character_index = page.character_combo.findData(character_name)
    if character_index < 0 and page.character_combo.count():
        character_index = 0
    if character_index >= 0:
        page.character_combo.setCurrentIndex(character_index)

    build_index = page.build_combo.findText(build_name)
    if build_index < 0 and page.build_combo.count():
        build_index = 0
    if build_index >= 0:
        page.build_combo.setCurrentIndex(build_index)


def refresh_saved_builds(page) -> None:
    """Reload canonical saved Builds and rebuild the selectors safely."""
    selected_character = str(page.character_combo.currentData() or "")
    selected_build = str(page.build_combo.currentText() or "")

    page.roster = page.build_service.load()

    page.character_combo.blockSignals(True)
    page.character_combo.clear()
    seen: set[str] = set()
    for build in page.roster.Members:
        name = page._character_name(build)
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        page.character_combo.addItem(name, name)
    page.character_combo.blockSignals(False)

    _restore_selection(page, selected_character, selected_build)
    page._character_changed()
    if selected_build:
        index = page.build_combo.findText(selected_build)
        if index >= 0:
            page.build_combo.setCurrentIndex(index)
    page._refresh_build_context()


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage

    original_show_event = CanonicalRotationDashboardPage.showEvent

    def show_event_with_saved_build_refresh(self, event) -> None:
        try:
            refresh_saved_builds(self)
        except Exception as exc:  # navigation must not take the whole app down
            status = getattr(self, "status", None)
            if status is not None and hasattr(status, "error"):
                status.error(f"Could not refresh saved builds for Rotations: {exc}")
            else:
                print(f"[FoundryDock] Rotation build refresh failed: {exc}")
        original_show_event(self, event)

    CanonicalRotationDashboardPage.showEvent = show_event_with_saved_build_refresh
    _INSTALLED = True


__all__ = ["install", "refresh_saved_builds"]
