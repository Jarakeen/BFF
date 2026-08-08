# ==================================================
# Black Feather Foundry
#
# File:
# importers/collectible_importer.py
#
# Purpose:
# Imports ESO collectible data into SQLite.
#
# ==================================================

from __future__ import annotations

import json

from pathlib import Path

from services.eso_database import EsoDatabase


class CollectibleImporter:
    """
    Imports collectible categories and collectibles.
    """

    FILES = (
        "collectibleCategories.json",
        "collectibles.json",
    )

    def __init__(self, database: EsoDatabase):

        self.db = database

    # --------------------------------------------------
    # Import
    # --------------------------------------------------

    def run(self, raw_folder: Path):

        self._create_tables()

        self._import_categories(
            raw_folder / self.FILES[0]
        )

        self._import_collectibles(
            raw_folder / self.FILES[1]
        )

    # --------------------------------------------------
    # Schema
    # --------------------------------------------------

    def _create_tables(self):

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS collectible_category (

                id          INTEGER PRIMARY KEY,
                parent_id   INTEGER,
                name        TEXT
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS collectible (

                id            INTEGER PRIMARY KEY,
                category_id   INTEGER,
                name          TEXT,
                description   TEXT,
                icon          TEXT
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

        self.db.execute(
            "DELETE FROM collectible_category"
        )

        for row in rows:

            self.db.execute(
                """
                INSERT INTO collectible_category
                VALUES (?, ?, ?)
                """,
                (
                    row["id"],
                    row.get("parentCategoryId"),
                    row["name"],
                ),
            )

    # --------------------------------------------------
    # Collectibles
    # --------------------------------------------------

    def _import_collectibles(
        self,
        path: Path,
    ):

        rows = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        self.db.execute(
            "DELETE FROM collectible"
        )

        for row in rows:

            self.db.execute(
                """
                INSERT INTO collectible
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["categoryId"],
                    row["name"],
                    row.get("description", ""),
                    row.get("icon", ""),
                ),
            )