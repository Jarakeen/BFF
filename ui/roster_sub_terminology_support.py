from __future__ import annotations

"""Use raid-lead-facing 'Sub' terminology instead of 'Bench'.

Legacy persisted records may still contain ``Bench``; widgets/roster_record.py
maps those records to the current ``Sub`` display value when edited, so this
layer only updates the remaining header presentation.

This helper is intentionally instance-based. Application composition applies it
after ``MainWindow`` constructs the real Roster page instead of replacing a
class method at runtime.
"""


def apply_roster_sub_terminology(page) -> None:
    """Rename any remaining Bench presentation option on one constructed page."""
    combo = getattr(page, "show_combo", None)
    if combo is None:
        return
    for index in range(combo.count()):
        if combo.itemText(index).strip().casefold() == "bench":
            combo.setItemText(index, "Sub")


__all__ = ["apply_roster_sub_terminology"]
