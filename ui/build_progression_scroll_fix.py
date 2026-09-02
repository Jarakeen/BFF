from __future__ import annotations

"""Use the Builds page as the sole vertical scroll owner for embedded progression.

CharacterProgressionDialog keeps its own scroll areas when used as a standalone
window.  When that same widget is embedded in Builds, those nested scroll areas
are unwrapped so mouse-wheel handling and page sizing belong to FoundryPage.
"""

from PySide6.QtWidgets import QScrollArea, QTabWidget

_INSTALLED = False


def _unwrap_progression_scroll_areas(panel) -> None:
    tabs = panel.findChild(QTabWidget)
    if tabs is None:
        return

    for index in range(tabs.count()):
        page = tabs.widget(index)
        if not isinstance(page, QScrollArea):
            continue
        title = tabs.tabText(index)
        icon = tabs.tabIcon(index)
        tooltip = tabs.tabToolTip(index)
        content = page.takeWidget()
        if content is None:
            continue
        tabs.removeTab(index)
        tabs.insertTab(index, content, icon, title)
        tabs.setTabToolTip(index, tooltip)
        page.deleteLater()


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    original_load_progression = BuildsPage._load_progression_tab

    def load_progression_without_inner_scroll(self, index: int) -> None:
        original_load_progression(self, index)
        panel = getattr(self, "_progression_panel", None)
        if panel is not None:
            _unwrap_progression_scroll_areas(panel)

    BuildsPage._load_progression_tab = load_progression_without_inner_scroll
    _INSTALLED = True
