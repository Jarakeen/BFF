from __future__ import annotations

import re

_INSTALLED = False
_ORIGINAL_SHOW_SELECTED = None

# ESO tooltip text can contain inline color markup such as |cffffff or the
# malformed/extended |cffffff0 seen in imported set descriptions. Gear Lookup
# is plain-text UI, so these source formatting tokens should never be visible.
_ESO_COLOR_TAG_RE = re.compile(r"\|c[0-9A-Fa-f]{6,8}")


def strip_eso_color_markup(value: str) -> str:
    return _ESO_COLOR_TAG_RE.sub("", str(value or "")).replace("|r", "")


def install() -> None:
    global _INSTALLED, _ORIGINAL_SHOW_SELECTED
    if _INSTALLED:
        return

    from ui.gear_lookup_page import GearLookupPage

    _ORIGINAL_SHOW_SELECTED = GearLookupPage._show_selected

    def show_selected_without_eso_markup(self, current, previous=None) -> None:
        _ORIGINAL_SHOW_SELECTED(self, current, previous)
        if hasattr(self, "bonuses"):
            cleaned = strip_eso_color_markup(self.bonuses.text())
            if cleaned != self.bonuses.text():
                self.bonuses.setText(cleaned)

    GearLookupPage._show_selected = show_selected_without_eso_markup
    _INSTALLED = True
