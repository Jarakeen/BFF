from __future__ import annotations


_INSTALLED = False
_ORIGINAL_ROSTER_INIT = None
_ORIGINAL_REFRESH_CHOICES = None


def _roster_init_without_generated_dropdown(self, parent=None) -> None:
    """Keep generated-plan machinery available without exposing it in the Roster header."""
    assert _ORIGINAL_ROSTER_INIT is not None
    _ORIGINAL_ROSTER_INIT(self, parent)

    combo = getattr(self, "generated_plan_combo", None)
    if combo is not None:
        host = combo.parentWidget()
        if host is not None:
            host.hide()
        else:
            combo.hide()


def _refresh_generated_plan_choices_hidden(page, selected: str | None = None) -> None:
    """Refresh generated-plan state without adding a duplicate TEAM label to Roster."""
    assert _ORIGINAL_REFRESH_CHOICES is not None
    _ORIGINAL_REFRESH_CHOICES(page, selected)


def install() -> None:
    global _INSTALLED, _ORIGINAL_ROSTER_INIT, _ORIGINAL_REFRESH_CHOICES
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    _ORIGINAL_ROSTER_INIT = RosterPage.__init__
    _ORIGINAL_REFRESH_CHOICES = RosterPage._refresh_generated_plan_choices
    RosterPage.__init__ = _roster_init_without_generated_dropdown
    RosterPage._refresh_generated_plan_choices = _refresh_generated_plan_choices_hidden
    _INSTALLED = True
