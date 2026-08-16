# ==================================================
# Black Feather Foundry
#
# File:
# widgets/achievement_stats.py
#
# Purpose:
# Small stat boxes for the Achievement Desk:
# achievement points, category/dungeon/trial
# progress, a free-form box, and an achievement
# details lookup. Meant to sit inside FoundryCard
# containers, which already supply the box title.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from ui.theme.colors import Colors
from ui.theme.fonts import Fonts


# --------------------------------------------------
# Shared value label
# --------------------------------------------------

class StatValueLabel(QLabel):
    """
    Large, centered statistic value for use inside a
    FoundryCard, e.g. "24,530" or "356 / 395".
    """

    def __init__(
        self,
        text: str = "—",
        parent=None,
    ):
        super().__init__(text, parent)

        self.setFont(
            Fonts.statistic()
        )

        self.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.setStyleSheet(
            f"color: {Colors.GOLD};"
        )


# --------------------------------------------------
# Achievement Points
# --------------------------------------------------

class AchievementPointsCard(QWidget):
    """
    Total achievement points earned.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.value = StatValueLabel("0")

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.value)

    def set_points(self, earned: int):

        self.value.setText(
            f"{earned:,}"
        )


# --------------------------------------------------
# Earned / Total ratio (Dungeons, Trials, etc.)
# --------------------------------------------------

class AchievementRatioCard(QWidget):
    """
    Simple "earned / total" display, e.g. "356 / 395".
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.value = StatValueLabel("0 / 0")

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.value)

    def set_ratio(self, earned: int, total: int):

        self.value.setText(
            f"{earned:,} / {total:,}"
        )


# --------------------------------------------------
# Category picker + ratio
# --------------------------------------------------

class CategoryProgressCard(QWidget):
    """
    Category picker with points earned / total points
    possible for whichever category is selected.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.picker = QComboBox()

        self.value = StatValueLabel("0 / 0")

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(6)

        layout.addWidget(self.picker)

        layout.addWidget(self.value)

    def set_categories(self, categories: list[str]):

        self.picker.blockSignals(True)

        self.picker.clear()

        self.picker.addItems(categories)

        self.picker.blockSignals(False)

    def current_category(self) -> str:

        return self.picker.currentText()

    def set_ratio(self, earned: int, total: int):

        self.value.setText(
            f"{earned:,} / {total:,}"
        )


# --------------------------------------------------
# Free-form "x / x" box
# --------------------------------------------------

class CustomStatCard(QWidget):
    """
    Blank box the user can type "x / x" (or anything
    else) into. Not wired to any data source -- just
    free text for whatever the user wants to track.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.value = QLineEdit()

        self.value.setPlaceholderText(
            "e.g. 12 / 20"
        )

        self.value.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.value.setFont(
            Fonts.statistic()
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.value)

    def text(self) -> str:

        return self.value.text()

    def set_text(self, text: str):

        self.value.setText(text)


# --------------------------------------------------
# Achievement Details
# --------------------------------------------------

class AchievementDetailsPanel(QWidget):
    """
    Search for an achievement and show its details --
    name, description, points, completion status, and
    title reward -- matching the wireframe's Achievement
    Details box.
    """

    def __init__(
        self,
        database_service,
        progress_service,
        parent=None,
    ):
        super().__init__(parent)

        self.database_service = database_service

        self.progress_service = progress_service

        #
        # Search
        #

        self.search = QLineEdit()

        self.search.setPlaceholderText(
            "Search achievements..."
        )

        self.results = QListWidget()

        self.results.setMaximumHeight(90)

        self.results.setVisible(False)

        #
        # Details
        #

        self.name = QLabel(
            "Search for an achievement to see its details."
        )

        self.name.setWordWrap(True)

        self.name.setFont(
            Fonts.section_title()
        )

        self.description = QLabel("")

        self.description.setWordWrap(True)

        self.description.setStyleSheet(
            f"color: {Colors.TEXT_MUTED};"
        )

        self.points = StatValueLabel("")

        self.status = QLabel("")

        self.reward = QLabel("")

        self.reward.setWordWrap(True)

        #
        # Layout
        #

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(8)

        layout.addWidget(self.search)

        layout.addWidget(self.results)

        layout.addWidget(self.name)

        layout.addWidget(self.description)

        layout.addWidget(self.points)

        layout.addWidget(self.status)

        layout.addWidget(self.reward)

        #
        # Signals
        #

        self.search.textChanged.connect(
            self._search_changed
        )

        self.results.itemClicked.connect(
            self._result_selected
        )

    # --------------------------------------------------
    # Search
    # --------------------------------------------------

    def _search_changed(self, text: str):

        text = text.strip()

        self.results.clear()

        if not text:

            self.results.setVisible(False)

            return

        matches = self.database_service.search(text)[:20]

        for achievement in matches:

            item = QListWidgetItem(
                achievement["name"]
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                achievement["id"],
            )

            self.results.addItem(item)

        self.results.setVisible(
            bool(matches)
        )

    def _result_selected(self, item: QListWidgetItem):

        achievement_id = item.data(
            Qt.ItemDataRole.UserRole
        )

        if achievement_id is not None:

            self.load_achievement(achievement_id)

    # --------------------------------------------------
    # Details
    # --------------------------------------------------

    def load_achievement(self, achievement_id):

        achievement = self.database_service.achievement(
            achievement_id
        )

        if achievement is None:
            return

        self.name.setText(
            achievement["name"]
        )

        self.description.setText(
            achievement["desc"] or ""
        )

        self.points.setText(
            f"{achievement.get('points', 0)} points"
        )

        completed = self.progress_service.is_complete(
            achievement_id
        )

        if completed:

            self.status.setText(
                "✓ Completed"
            )

            self.status.setStyleSheet(
                f"color: {Colors.SUCCESS};"
            )

        else:

            self.status.setText(
                "Not completed"
            )

            self.status.setStyleSheet(
                f"color: {Colors.TEXT_MUTED};"
            )

        title = achievement.get("title") or ""

        self.reward.setText(
            f"Title Reward: {title}" if title else ""
        )

    def clear(self):

        self.search.clear()

        self.results.clear()

        self.results.setVisible(False)

        self.name.setText(
            "Search for an achievement to see its details."
        )

        self.description.setText("")

        self.points.setText("")

        self.status.setText("")

        self.reward.setText("")
