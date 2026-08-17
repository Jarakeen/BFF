# ==================================================
# Black Feather Foundry
#
# File:
# services/achievement_stats_service.py
#
# Purpose:
# Combines the read-only ESO achievement database
# with local progress tracking to produce the
# summary numbers shown on the Achievement Desk
# (points earned, category/dungeon/trial progress).
#
# ==================================================

from __future__ import annotations


class AchievementStatsService:
    """
    Read-only summary statistics for the Achievement Desk.

    Achievement/point data comes from EsoAchievementDatabaseService
    (the read-only game database). Completion comes from
    AchievementProgressService (the local progress file).
    """

    def __init__(
        self,
        database_service,
        progress_service,
    ):

        self.database_service = database_service

        self.progress_service = progress_service

        self._rows = None

    # --------------------------------------------------
    # Loading
    # --------------------------------------------------

    def _load(self) -> list[dict]:

        if self._rows is None:

            self._rows = (
                self.database_service.all_achievement_points()
            )

        return self._rows

    def refresh(self):
        """
        Drop the cached rows and completion state so the
        next call picks up any new progress.
        """

        self._rows = None

    # --------------------------------------------------
    # Categories
    # --------------------------------------------------

    def top_categories(self) -> list[str]:

        return self.database_service.top_categories()

    # --------------------------------------------------
    # Summaries
    # --------------------------------------------------

    def overall(self) -> dict:
        """
        Points/count earned and possible across every
        achievement in the database.
        """

        return self._summarize(
            self._load()
        )

    def category(
        self,
        category_name: str,
    ) -> dict:
        """
        Points/count earned and possible within a single
        top-level category (e.g. "Dungeons", "Trials").
        """

        rows = [
            row
            for row in self._load()
            if row["category"] == category_name
        ]

        return self._summarize(rows)

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _summarize(
        self,
        rows: list[dict],
    ) -> dict:

        points_total = sum(
            row["points"]
            for row in rows
        )

        count_total = len(rows)

        earned_rows = [
            row
            for row in rows
            if self.progress_service.is_complete(
                row["id"]
            )
        ]

        points_earned = sum(
            row["points"]
            for row in earned_rows
        )

        count_earned = len(earned_rows)

        return {
            "points_earned": points_earned,
            "points_total": points_total,
            "count_earned": count_earned,
            "count_total": count_total,
        }
