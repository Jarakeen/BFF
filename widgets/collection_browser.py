# ==================================================
# Black Feather Foundry
#
# File:
# widgets/collection_browser.py
#
# Purpose:
# Browse ESO Collections.
#
# ==================================================

from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPalette
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
)

from ui.theme.colors import Colors


_PLAYER_PLACEHOLDER = re.compile(r"\s*<<player>>(?:'s)?\s*", re.IGNORECASE)


def clean_achievement_display_text(value: object) -> str:
    """Remove unresolved ESO player-name tokens from user-facing achievement text."""
    text = _PLAYER_PLACEHOLDER.sub(" ", str(value or ""))
    text = " ".join(text.split())
    return re.sub(r"\s+([,.;:!?])", r"\1", text).strip()


class CollectionBrowser(QWidget):
    """
    Browser for ESO Collections.

    Displays categories on the left and
    achievements on the right.
    """

    achievementChanged = Signal(int, bool)
    achievementSelected = Signal(object)

    def __init__(
        self,
        provider=None,
        progress=None,
        parent=None,
    ):
        super().__init__(parent)

        self.provider = provider
        self.progress_service = progress

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search Collections...")

        self.categories = QListWidget()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Achievement", "Points"])
        self.tree.setColumnWidth(0, 500)
        self.tree.setColumnWidth(1, 80)

        left = QVBoxLayout()
        left.addWidget(self.search)
        left.addWidget(self.categories)

        right = QVBoxLayout()
        right.addWidget(self.tree)

        content = QHBoxLayout()
        content.addLayout(left, 1)
        content.addLayout(right, 3)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(content)

        self.search.textChanged.connect(self.search_changed)
        self.categories.currentTextChanged.connect(self.category_changed)
        self.tree.itemClicked.connect(self.item_selected)
        # Connect once for the lifetime of the browser. Population methods
        # block tree signals so programmatic check-state updates are not
        # mistaken for user edits.
        self.tree.itemChanged.connect(self.item_changed)

    # --------------------------------------------------
    # Provider
    # --------------------------------------------------

    def set_provider(self, provider):
        self.provider = provider
        self.reload()

    # --------------------------------------------------
    # Loading
    # --------------------------------------------------

    def reload(self):
        self.categories.clear()
        if self.provider is None:
            return
        for category in self.provider.top_categories():
            self.categories.addItem(category)
        self.refresh_completion_styles()

    def category_changed(self, category):
        if not category:
            return

        self.tree.blockSignals(True)
        try:
            self.tree.clear()

            for subcategory in self.provider.subcategories(category):
                parent = QTreeWidgetItem([subcategory, ""])
                self.tree.addTopLevelItem(parent)

                for achievement in self.provider.achievements_in(category, subcategory):
                    child = QTreeWidgetItem(
                        [clean_achievement_display_text(achievement["name"]), str(achievement.get("points", ""))]
                    )
                    achievement_id = achievement["id"]
                    child.setCheckState(
                        0,
                        Qt.CheckState.Checked
                        if self.progress_service.is_complete(achievement_id)
                        else Qt.CheckState.Unchecked,
                    )
                    child.setData(0, Qt.ItemDataRole.UserRole, achievement_id)
                    parent.addChild(child)

                parent.setExpanded(True)
        finally:
            self.tree.blockSignals(False)
        self.refresh_completion_styles()

    # --------------------------------------------------
    # Completion styling
    # --------------------------------------------------

    def _text_brush(self, complete: bool) -> QBrush:
        if complete:
            return QBrush(QColor(Colors.GOLD))
        return QBrush(self.palette().color(QPalette.ColorRole.Text))

    def _subcategory_complete(self, category: str, subcategory: str) -> bool:
        if self.provider is None or self.progress_service is None:
            return False
        achievements = tuple(self.provider.achievements_in(category, subcategory))
        return bool(achievements) and all(
            self.progress_service.is_complete(achievement["id"])
            for achievement in achievements
        )

    def _category_complete(self, category: str) -> bool:
        if self.provider is None or self.progress_service is None:
            return False
        subcategories = tuple(self.provider.subcategories(category))
        if not subcategories:
            return False
        seen_achievement = False
        for subcategory in subcategories:
            achievements = tuple(self.provider.achievements_in(category, subcategory))
            if not achievements:
                continue
            seen_achievement = True
            if not all(
                self.progress_service.is_complete(achievement["id"])
                for achievement in achievements
            ):
                return False
        return seen_achievement

    def refresh_completion_styles(self) -> None:
        """Gold completed categories/subcategories using the Achievement Points accent."""
        if self.provider is None or self.progress_service is None:
            return

        for index in range(self.categories.count()):
            item = self.categories.item(index)
            item.setForeground(self._text_brush(self._category_complete(item.text())))

        current = self.categories.currentItem()
        category = current.text() if current is not None else ""
        if not category or self.search.text().strip():
            return

        for index in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(index)
            # Normal category browsing uses top-level subcategory headers with
            # children. Search results are top-level achievements and are not
            # category headers, so leave them alone.
            if parent.childCount() <= 0 or parent.data(0, Qt.ItemDataRole.UserRole) is not None:
                continue
            parent.setForeground(
                0,
                self._text_brush(self._subcategory_complete(category, parent.text(0))),
            )

    # --------------------------------------------------
    # Search
    # --------------------------------------------------

    def search_changed(self, text):
        if self.provider is None:
            return

        if not text:
            current = self.categories.currentItem()
            if current:
                self.category_changed(current.text())
            return

        self.tree.blockSignals(True)
        try:
            self.tree.clear()

            for achievement in self.provider.search(text):
                item = QTreeWidgetItem(
                    [clean_achievement_display_text(achievement["name"]), str(achievement.get("points", ""))]
                )
                item.setData(0, Qt.ItemDataRole.UserRole, achievement["id"])
                item.setCheckState(
                    0,
                    Qt.CheckState.Checked
                    if achievement["completed"]
                    else Qt.CheckState.Unchecked,
                )
                self.tree.addTopLevelItem(item)
        finally:
            self.tree.blockSignals(False)

    # --------------------------------------------------
    # Progress
    # --------------------------------------------------

    def item_changed(self, item, column):
        achievement_id = item.data(0, Qt.ItemDataRole.UserRole)
        if achievement_id is None:
            return

        complete = item.checkState(0) == Qt.CheckState.Checked
        self.achievementChanged.emit(achievement_id, complete)

    # --------------------------------------------------
    # Selection
    # --------------------------------------------------

    def item_selected(self, item, column):
        achievement_id = item.data(0, Qt.ItemDataRole.UserRole)
        if achievement_id is None:
            return
        self.achievementSelected.emit(achievement_id)
