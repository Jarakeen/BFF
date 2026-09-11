from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.community_news_page import CommunityNewsPage
from ui.components.foundry_sidebar import FoundrySidebar, nav_sections


def _flatten_pages(sections) -> set[str]:
    pages: set[str] = set()
    for section in sections:
        if isinstance(section, tuple):
            if len(section) > 1:
                pages.add(str(section[1]))
            continue
        if section.get("page"):
            pages.add(str(section["page"]))
        for _label, page in section.get("children", ()):  # pragma: no branch - tiny helper
            pages.add(str(page))
    return pages


def test_community_news_is_hidden_and_inert():
    app = QApplication.instance() or QApplication([])

    assert "community_news" not in _flatten_pages(nav_sections(False))

    sidebar = FoundrySidebar(include_broadcast=False)
    assert "community_news" not in sidebar.buttons

    page = CommunityNewsPage()
    assert page.service is None
    assert page._latest_task is None
    assert page._trending_task is None
    assert page.header is None
    assert page.workspace_layout.count() == 0

    page.close()
    sidebar.close()
    app.processEvents()
