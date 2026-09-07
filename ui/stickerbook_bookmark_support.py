from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QPushButton

from services.stickerbook_bookmark_service import StickerbookBookmarkService
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_INIT = None
_ORIGINAL_FILTERED_ROWS = None
_ORIGINAL_FILTER_SETS = None
_ORIGINAL_SHOW_SELECTED = None
_ORIGINAL_SET_PROFILE = None


def _details_card(page) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Set Details":
            return card
    return None


def _bookmarked_ids(page) -> set[int]:
    service = getattr(page, "stickerbook_bookmark_service", None)
    if service is None:
        return set()
    return service.bookmarked_set_ids(getattr(page, "profile_id", "Default"))


def _update_bookmark_button(page) -> None:
    button = getattr(page, "stickerbook_bookmark_button", None)
    service = getattr(page, "stickerbook_bookmark_service", None)
    set_id = getattr(page, "_selected_set_id", None)
    if button is None or service is None:
        return
    if set_id is None:
        button.setEnabled(False)
        button.setText("☆ Save for Trial Comp")
        return
    bookmarked = service.is_bookmarked(page.profile_id, int(set_id))
    button.setEnabled(True)
    button.setText("★ Saved for Trial Comp" if bookmarked else "☆ Save for Trial Comp")
    button.setToolTip(
        "Remove this set from your trial-comp shortlist."
        if bookmarked
        else "Bookmark this set as something you may want Comp Maker to consider later."
    )


def _decorate_results(page) -> None:
    results = getattr(page, "results", None)
    if results is None:
        return
    bookmarked = _bookmarked_ids(page)
    for index in range(results.count()):
        item = results.item(index)
        text = item.text()
        while text.startswith("★ "):
            text = text[2:]
        set_id = item.data(Qt.ItemDataRole.UserRole)
        item.setText(f"★ {text}" if set_id in bookmarked else text)


def _toggle_bookmark(page) -> None:
    service = getattr(page, "stickerbook_bookmark_service", None)
    set_id = getattr(page, "_selected_set_id", None)
    if service is None or set_id is None:
        return
    current = service.is_bookmarked(page.profile_id, int(set_id))
    service.set_bookmarked(page.profile_id, int(set_id), not current)
    _update_bookmark_button(page)
    page._filter_sets()
    page.status.success(
        "Saved set for trial-comp consideration."
        if not current
        else "Removed set from trial-comp bookmarks."
    )


def _filtered_rows_with_bookmarks(self) -> list[dict]:
    assert _ORIGINAL_FILTERED_ROWS is not None
    rows = _ORIGINAL_FILTERED_ROWS(self)
    combo = getattr(self, "stickerbook_bookmark_filter", None)
    if combo is None or combo.currentData() != "bookmarked":
        return rows
    bookmarked = _bookmarked_ids(self)
    return [row for row in rows if int(row["id"]) in bookmarked]


def _filter_sets_with_bookmarks(self, *args) -> None:
    assert _ORIGINAL_FILTER_SETS is not None
    _ORIGINAL_FILTER_SETS(self, *args)
    _decorate_results(self)
    _update_bookmark_button(self)


def _show_selected_with_bookmark(self, current, previous=None) -> None:
    assert _ORIGINAL_SHOW_SELECTED is not None
    _ORIGINAL_SHOW_SELECTED(self, current, previous)
    _update_bookmark_button(self)


def _set_profile_with_bookmarks(self, profile_id: str) -> None:
    assert _ORIGINAL_SET_PROFILE is not None
    _ORIGINAL_SET_PROFILE(self, profile_id)
    _decorate_results(self)
    _update_bookmark_button(self)


def _install_bookmark_ui(page) -> None:
    page.stickerbook_bookmark_service = StickerbookBookmarkService(page.service.database_path)

    filter_combo = QComboBox()
    filter_combo.addItem("All Sets", "all")
    filter_combo.addItem("★ Bookmarked for Comp", "bookmarked")
    filter_combo.setMinimumWidth(165)
    filter_combo.currentIndexChanged.connect(lambda *_: page._filter_sets())
    page.stickerbook_bookmark_filter = filter_combo
    page.header.add_context_widget(page._context("SHOW", filter_combo))

    bookmark_button = QPushButton("☆ Save for Trial Comp")
    bookmark_button.setProperty("stickerbookBookmark", True)
    bookmark_button.clicked.connect(lambda *_: _toggle_bookmark(page))
    page.stickerbook_bookmark_button = bookmark_button
    details = _details_card(page)
    if details is not None:
        details.set_header_action(bookmark_button)

    _decorate_results(page)
    _update_bookmark_button(page)


def _init_with_bookmarks(self, parent=None) -> None:
    assert _ORIGINAL_INIT is not None
    _ORIGINAL_INIT(self, parent)
    _install_bookmark_ui(self)


def install() -> None:
    global _INSTALLED
    global _ORIGINAL_INIT, _ORIGINAL_FILTERED_ROWS, _ORIGINAL_FILTER_SETS
    global _ORIGINAL_SHOW_SELECTED, _ORIGINAL_SET_PROFILE
    if _INSTALLED:
        return

    from ui.stickerbook_page import StickerbookPage

    _ORIGINAL_INIT = StickerbookPage.__init__
    _ORIGINAL_FILTERED_ROWS = StickerbookPage._filtered_rows
    _ORIGINAL_FILTER_SETS = StickerbookPage._filter_sets
    _ORIGINAL_SHOW_SELECTED = StickerbookPage._show_selected
    _ORIGINAL_SET_PROFILE = StickerbookPage.set_profile

    StickerbookPage.__init__ = _init_with_bookmarks
    StickerbookPage._filtered_rows = _filtered_rows_with_bookmarks
    StickerbookPage._filter_sets = _filter_sets_with_bookmarks
    StickerbookPage._show_selected = _show_selected_with_bookmark
    StickerbookPage.set_profile = _set_profile_with_bookmarks
    _INSTALLED = True
