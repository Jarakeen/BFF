from __future__ import annotations

"""Temporarily disabled Community News page.

The original feed implementation was causing unwanted flashing/repaint behavior.
Keep the page class import-compatible, but do not build the rich-text UI, create
feed services, or start any background tasks while the feature is disabled.

The sidebar entry is also removed at import time so the page is not exposed in
normal navigation. The previous implementation remains available in git history
for later repair/reintroduction.
"""

from ui.components import foundry_sidebar as _foundry_sidebar
from ui.foundry_page import FoundryPage


_foundry_sidebar.CORE_NAV_SECTIONS[:] = [
    section
    for section in _foundry_sidebar.CORE_NAV_SECTIONS
    if not (
        isinstance(section, tuple)
        and len(section) > 1
        and section[1] == "community_news"
    )
]


class CommunityNewsPage(FoundryPage):
    """Inert compatibility shell while Community News is disabled."""

    def __init__(self, service=None, parent=None):
        super().__init__(parent)
        self.service = service
        self._latest_items = None
        self._trending_items = None
        self._latest_task = None
        self._trending_task = None
        # Deliberately do not build the feed UI, connect signals, or refresh.


__all__ = ["CommunityNewsPage"]
