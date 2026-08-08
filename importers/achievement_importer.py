# ==================================================
# Black Feather Foundry
#
# File:
# importers/achievement_importer.py
#
# Purpose:
# Imports ESO achievement data into SQLite.
#
# Source:
# all_achievement_raw.json
#
# ==================================================

from __future__ import annotations

import json
from pathlib import Path

from services.eso_database import EsoDatabase


class AchievementImporter:
    """
    Imports ESO achievement categories, achievements,
    and achievement criteria into SQLite.
    """

    RAW_FILE = "all_achievement_raw.json"
    CATEGORY_FILE = "eso_achievement_categories_raw.json"
    def __init__(self, database: EsoDatabase):
        self.db = database

    # --------------------------------------------------
    # Import
    # --------------------------------------------------

    def run(self, raw_folder: Path) -> None:
        raw_path = raw_folder / self.RAW_FILE
        category_path = raw_folder / self.CATEGORY_FILE

        if not raw_path.exists():
            raise FileNotFoundError(
                f"Achievement data file not found: {raw_path}"
            )

        if not category_path.exists():
            raise FileNotFoundError(
                f"Achievement category file not found: {category_path}"
            )

        print(f"Reading achievements: {raw_path}")
        print(f"Reading categories:  {category_path}")

        data = json.loads(
            raw_path.read_text(encoding="utf-8")
        )

        category_data = json.loads(
            category_path.read_text(encoding="utf-8")
        )

        achievements = data.get("achievements", [])
        criteria = data.get("achievementCriteria", [])
        categories = category_data.get(
            "achievementCategories", []
        )

        print(f"Achievements: {len(achievements)}")
        print(f"Criteria:     {len(criteria)}")
        print(f"Categories:   {len(categories)}")

    # --------------------------------------------------
    # Schema
    # --------------------------------------------------

    def _create_tables(self) -> None:

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS achievement_category (

                id                  INTEGER PRIMARY KEY,

                category_name       TEXT,
                subcategory_name    TEXT,

                category_index      INTEGER,
                subcategory_index   INTEGER,

                num_achievements    INTEGER,
                points              INTEGER,
                hides_points        INTEGER,

                icon                TEXT,
                pressed_icon        TEXT,
                mouseover_icon      TEXT,
                gamepad_icon        TEXT
            )
            """
        )

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS achievement (

                id                  INTEGER PRIMARY KEY,

                name                TEXT,
                description         TEXT,

                category_index      INTEGER,
                subcategory_index   INTEGER,
                achievement_index   INTEGER,

                points              INTEGER,
                icon                TEXT,
                num_rewards         INTEGER,

                item_link           TEXT,
                link                TEXT,

                title               TEXT,
                collectible_id      INTEGER,

                dye_id              INTEGER,
                dye_name            TEXT,
                dye_rarity          INTEGER,
                dye_hue              INTEGER,
                dye_color           TEXT,

                category_name       TEXT,

                first_id            INTEGER,
                prev_id             INTEGER,
                next_id             INTEGER
            )
            """
        )

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS achievement_criterion (

                id                  INTEGER PRIMARY KEY,

                achievement_id      INTEGER,
                description         TEXT,
                num_required       INTEGER,
                criteria_index      INTEGER
            )
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_achievement_criterion_achievement
            ON achievement_criterion(achievement_id)
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_achievement_category_index
            ON achievement(category_index, subcategory_index)
            """
        )

    # --------------------------------------------------
    # Categories
    # --------------------------------------------------

    def _import_categories(self, rows: list[dict]) -> int:

        sql = """
            INSERT INTO achievement_category (
                id,
                category_name,
                subcategory_name,
                category_index,
                subcategory_index,
                num_achievements,
                points,
                hides_points,
                icon,
                pressed_icon,
                mouseover_icon,
                gamepad_icon
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(id) DO UPDATE SET

                category_name = excluded.category_name,
                subcategory_name = excluded.subcategory_name,
                category_index = excluded.category_index,
                subcategory_index = excluded.subcategory_index,
                num_achievements = excluded.num_achievements,
                points = excluded.points,
                hides_points = excluded.hides_points,
                icon = excluded.icon,
                pressed_icon = excluded.pressed_icon,
                mouseover_icon = excluded.mouseover_icon,
                gamepad_icon = excluded.gamepad_icon
        """

        for row in rows:

            self.db.execute(
                sql,
                (
                    self._int(row.get("id")),

                    row.get("categoryName", ""),
                    row.get("subCategoryName", ""),

                    self._int(row.get("categoryIndex")),
                    self._int(row.get("subCategoryIndex")),

                    self._int(row.get("numAchievements"), 0),
                    self._int(row.get("points"), 0),
                    self._int(row.get("hidesPoints"), 0),

                    row.get("icon", ""),
                    row.get("pressedIcon", ""),
                    row.get("mouseoverIcon", ""),
                    row.get("gamepadIcon", ""),
                ),
            )

        return len(rows)

    # --------------------------------------------------
    # Achievements
    # --------------------------------------------------

    def _import_achievements(self, rows: list[dict]) -> int:

        sql = """
            INSERT INTO achievement (
                id,
                name,
                description,

                category_index,
                subcategory_index,
                achievement_index,

                points,
                icon,
                num_rewards,

                item_link,
                link,

                title,
                collectible_id,

                dye_id,
                dye_name,
                dye_rarity,
                dye_hue,
                dye_color,

                category_name,

                first_id,
                prev_id,
                next_id
            )
            VALUES (
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?, ?,
                ?,
                ?, ?, ?
            )
            ON CONFLICT(id) DO UPDATE SET

                name = excluded.name,
                description = excluded.description,

                category_index = excluded.category_index,
                subcategory_index = excluded.subcategory_index,
                achievement_index = excluded.achievement_index,

                points = excluded.points,
                icon = excluded.icon,
                num_rewards = excluded.num_rewards,

                item_link = excluded.item_link,
                link = excluded.link,

                title = excluded.title,
                collectible_id = excluded.collectible_id,

                dye_id = excluded.dye_id,
                dye_name = excluded.dye_name,
                dye_rarity = excluded.dye_rarity,
                dye_hue = excluded.dye_hue,
                dye_color = excluded.dye_color,

                category_name = excluded.category_name,

                first_id = excluded.first_id,
                prev_id = excluded.prev_id,
                next_id = excluded.next_id
        """

        for row in rows:

            self.db.execute(
                sql,
                (
                    self._int(row.get("id")),

                    row.get("name", ""),
                    row.get("description", ""),

                    self._int(row.get("categoryIndex")),
                    self._int(row.get("subCategoryIndex")),
                    self._int(row.get("achievementIndex")),

                    self._int(row.get("points"), 0),
                    row.get("icon", ""),
                    self._int(row.get("numRewards"), 0),

                    row.get("itemLink", ""),
                    row.get("link", ""),

                    row.get("title", ""),
                    self._int(row.get("collectibleId"), 0),

                    self._int(row.get("dyeId"), 0),
                    row.get("dyeName", ""),
                    self._int(row.get("dyeRarity"), -1),
                    self._int(row.get("dyeHue"), -1),
                    row.get("dyeColor", ""),

                    row.get("categoryName", ""),

                    self._int(row.get("firstId"), 0),
                    self._int(row.get("prevId"), 0),
                    self._int(row.get("nextId"), 0),
                ),
            )

        return len(rows)

    # --------------------------------------------------
    # Criteria
    # --------------------------------------------------

    def _import_criteria(self, rows: list[dict]) -> int:

        sql = """
            INSERT INTO achievement_criterion (
                id,
                achievement_id,
                description,
                num_required,
                criteria_index
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(id) DO UPDATE SET

                achievement_id = excluded.achievement_id,
                description = excluded.description,
                num_required = excluded.num_required,
                criteria_index = excluded.criteria_index
        """

        for row in rows:

            self.db.execute(
                sql,
                (
                    self._int(row.get("id")),

                    self._int(
                        row.get("achievementId")
                    ),

                    row.get("description", ""),

                    self._int(
                        row.get("numRequired"),
                        0
                    ),

                    self._int(
                        row.get("criteriaIndex"),
                        0
                    ),
                ),
            )

        return len(rows)

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    def _int(value, default=None):

        if value is None:
            return default

        if isinstance(value, int):
            return value

        try:
            return int(value)

        except (TypeError, ValueError):
            return default


# ==================================================
# Command-line entry point
# ==================================================

if __name__ == "__main__":

    project_root = Path(__file__).resolve().parents[1]

    raw_folder = project_root / "data" / "raw"
    database_path = project_root / "data" / "eso.db"

    print("==========================================")
    print(" Black Feather Foundry")
    print(" ESO Achievement Importer")
    print("==========================================")
    print()

    print(f"Raw data folder: {raw_folder}")
    print(f"Database:        {database_path}")
    print()

    if not raw_folder.exists():
        raise FileNotFoundError(
            f"Raw data folder does not exist: {raw_folder}"
        )

    raw_file = raw_folder / AchievementImporter.RAW_FILE
    category_file = raw_folder / AchievementImporter.CATEGORY_FILE

    if not raw_file.exists():
        raise FileNotFoundError(
            f"Required file not found: {raw_file}"
        )

    if not category_file.exists():
        raise FileNotFoundError(
            f"Required file not found: {category_file}"
    )

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    db = EsoDatabase(database_path)

    try:

        importer = AchievementImporter(db)

        importer.run(raw_folder)

    finally:

        db.close()