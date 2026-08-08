# ==================================================
# Black Feather Foundry
#
# File:
# importers/import_eso.py
#
# Purpose:
# Imports all ESO JSON data into the SQLite database.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from services.eso_database import EsoDatabase

# from importers.achievement_importer import AchievementImporter
from importers.collectible_importer import CollectibleImporter


class EsoImporter:
    """
    Imports all supported ESO data.
    """

    def __init__(
        self,
        raw_folder: Path,
        database: EsoDatabase,
    ):

        self.raw_folder = Path(raw_folder)

        self.database = database

    # --------------------------------------------------
    # Import
    # --------------------------------------------------

    def run(self):

        print("Importing ESO data...")

        # AchievementImporter(
        #     self.database
        # ).run(
        #     self.raw_folder
        #     / "all_achievements_raw.json",
        #     self.raw_folder
        #     / "eso_achievement_categories_raw.json",
            # self.raw_folder
            # / "eso_achievement_criteria_raw.json",
        # )

        CollectibleImporter(
            self.database
        ).run(
            self.raw_folder
            / "collectable_raw.json",
            # self.raw_folder
            # / "collectibleCategories.json",
        )

        self.database.commit()

        print("Import complete.")