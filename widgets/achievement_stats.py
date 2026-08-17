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
    QSizePolicy,
)
from PySide6.QtGui import QFont
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

        stat_font = QFont()
        stat_font.setPointSize(28)
        stat_font.setBold(True)

        self.setFont(
            stat_font
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
    Displays the details of the achievement selected
    in the Achievement browser.

    The search box was intentionally removed from this
    panel. Searching now happens in CollectionBrowser.
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

        # --------------------------------------------------
        # Achievement Name
        # --------------------------------------------------

        self.name = QLabel("")

        self.name.setWordWrap(True)

        name_font = QFont()
        name_font.setPointSize(24)
        name_font.setBold(True)

        self.name.setFont(
            name_font
        )

        # --------------------------------------------------
        # Description
        # --------------------------------------------------

        self.description = QLabel("")

        self.description.setWordWrap(True)

        description_font = QFont()
        description_font.setPointSize(20)

        self.description.setFont(
            description_font
        )

        self.description.setStyleSheet(
            f"color: {Colors.TEXT_MUTED};"
        )

        # --------------------------------------------------
        # Points
        # --------------------------------------------------

        self.points = QLabel("")

        points_font = QFont()
        points_font.setPointSize(20)
        points_font.setBold(True)

        self.points.setFont(
            points_font
        )

        self.points.setStyleSheet(
            f"color: {Colors.GOLD};"
        )

        # --------------------------------------------------
        # Completion Status
        # --------------------------------------------------

        self.status = QLabel("")

        status_font = QFont()
        status_font.setPointSize(20)

        self.status.setFont(
            status_font
        )

        # --------------------------------------------------
        # Reward
        # --------------------------------------------------

        self.reward = QLabel("")

        self.reward.setWordWrap(True)

        reward_font = QFont()
        reward_font.setPointSize(20)

        self.reward.setFont(
            reward_font
        )

        # --------------------------------------------------
        # Layout
        # --------------------------------------------------

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        layout.setSpacing(16)

        layout.addWidget(
            self.name
        )

        layout.addWidget(
            self.description
        )

        layout.addWidget(
            self.points
        )

        layout.addWidget(
            self.status
        )

        layout.addWidget(
            self.reward
        )

        layout.addStretch()

    # --------------------------------------------------
    # Load Achievement
    # --------------------------------------------------

    def load_achievement(
        self,
        achievement_id,
    ):

        achievement = (
            self.database_service.achievement(
                achievement_id
            )
        )

        if achievement is None:
            return

        # --------------------------------------------------
        # Name
        # --------------------------------------------------

        self.name.setText(
            achievement["name"]
        )

        # --------------------------------------------------
        # Description
        # --------------------------------------------------

        self.description.setText(
            achievement["desc"] or ""
        )

        # --------------------------------------------------
        # Points
        # --------------------------------------------------

        self.points.setText(
            f"{achievement.get('points', 0)} points"
        )

        # --------------------------------------------------
        # Completion
        # --------------------------------------------------

        completed = (
            self.progress_service.is_complete(
                achievement_id
            )
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

        # --------------------------------------------------
        # Title Reward
        # --------------------------------------------------

        title = (
            achievement.get("title")
            or ""
        )

        self.reward.setText(
            f"Title Reward: {title}"
            if title
            else ""
        )

    # --------------------------------------------------
    # Clear
    # --------------------------------------------------

    def clear(self):

        self.name.setText("")
        self.description.setText("")
        self.points.setText("")
        self.status.setText("")
        self.reward.setText("")
