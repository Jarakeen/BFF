# ==================================================
# Black Feather Foundry
#
# File:
# importers/gear_set_importer.py
#
# Purpose:
# Imports canonical ESO gear-set data into SQLite.
#
# ==================================================

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

from services.eso_database import EsoDatabase
from parsers.gear_set_parser import GearSetParser

class GearSetImporter:
    """
    Imports canonical ESO gear-set data into SQLite.

    The parser handles:
        - grouping raw items by setId
        - set classification
        - set bonuses
        - available equipment pieces
        - source item IDs

    This importer handles:
        - SQLite schema
        - inserting/updating sets
        - inserting/updating bonuses
        - inserting/updating pieces
        - inserting/updating item relationships
    """

    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------

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
    ) -> None:

        raw_file = (
            raw_folder
            / "gear_sets_raw.json"
        )

        if not raw_file.exists():
            raise FileNotFoundError(
                f"Gear item data file not found: "
                f"{raw_file}"
            )

        print(
            f"Reading gear items: {raw_file}"
        )

        parser = GearSetParser(
            raw_file=raw_file,
            output_file=(
                raw_folder
                / "gear_sets_debug.json"
            ),
        )

        sets = parser.parse()

        print(
            f"Canonical gear sets: "
            f"{len(sets)}"
        )

        self._create_tables()

        set_count = self._import_sets(
            sets
        )

        bonus_count = self._import_bonuses(
            sets
        )

        piece_count = self._import_pieces(
            sets
        )

        item_count = self._import_items(
            sets
        )

        self.db.commit()

        print()
        print(
            "Gear Set Import Complete"
        )
        print(
            f"Sets:        {set_count}"
        )
        print(
            f"Bonuses:     {bonus_count}"
        )
        print(
            f"Pieces:      {piece_count}"
        )
        print(
            f"Items:       {item_count}"
        )

    # --------------------------------------------------
    # Schema
    # --------------------------------------------------

    def _create_tables(self) -> None:

        #
        # Gear Sets
        #

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS gear_set (

                id                  INTEGER PRIMARY KEY,

                name                TEXT NOT NULL,

                category            TEXT,

                max_equip_count     INTEGER
            )
            """
        )

        #
        # Set Bonuses
        #

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS gear_set_bonus (

                id                  INTEGER PRIMARY KEY AUTOINCREMENT,

                set_id              INTEGER NOT NULL,

                piece_count         INTEGER NOT NULL,

                description         TEXT,

                UNIQUE(
                    set_id,
                    piece_count
                ),

                FOREIGN KEY(set_id)
                    REFERENCES gear_set(id)
                    ON DELETE CASCADE
            )
            """
        )

        #
        # Set Pieces
        #

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS gear_set_piece (

                id                  INTEGER PRIMARY KEY AUTOINCREMENT,

                set_id              INTEGER NOT NULL,

                equip_type          INTEGER,

                armor_type          INTEGER,

                weapon_type         INTEGER,

                UNIQUE(
                    set_id,
                    equip_type,
                    armor_type,
                    weapon_type
                ),

                FOREIGN KEY(set_id)
                    REFERENCES gear_set(id)
                    ON DELETE CASCADE
            )
            """
        )

        #
        # Source Items
        #

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS gear_set_item (

                set_id              INTEGER NOT NULL,

                item_id             INTEGER NOT NULL,

                PRIMARY KEY(
                    set_id,
                    item_id
                ),

                FOREIGN KEY(set_id)
                    REFERENCES gear_set(id)
                    ON DELETE CASCADE
            )
            """
        )

        #
        # Indexes
        #

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_gear_set_bonus_set
            ON gear_set_bonus(set_id)
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_gear_set_piece_set
            ON gear_set_piece(set_id)
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_gear_set_item_set
            ON gear_set_item(set_id)
            """
        )

    # --------------------------------------------------
    # Sets
    # --------------------------------------------------

    def _import_sets(
        self,
        sets: dict[str, dict],
    ) -> int:

        sql = """
            INSERT INTO gear_set (
                id,
                name,
                category,
                max_equip_count
            )

            VALUES (
                ?, ?, ?, ?
            )

            ON CONFLICT(id) DO UPDATE SET

                name = excluded.name,

                category = excluded.category,

                max_equip_count =
                    excluded.max_equip_count
        """

        count = 0

        for record in sets.values():

            self.db.execute(
                sql,
                (
                    self._int(
                        record.get("id")
                    ),

                    record.get(
                        "name",
                        "",
                    ),

                    record.get(
                        "category",
                        "standard",
                    ),

                    self._int(
                        record.get(
                            "max_equip_count"
                        )
                    ),
                ),
            )

            count += 1

        return count

    # --------------------------------------------------
    # Bonuses
    # --------------------------------------------------

    def _import_bonuses(
        self,
        sets: dict[str, dict],
    ) -> int:

        sql = """
            INSERT INTO gear_set_bonus (
                set_id,
                piece_count,
                description
            )

            VALUES (
                ?, ?, ?
            )

            ON CONFLICT(
                set_id,
                piece_count
            )

            DO UPDATE SET

                description =
                    excluded.description
        """

        count = 0

        for record in sets.values():

            set_id = self._int(
                record.get("id")
            )

            bonuses = record.get(
                "bonuses",
                {},
            )

            for piece_count, description in (
                bonuses.items()
            ):

                self.db.execute(
                    sql,
                    (
                        set_id,

                        self._int(
                            piece_count
                        ),

                        description,
                    ),
                )

                count += 1

        return count

    # --------------------------------------------------
    # Pieces
    # --------------------------------------------------

    def _import_pieces(
        self,
        sets: dict[str, dict],
    ) -> int:

        sql = """
            INSERT OR IGNORE INTO
            gear_set_piece (
                set_id,
                equip_type,
                armor_type,
                weapon_type
            )

            VALUES (
                ?, ?, ?, ?
            )
        """

        count = 0

        for record in sets.values():

            set_id = self._int(
                record.get("id")
            )

            pieces = record.get(
                "pieces",
                {},
            )

            items = pieces.get(
                "items",
                [],
            )

            for item in items:

                self.db.execute(
                    sql,
                    (
                        set_id,

                        self._int(
                            item.get(
                                "equip_type"
                            )
                        ),

                        self._int(
                            item.get(
                                "armor_type"
                            )
                        ),

                        self._int(
                            item.get(
                                "weapon_type"
                            )
                        ),
                    ),
                )

                count += 1

        return count

    # --------------------------------------------------
    # Source Items
    # --------------------------------------------------

    def _import_items(
        self,
        sets: dict[str, dict],
    ) -> int:

        sql = """
            INSERT OR IGNORE INTO
            gear_set_item (
                set_id,
                item_id
            )

            VALUES (
                ?, ?
            )
        """

        count = 0

        for record in sets.values():

            set_id = self._int(
                record.get("id")
            )

            item_ids = record.get(
                "source_item_ids",
                [],
            )

            for item_id in item_ids:

                self.db.execute(
                    sql,
                    (
                        set_id,
                        self._int(
                            item_id
                        ),
                    ),
                )

                count += 1

        return count

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    def _int(
        value,
        default=None,
    ):

        if value is None:
            return default

        if isinstance(
            value,
            int,
        ):
            return value

        try:

            return int(value)

        except (
            TypeError,
            ValueError,
        ):

            return default


# ==================================================
# Command-line entry point
# ==================================================

if __name__ == "__main__":

    project_root = (
        Path(__file__)
        .resolve()
        .parents[1]
    )

    raw_folder = (
        project_root
        / "data"
        / "raw"
    )

    database_path = (
        project_root
        / "data"
        / "eso.db"
    )

    print(
        "=========================================="
    )

    print(
        " Black Feather Foundry"
    )

    print(
        " ESO Gear Set Importer"
    )

    print(
        "=========================================="
    )

    print()

    print(
        f"Raw data folder: {raw_folder}"
    )

    print(
        f"Database:        {database_path}"
    )

    print()

    if not raw_folder.exists():

        raise FileNotFoundError(
            f"Raw data folder does not exist: "
            f"{raw_folder}"
        )

    raw_file = (
        raw_folder
        / "gear_sets_raw.json"
    )

    if not raw_file.exists():

        raise FileNotFoundError(
            f"Required file not found: "
            f"{raw_file}"
        )

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    db = EsoDatabase(
        database_path
    )

    try:

        importer = GearSetImporter(
            db
        )

        importer.run(
            raw_folder
        )

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()