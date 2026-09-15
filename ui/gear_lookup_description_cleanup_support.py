from __future__ import annotations

"""Instance-level cleanup for ESO color markup in Gear Lookup descriptions.

Gear Lookup owns the canonical selection/render path. This helper only normalizes
its already-rendered bonus text, so it composes with the constructed page instead
of replacing ``GearLookupPage._show_selected`` at runtime.
"""

from ui.eso_text_cleanup import strip_eso_color_markup


def apply_gear_lookup_description_cleanup(page) -> None:
    """Strip ESO color markup after each normal Gear Lookup selection render."""
    if getattr(page, "_gear_lookup_description_cleanup_handler", None) is not None:
        return

    results = getattr(page, "results", None)
    bonuses = getattr(page, "bonuses", None)
    if results is None or bonuses is None:
        return

    def cleanup(*_args) -> None:
        current = bonuses.text()
        cleaned = strip_eso_color_markup(current)
        if cleaned != current:
            bonuses.setText(cleaned)

    # Keep the closure on the page for an explicit lifetime and idempotency marker.
    page._gear_lookup_description_cleanup_handler = cleanup
    results.currentItemChanged.connect(cleanup)
    cleanup()


__all__ = ["apply_gear_lookup_description_cleanup"]
