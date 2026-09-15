from __future__ import annotations

"""Explicit instance-level UI composition after ``MainWindow`` construction.

Pre-construction installers are still used by older features that replace class
methods. New migrations should prefer this module when a feature only needs to
configure an already-created page instance. Keeping those calls here makes the
application boundary visible and avoids hiding presentation behavior behind
runtime class mutation.
"""

from ui.roster_sub_terminology_support import apply_roster_sub_terminology


def compose_application_window(window) -> None:
    """Apply instance-level presentation features to the constructed application."""
    apply_roster_sub_terminology(window.pages["roster_page"])


__all__ = ["compose_application_window"]
