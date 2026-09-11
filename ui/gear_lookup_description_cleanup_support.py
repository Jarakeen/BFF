from __future__ import annotations

from ui.eso_text_cleanup import strip_eso_color_markup

_INSTALLED = False
_ORIGINAL_SHOW_SELECTED = None


def install() -> None:
    global _INSTALLED, _ORIGINAL_SHOW_SELECTED
    if _INSTALLED:
        return

    from ui.gear_lookup_layout_support import install as install_layout_support
    from ui.gear_lookup_page import GearLookupPage

    install_layout_support()
    _ORIGINAL_SHOW_SELECTED = GearLookupPage._show_selected

    def show_selected_without_eso_markup(self, current, previous=None) -> None:
        _ORIGINAL_SHOW_SELECTED(self, current, previous)
        if hasattr(self, "bonuses"):
            cleaned = strip_eso_color_markup(self.bonuses.text())
            if cleaned != self.bonuses.text():
                self.bonuses.setText(cleaned)

    GearLookupPage._show_selected = show_selected_without_eso_markup
    _INSTALLED = True
