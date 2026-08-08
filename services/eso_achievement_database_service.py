# ==================================================
# Black Feather Foundry
#
# File:
# services/eso_achievement_database_service.py
#
# Purpose:
# Read-only access to ESO achievement data in SQLite.
#
# ==================================================

from __future__ import annotations

import sqlite3
from pathlib import Path


class EsoAchievementDatabaseService:
    """
    Read-only access to ESO achievement data stored in SQLite.

    Categories come from the current achievement category import.
    Achievements and criteria come from the achievement import.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self._connection: sqlite3.Connection | None = None

    # --------------------------------------------------
    # Connection
    # --------------------------------------------------

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.database_path
            )

            self._connection.row_factory = sqlite3.Row

        return self._connection

    # --------------------------------------------------
    # Categories
    # --------------------------------------------------

    def top_categories(self) -> list[str]:
        rows = self.connection.execute(
            """
            SELECT
                category_name,
                MIN(category_index) AS category_index
            FROM achievement_category
            WHERE category_name IS NOT NULL
              AND category_name != ''
            GROUP BY category_name
            ORDER BY category_index
            """
        ).fetchall()

        return [
            row["category_name"]
            for row in rows
        ]

    def subcategories(
        self,
        category: str,
    ) -> list[str]:

        rows = self.connection.execute(
            """
            SELECT
                subcategory_name,
                MIN(subcategory_index) AS subcategory_index
            FROM achievement_category
            WHERE category_name = ?
              AND subcategory_name IS NOT NULL
              AND subcategory_name != ''
            GROUP BY subcategory_name
            ORDER BY subcategory_index
            """,
            (category,),
        ).fetchall()

        return [
            row["subcategory_name"]
            for row in rows
        ]

    # --------------------------------------------------
    # Achievements
    # --------------------------------------------------

    def achievements_in(
        self,
        category: str,
        subcategory: str,
    ) -> list[dict]:

        rows = self.connection.execute(
            """
            SELECT
                a.id,
                a.name,
                a.description,
                a.points,
                a.icon,
                a.title,
                a.collectible_id,
                a.dye_name,
                a.dye_color,

                a.category_index,
                a.subcategory_index,
                a.achievement_index

            FROM achievement a

            INNER JOIN achievement_category c
                ON c.category_index = a.category_index
                AND c.subcategory_index = a.subcategory_index

            WHERE c.category_name = ?
              AND c.subcategory_name = ?

            ORDER BY
                a.achievement_index,
                a.id
            """,
            (
                category,
                subcategory,
            ),
        ).fetchall()
        print(
        "ACHIEVEMENTS:",
        [
            (row["id"], row["name"], row["points"])
            for row in rows[:5]
            ]
        )
        return [
            self._achievement_dict(row)
            for row in rows
        ]

    # --------------------------------------------------
    # Search
    # --------------------------------------------------

    def search(
        self,
        query: str,
    ) -> list[dict]:

        query = query.strip()

        if not query:
            return []

        pattern = f"%{query}%"

        rows = self.connection.execute(
            """
            SELECT
                a.id,
                a.name,
                a.description,
                a.points,
                a.icon,

                c.category_name,
                c.subcategory_name

            FROM achievement a

            LEFT JOIN achievement_category c
                ON c.category_index = a.category_index
                AND c.subcategory_index = a.subcategory_index

            WHERE
                a.name LIKE ?
                OR a.description LIKE ?

            GROUP BY a.id

            ORDER BY
                a.category_index,
                a.subcategory_index,
                a.achievement_index,
                a.id
            """,
            (
                pattern,
                pattern,
            ),
        ).fetchall()

        return [
            {
                "id": row["id"],
                "name": row["name"] or "",
                "desc": row["description"] or "",
                "points": row["points"] or 0,
                "category": row["category_name"] or "",
                "subcategory": row["subcategory_name"] or "",
            }
            for row in rows
        ]

    # --------------------------------------------------
    # Detail
    # --------------------------------------------------

    def achievement(
        self,
        achievement_id: int,
    ) -> dict | None:

        row = self.connection.execute(
            """
            SELECT *
            FROM achievement
            WHERE id = ?
            """,
            (achievement_id,),
        ).fetchone()

        if row is None:
            return None

        result = self._achievement_dict(row)

        criteria = self.connection.execute(
            """
            SELECT
                id,
                description,
                num_required,
                criteria_index

            FROM achievement_criterion

            WHERE achievement_id = ?

            ORDER BY criteria_index, id
            """,
            (achievement_id,),
        ).fetchall()

        result["criteria"] = [
            {
                "id": row["id"],
                "description": row["description"] or "",
                "numRequired": row["num_required"] or 0,
                "criteriaIndex": row["criteria_index"] or 0,
            }
            for row in criteria
        ]

        return result

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    def _achievement_dict(
        row: sqlite3.Row,
    ) -> dict:

        return {
            "id": row["id"],
            "name": row["name"] or "",
            "desc": row["description"] or "",
            "points": row["points"] or 0,
            "icon": row["icon"] or "",
            "title": row["title"] or "",
            "collectibleId": row["collectible_id"],
            "dyeName": row["dye_name"] or "",
            "dyeColor": row["dye_color"] or "",
        }

    # --------------------------------------------------
    # Cleanup
    # --------------------------------------------------

    def close(self) -> None:

        if self._connection is not None:
            self._connection.close()
            self._connection = None