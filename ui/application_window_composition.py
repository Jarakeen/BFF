from __future__ import annotations

"""Explicit instance-level UI composition after ``MainWindow`` construction.

Pre-construction installers are still used by older features that replace class
methods. New migrations should prefer this module when a feature only needs to
configure an already-created page instance. Keeping those calls here makes the
application boundary visible and avoids hiding presentation behavior behind
runtime class mutation.
"""

from ui.extreme_max_magicka_record_support import apply_extreme_max_magicka_record
from ui.gear_lookup_description_cleanup_support import (
    apply_gear_lookup_description_cleanup,
)
from ui.roster_sub_terminology_support import apply_roster_sub_terminology


def compose_application_window(window) -> None:
    """Apply instance-level presentation features to the constructed application."""
    apply_roster_sub_terminology(window.pages["roster_page"])
    apply_gear_lookup_description_cleanup(window.pages["gear_lookup"])
    apply_extreme_max_magicka_record(window.pages["extreme_optimization"])


__all__ = ["compose_application_window"]
