# ==================================================
# Black Feather Foundry
#
# File:
# services/achievement_provider.py
#
# Purpose:
# Provides Achievement data to the
# Collections page.
#
# ==================================================

from __future__ import annotations

import json

from pathlib import Path

from services.achievement_progress_service import (
    AchievementProgressService,
)


class AchievementProvider:
    """
    Provides Achievement data.

    This class is the single source of
    achievement information used by the
    Collections browser.
    """

    def __init__(
        self,
        data_path: Path,
        progress: AchievementProgressService,
    ):

        self.data_path = data_path

        self.progress = progress

        self._data = None

    # --------------------------------------------------
    # Data
    # --------------------------------------------------

    def load(self):

        if self._data is not None:
            return

        if not self.data_path.exists():

            self._data = []

            return

        self._data = json.loads(
            self.data_path.read_text(
                encoding="utf-8"
            )
        )

    # --------------------------------------------------
    # Categories
    # --------------------------------------------------

    def categories(self) -> list[str]:

        self.load()

        categories = {
            item["category"]
            for item in self._data
        }

        return sorted(categories)

    def subcategories(
        self,
        category: str,
    ) -> list[str]:

        self.load()

        subcategories = {

            item["subcategory"]

            for item in self._data

            if item["category"] == category

        }

        return sorted(subcategories)

    # --------------------------------------------------
    # Achievements
    # --------------------------------------------------

    def achievements(
        self,
        category: str,
        subcategory: str,
    ) -> list[dict]:

        self.load()

        results = []

        for achievement in self._data:

            if achievement["category"] != category:
                continue

            if achievement["subcategory"] != subcategory:
                continue

            achievement = achievement.copy()

            achievement["completed"] = (
                self.progress.is_complete(
                    achievement["id"]
                )
            )

            results.append(
                achievement
            )

        return results

    # --------------------------------------------------
    # Search
    # --------------------------------------------------

    def search(
        self,
        text: str,
    ) -> list[dict]:

        self.load()

        text = text.lower()

        results = []

        for achievement in self._data:

            if text not in achievement["name"].lower():
                continue

            achievement = achievement.copy()

            achievement["completed"] = (
                self.progress.is_complete(
                    achievement["id"]
                )
            )

            results.append(
                achievement
            )

        return results

    # --------------------------------------------------
    # Progress
    # --------------------------------------------------

    def completed_count(self) -> int:

        return self.progress.completed_count()

    def set_complete(
        self,
        achievement_id: str,
        complete: bool,
    ):

        self.progress.set_complete(
            achievement_id,
            complete,
        )