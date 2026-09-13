from __future__ import annotations

"""Use raid-lead-facing 'Sub' terminology instead of 'Bench'.

Legacy persisted records may still contain ``Bench``; widgets/roster_record.py
maps those records to the current ``Sub`` display value when edited, so this
layer only updates the remaining header presentation.
"""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original_build_ui = RosterPage._build_ui

    def build_ui_with_sub_terminology(self) -> None:
        original_build_ui(self)
        combo = getattr(self, "show_combo", None)
        if combo is not None:
            for index in range(combo.count()):
                if combo.itemText(index).strip().casefold() == "bench":
                    combo.setItemText(index, "Sub")

    RosterPage._build_ui = build_ui_with_sub_terminology
    _INSTALLED = True
