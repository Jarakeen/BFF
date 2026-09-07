from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QPushButton

from services.stickerbook_bookmark_service import StickerbookBookmarkService
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_INIT = None
_ORIGINAL_FILTER_SETS = None
_ORIGINAL_SHOW_SELECTED = None


def _details_card(page) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Set Details":
            return card
    return None


def _available_profiles(page) -> list[str]:
    values: set[str] = {"Default"}
    try:
        with sqlite3.connect(page.database_path) as connection:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "stickerbook_progress" in tables:
                values.update(
                    str(row[0]).strip()
                    for row in connection.execute(
                        "SELECT DISTINCT profile_id FROM stickerbook_progress"
                    ).fetchall()
                    if str(row[0] or "").strip()
                )
            if "stickerbook_set_bookmark" in tables:
                values.update(
                    str(row[0]).strip()
                    for row in connection.execute(
                        "SELECT DISTINCT profile_id FROM stickerbook_set_bookmark"
                    ).fetchall()
                    if str(row[0] or "").strip()
                )
    except sqlite3.Error:
        pass
    return sorted(values, key=str.casefold)


def _profile(page) -> str:
    combo = getattr(page, "gear_bookmark_profile", None)
    value = combo.currentText().strip() if combo is not None else "Default"
    return value or "Default"


def _selected_row(page):
    current = getattr(page, "results", None)
    item = current.currentItem() if current is not None else None
    if item is None:
        return None
    catalog_id = item.data(Qt.ItemDataRole.UserRole)
    return next((row for row in page._sets if row["id"] == catalog_id), None)


def _bookmarked_ids(page) -> set[int]:
    service = getattr(page, "gear_bookmark_service", None)
    if service is None:
        return set()
    return service.bookmarked_set_ids(_profile(page))


def _update_button(page) -> None:
    button = getattr(page, "gear_bookmark_button", None)
    service = getattr(page, "gear_bookmark_service", None)
    row = _selected_row(page)
    if button is None or service is None:
        return
    set_id = row.get("gear_set_id") if row is not None else None
    if set_id is None:
        button.setEnabled(False)
        button.setText("☆ Save for Trial Comp")
        button.setToolTip(
            "This catalog-only set can be bookmarked once it has a normalized gear-set id."
        )
        return
    bookmarked = service.is_bookmarked(_profile(page), int(set_id))
    button.setEnabled(True)
    button.setText("★ Saved for Trial Comp" if bookmarked else "☆ Save for Trial Comp")
    button.setToolTip(
        "Remove this set from the trial-comp shortlist."
        if bookmarked
        else "Bookmark this set as gear you may want to try in a trial composition."
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
        catalog_id = item.data(Qt.ItemDataRole.UserRole)
        row = next((row for row in page._sets if row["id"] == catalog_id), None)
        set_id = row.get("gear_set_id") if row is not None else None
        item.setText(f"★ {text}" if set_id in bookmarked else text)


def _apply_bookmark_filter(page) -> None:
    combo = getattr(page, "gear_bookmark_filter", None)
    results = getattr(page, "results", None)
    if combo is None or results is None or combo.currentData() != "bookmarked":
        return
    bookmarked = _bookmarked_ids(page)
    for index in range(results.count() - 1, -1, -1):
        item = results.item(index)
        catalog_id = item.data(Qt.ItemDataRole.UserRole)
        row = next((row for row in page._sets if row["id"] == catalog_id), None)
        set_id = row.get("gear_set_id") if row is not None else None
        if set_id not in bookmarked:
            results.takeItem(index)


def _toggle_bookmark(page) -> None:
    row = _selected_row(page)
    service = getattr(page, "gear_bookmark_service", None)
    if row is None or service is None:
        return
    set_id = row.get("gear_set_id")
    if set_id is None:
        return
    profile = _profile(page)
    current = service.is_bookmarked(profile, int(set_id))
    service.set_bookmarked(profile, int(set_id), not current)
    page._filter_sets()
    page.status.success(
        f"{'Removed' if current else 'Saved'} {row['name']} "
        f"{'from' if current else 'to'} the trial-comp shortlist."
    )


def _filter_sets_with_bookmarks(self, *args) -> None:
    assert _ORIGINAL_FILTER_SETS is not None
    _ORIGINAL_FILTER_SETS(self, *args)
    _apply_bookmark_filter(self)
    _decorate_results(self)
    _update_button(self)


def _show_selected_with_bookmark(self, current, previous=None) -> None:
    assert _ORIGINAL_SHOW_SELECTED is not None
    _ORIGINAL_SHOW_SELECTED(self, current, previous)
    _update_button(self)


def _install_bookmarks(page) -> None:
    page.gear_bookmark_service = StickerbookBookmarkService(page.database_path)

    profile = QComboBox()
    profile.setEditable(True)
    profile.addItems(_available_profiles(page))
    profile.setCurrentText("Default")
    profile.setMinimumWidth(140)
    profile.currentTextChanged.connect(lambda *_: page._filter_sets())
    page.gear_bookmark_profile = profile
    page.header.add_context_widget(page._context_field("SHORTLIST PROFILE", profile))

    show = QComboBox()
    show.addItem("All Sets", "all")
    show.addItem("★ Bookmarked", "bookmarked")
    show.setMinimumWidth(135)
    show.currentIndexChanged.connect(lambda *_: page._filter_sets())
    page.gear_bookmark_filter = show
    page.header.add_context_widget(page._context_field("SHOW", show))

    button = QPushButton("☆ Save for Trial Comp")
    button.setProperty("gearSetBookmark", True)
    button.clicked.connect(lambda *_: _toggle_bookmark(page))
    page.gear_bookmark_button = button
    details = _details_card(page)
    if details is not None:
        details.set_header_action(button)

    _decorate_results(page)
    _update_button(page)


def _init_with_bookmarks(self, parent=None) -> None:
    assert _ORIGINAL_INIT is not None
    _ORIGINAL_INIT(self, parent)
    _install_bookmarks(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_INIT, _ORIGINAL_FILTER_SETS, _ORIGINAL_SHOW_SELECTED
    if _INSTALLED:
        return

    from ui.gear_lookup_page import GearLookupPage

    _ORIGINAL_INIT = GearLookupPage.__init__
    _ORIGINAL_FILTER_SETS = GearLookupPage._filter_sets
    _ORIGINAL_SHOW_SELECTED = GearLookupPage._show_selected

    GearLookupPage.__init__ = _init_with_bookmarks
    GearLookupPage._filter_sets = _filter_sets_with_bookmarks
    GearLookupPage._show_selected = _show_selected_with_bookmark
    _INSTALLED = True
