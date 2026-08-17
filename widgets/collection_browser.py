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

from PySide6.QtCore import Qt, Signal

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QLabel,
)


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

        #
        # Search
        #

        self.search = QLineEdit()

        self.search.setPlaceholderText(
            "Search Collections..."
        )

        #
        # Categories
        #

        self.categories = QListWidget()

        #
        # Browser
        #

        self.tree = QTreeWidget()

        # --------------------------------------------------
        # Achievement list
        #
        # Keep only the achievement name and points.
        # The description belongs in Achievement Details.
        # --------------------------------------------------

        self.tree.setHeaderLabels(
            [
                "Achievement",
                "Points",
            ]
        )

        self.tree.setColumnWidth(
            0,
            500,
        )

        self.tree.setColumnWidth(
            1,
            80,
        )

        
        #
        # Layout
        #

        left = QVBoxLayout()

        left.addWidget(
            self.search
        )

        left.addWidget(
            self.categories
        )

        right = QVBoxLayout()

        right.addWidget(
            self.tree
        )

    

        content = QHBoxLayout()

        content.addLayout(
            left,
            1,
        )

        content.addLayout(
            right,
            3,
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.addLayout(
            content
        )

        #
        # Signals
        #

        self.search.textChanged.connect(
            self.search_changed
        )

        self.categories.currentTextChanged.connect(
            self.category_changed
        )

        self.tree.itemClicked.connect(
            self.item_selected
        )

    # --------------------------------------------------
    # Provider
    # --------------------------------------------------

    def set_provider(
        self,
        provider,
    ):

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

            self.categories.addItem(
                category
            )

       

    def category_changed(
        self,
        category,
    ):

        if not category:
            return

        self.tree.clear()

        for subcategory in self.provider.subcategories(
            category
        ):

            parent = QTreeWidgetItem(
                [
                    subcategory,
                    "",
                ]
            )

            self.tree.addTopLevelItem(
                parent
            )

            for achievement in self.provider.achievements_in(
                category,
                subcategory,
            ):

                child = QTreeWidgetItem(
                    [
                        achievement["name"],
                        str(
                            achievement.get(
                                "points",
                                ""
                            )
                        ),
                    ]
                )

                achievement_id = achievement["id"]

                if self.progress_service.is_complete(
                    achievement_id
                ):

                    child.setCheckState(
                        0,
                        Qt.CheckState.Checked,
                    )

                else:

                    child.setCheckState(
                        0,
                        Qt.CheckState.Unchecked,
                    )

                child.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    achievement_id,
                )

                parent.addChild(
                    child
                )

            parent.setExpanded(
                True
            )

        #
        # Connect only once.
        #
        # Reconnecting this signal every time a category
        # changes can cause duplicate callbacks.
        #

        try:
            self.tree.itemChanged.disconnect(
                self.item_changed
            )
        except (TypeError, RuntimeError):
            pass

        self.tree.itemChanged.connect(
            self.item_changed
        )

    # --------------------------------------------------
    # Search
    # --------------------------------------------------

    def search_changed(
        self,
        text,
    ):

        if self.provider is None:
            return

        if not text:

            current = self.categories.currentItem()

            if current:

                self.category_changed(
                    current.text()
                )

            return

        self.tree.clear()

        for achievement in self.provider.search(
            text
        ):

            item = QTreeWidgetItem(
                [
                    achievement["name"],
                    str(
                        achievement.get(
                            "points",
                            ""
                        )
                    ),
                ]
            )

            item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                achievement["id"],
            )

            item.setCheckState(
                0,
                Qt.CheckState.Checked
                if achievement["completed"]
                else Qt.CheckState.Unchecked,
            )

            self.tree.addTopLevelItem(
                item
            )

    # --------------------------------------------------
    # Progress
    # --------------------------------------------------

    def item_changed(
        self,
        item,
        column,
    ):

        achievement_id = item.data(
            0,
            Qt.ItemDataRole.UserRole,
        )

        if achievement_id is None:
            return

        complete = (
            item.checkState(0)
            == Qt.CheckState.Checked
        )

        self.achievementChanged.emit(
            achievement_id,
            complete,
        )


    # --------------------------------------------------
    # Selection
    # --------------------------------------------------

    def item_selected(
        self,
        item,
        column,
    ):

        achievement_id = item.data(
            0,
            Qt.ItemDataRole.UserRole,
        )

        if achievement_id is None:
            return

        self.achievementSelected.emit(
            achievement_id
        )