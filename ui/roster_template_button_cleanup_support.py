from __future__ import annotations


_INSTALLED = False
_ORIGINAL_ROSTER_INIT = None


def _roster_init_without_template_button(self, parent=None) -> None:
    assert _ORIGINAL_ROSTER_INIT is not None
    _ORIGINAL_ROSTER_INIT(self, parent)

    # Template inspection remains available to internal services, but the Roster
    # page no longer exposes a conditional grey button that only works for a subset
    # of generated rows. Build/source details belong in Comp Maker instead.
    button = getattr(self, "view_template_button", None)
    if button is not None:
        button.hide()


def install() -> None:
    global _INSTALLED, _ORIGINAL_ROSTER_INIT
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    _ORIGINAL_ROSTER_INIT = RosterPage.__init__
    RosterPage.__init__ = _roster_init_without_template_button
    _INSTALLED = True
