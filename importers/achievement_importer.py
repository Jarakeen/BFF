# ==================================================
# Black Feather Foundry
#
# File:
# importers/achievement_importer.py
#
# Purpose:
# Imports ESO achievement data into SQLite.
#
# ==================================================

from __future__ import annotations

import json

from pathlib import Path

from services.eso_database import EsoDatabase


class AchievementImporter:
    """
    Imports achievement categories and achievements.
    """

    FILES = (
        "achievementCategories.json",
        "achievements.json",
    )

    def __init__(
        self,
        database: EsoDatabase,
    ):

        self.db = database

    # --------------------------------------------------
    # Import
    # --------------------------------------------------

    def run(
        self,
        raw_folder: Path,
    ):

        self._create_tables()

        self._import_categories(
            raw_folder / self.FILES[0]
        )

        self._import_achievements(
            raw_folder / self.FILES[1]
        )
        
    # --------------------------------------------------
    # Schema
    # --------------------------------------------------

    def _create_tables(self):

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS achievement_category (

                id          INTEGER PRIMARY KEY,
                parent_id   INTEGER,
                name        TEXT
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS achievement (

                id               INTEGER PRIMARY KEY,

                category_id      INTEGER,

                name             TEXT,

                description      TEXT,

                points           INTEGER,

                title            TEXT,

                collectible_id   INTEGER,

                dye_name         TEXT,

                dye_color        TEXT
            )
        """)
    # --------------------------------------------------
    # Categories
    # --------------------------------------------------

    def _import_categories(
            self,
            path: Path,
        ):

            rows = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )


            for row in rows:

                self.db.execute(
                    """
                    INSERT INTO achievement_category (
                        id,
                        parent_id,
                        name
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        row["id"],
                        row.get("parentCategoryId"),
                        row["name"],
                    ),
                )


    def _import_achievements(
        self,
        path: Path,
    ):

        rows = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )


        for row in rows:

            dye_name = row.get(
                "dyeName",
                ""
            ).strip()

            dye_color = row.get(
                "dyeColor",
                ""
            ).strip()

            #
            # Ignore default dye values.
            #

            if not dye_name or dye_color == "000000":

                dye_name = ""
                dye_color = ""

            self.db.execute(
                """
                INSERT INTO achievement (
                    id,
                    category_id,
                    name,
                    description,
                    points,
                    title,
                    collectible_id,
                    dye_name,
                    dye_color
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["categoryId"],
                    row["name"],
                    row.get("description", ""),
                    row.get("points", 0),
                    row.get("title", ""),
                    row.get("collectibleId"),
                    dye_name,
                    dye_color,
                ),
            )

        self.db.commit()