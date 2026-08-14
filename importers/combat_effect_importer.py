from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]

DATABASE_FILE = (
    ROOT
    / "data"
    / "eso.db"
)

# The importer accepts either spelling so we don't have to fight
# Windows filenames for sport.
SOURCE_CANDIDATES = [
    ROOT / "data" / "raw" / "combat effects.md",
    ROOT / "data" / "raw" / "combat_effects.md",
]


class CombatEffectImporter:

    def __init__(
        self,
        database_path: Path = DATABASE_FILE,
        source_file: Optional[Path] = None,
    ):
        self.database_path = Path(
            database_path
        )

        self.source_file = (
            Path(source_file)
            if source_file
            else self._find_source_file()
        )

    # ==================================================
    # RUN
    # ==================================================

    def run(self):

        print()
        print("=========================================")
        print(" Black Feather Foundry")
        print(" ESO Combat Effects Importer")
        print("=========================================")
        print()

        print(
            f"Source:   {self.source_file}"
        )

        print(
            f"Database: {self.database_path}"
        )

        print()

        if not self.source_file.exists():

            raise FileNotFoundError(
                "Combat effects source file not found.\n\n"
                "Expected one of:\n"
                + "\n".join(
                    f"  {path}"
                    for path in SOURCE_CANDIDATES
                )
            )

        text = self.source_file.read_text(
            encoding="utf-8"
        )

        db = sqlite3.connect(
            self.database_path
        )

        try:

            self._create_tables(db)

            self._clear_tables(db)

            effects = (
                self._build_effects()
            )

            effect_ids = {}

            for effect in effects:

                effect_id = (
                    self._insert_effect(
                        db,
                        effect,
                    )
                )

                effect_ids[
                    effect["name"]
                ] = effect_id

            self._insert_triggers(
                db,
                effect_ids,
            )

            self._insert_interactions(
                db,
                effect_ids,
            )

            db.commit()

            self._report(
                db
            )

        except Exception:

            db.rollback()
            raise

        finally:

            db.close()

    # ==================================================
    # SOURCE FILE
    # ==================================================

    def _find_source_file(
        self,
    ) -> Path:

        for path in SOURCE_CANDIDATES:

            if path.exists():

                return path

        return SOURCE_CANDIDATES[0]

    # ==================================================
    # TABLES
    # ==================================================

    def _create_tables(
        self,
        db: sqlite3.Connection,
    ):

        # ------------------------------------------
        # Canonical combat effect
        # ------------------------------------------

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS
            combat_effect (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL UNIQUE,

                category TEXT NOT NULL,

                description TEXT,

                duration REAL,

                tick_interval REAL,

                stack_max INTEGER,

                immunity_duration REAL,

                raw_source TEXT
            )
            """
        )

        # ------------------------------------------
        # How an effect is triggered
        # ------------------------------------------

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS
            combat_effect_trigger (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                combat_effect_id INTEGER NOT NULL,

                trigger_type TEXT NOT NULL,

                damage_type TEXT,

                weapon_requirement TEXT,

                condition TEXT,

                raw_source TEXT,

                FOREIGN KEY (
                    combat_effect_id
                )
                REFERENCES combat_effect(id)
                ON DELETE CASCADE
            )
            """
        )

        # ------------------------------------------
        # What an effect causes/enables
        # ------------------------------------------

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS
            combat_effect_interaction (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                source_effect_id INTEGER NOT NULL,

                target_name TEXT NOT NULL,

                interaction_type TEXT NOT NULL,

                condition TEXT,

                duration REAL,

                target_value REAL,

                target_unit TEXT,

                target_scope TEXT,

                raw_source TEXT,

                FOREIGN KEY (
                    source_effect_id
                )
                REFERENCES combat_effect(id)
                ON DELETE CASCADE
            )
            """
        )

        db.commit()

    # ==================================================
    # CLEAR
    # ==================================================

    def _clear_tables(
        self,
        db: sqlite3.Connection,
    ):

        db.execute(
            """
            DELETE FROM
            combat_effect_interaction
            """
        )

        db.execute(
            """
            DELETE FROM
            combat_effect_trigger
            """
        )

        db.execute(
            """
            DELETE FROM
            combat_effect
            """
        )

        db.commit()

    # ==================================================
    # EFFECT DEFINITIONS
    # ==================================================

    def _build_effects(self):

        return [

            # ------------------------------------------
            # STATUS EFFECTS
            # ------------------------------------------

            {
                "name": "Burning",
                "category": "Status",
                "description": (
                    "The Burning status can be applied "
                    "by dealing Flame Damage to a target. "
                    "The target takes flame damage over time "
                    "based on Max Magicka and Spell Damage."
                ),
                "duration": 4,
                "tick_interval": 2,
                "stack_max": None,
                "immunity_duration": None,
            },

            {
                "name": "Chilled",
                "category": "Status",
                "description": (
                    "The Chilled status can be applied "
                    "by dealing Frost Damage to a target. "
                    "A Chilled enemy takes instant frost "
                    "damage and suffers from Minor Maim."
                ),
                "duration": 4,
                "tick_interval": None,
                "stack_max": None,
                "immunity_duration": None,
            },

            {
                "name": "Concussion",
                "category": "Status",
                "description": (
                    "The Concussion status can be applied "
                    "by dealing Shock Damage to a target. "
                    "A Concussed enemy takes instant shock "
                    "damage and suffers from Minor Vulnerability."
                ),
                "duration": 4,
                "tick_interval": None,
                "stack_max": None,
                "immunity_duration": None,
            },

            {
                "name": "Poisoned",
                "category": "Status",
                "description": (
                    "The Poisoned status can be applied "
                    "by dealing Poison Damage to a target. "
                    "The target takes Poison damage over time."
                ),
                "duration": 4,
                "tick_interval": 2,
                "stack_max": None,
                "immunity_duration": None,
            },

            {
                "name": "Diseased",
                "category": "Status",
                "description": (
                    "The Diseased status can be applied "
                    "by dealing Disease Damage to a target. "
                    "The target takes direct Disease damage "
                    "and suffers from Minor Defile."
                ),
                "duration": 4,
                "tick_interval": None,
                "stack_max": None,
                "immunity_duration": None,
            },

            {
                "name": "Hemorrhaging",
                "category": "Status",
                "description": (
                    "The Hemorrhaging status can be applied "
                    "by dealing Bleed Damage to a target. "
                    "The effect stacks up to 3 times."
                ),
                "duration": 4,
                "tick_interval": 2,
                "stack_max": 3,
                "immunity_duration": None,
            },

            {
                "name": "Sundered",
                "category": "Status",
                "description": (
                    "The Sundered status can be applied "
                    "by dealing Physical Damage to a target. "
                    "The target suffers from Minor Breach."
                ),
                "duration": 4,
                "tick_interval": None,
                "stack_max": None,
                "immunity_duration": None,
            },

            {
                "name": "Overcharged",
                "category": "Status",
                "description": (
                    "The Overcharged status can be applied "
                    "by dealing Magic Damage to a target. "
                    "The target suffers from Minor Magickasteal."
                ),
                "duration": 4,
                "tick_interval": None,
                "stack_max": None,
                "immunity_duration": None,
            },

            # ------------------------------------------
            # COMBAT EFFECT
            # ------------------------------------------

            {
                "name": "Off Balance",
                "category": "Combat",
                "description": (
                    "A debilitating combat effect that "
                    "stuns the target and makes it vulnerable "
                    "to effects against Off Balance. "
                    "Heavy Attacks against an Off Balance "
                    "target receive increased damage and "
                    "resource restoration."
                ),
                "duration": 7,
                "tick_interval": None,
                "stack_max": None,
                "immunity_duration": 15,
            },

            # ------------------------------------------
            # OTHER EFFECTS
            # ------------------------------------------

            {
                "name": "Hindered",
                "category": "Other",
                "description": (
                    "Healing missing health is prevented "
                    "for 12 seconds or until the specified "
                    "amount of healing is received."
                ),
                "duration": 12,
                "tick_interval": None,
                "stack_max": None,
                "immunity_duration": None,
            },

            {
                "name": "Rattled",
                "category": "Other",
                "description": (
                    "The target is shaken up for 12 seconds, "
                    "reducing damage done and increasing "
                    "damage taken."
                ),
                "duration": 12,
                "tick_interval": None,
                "stack_max": None,
                "immunity_duration": None,
            },

            {
                "name": "Devitalized",
                "category": "Other",
                "description": (
                    "The target is weakened for 8 seconds, "
                    "reducing Physical and Spell Resistance, "
                    "reducing damage shields, and increasing "
                    "damage taken."
                ),
                "duration": 8,
                "tick_interval": None,
                "stack_max": None,
                "immunity_duration": None,
            },
        ]

    # ==================================================
    # INSERT EFFECT
    # ==================================================

    def _insert_effect(
        self,
        db: sqlite3.Connection,
        effect: dict,
    ) -> int:

        cursor = db.execute(
            """
            INSERT INTO combat_effect (
                name,
                category,
                description,
                duration,
                tick_interval,
                stack_max,
                immunity_duration,
                raw_source
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                effect["name"],
                effect["category"],
                effect["description"],
                effect["duration"],
                effect["tick_interval"],
                effect["stack_max"],
                effect["immunity_duration"],
                str(effect),
            ),
        )

        return int(
            cursor.lastrowid
        )

    # ==================================================
    # TRIGGERS
    # ==================================================

    def _insert_triggers(
        self,
        db: sqlite3.Connection,
        effect_ids: dict,
    ):

        triggers = [

            # ------------------------------------------
            # Burning
            # ------------------------------------------

            (
                "Burning",
                "Damage",
                "Flame",
                None,
                None,
            ),

            # ------------------------------------------
            # Chilled
            # ------------------------------------------

            (
                "Chilled",
                "Damage",
                "Frost",
                None,
                None,
            ),

            # ------------------------------------------
            # Concussion
            # ------------------------------------------

            (
                "Concussion",
                "Damage",
                "Shock",
                None,
                None,
            ),

            # ------------------------------------------
            # Poisoned
            # ------------------------------------------

            (
                "Poisoned",
                "Damage",
                "Poison",
                None,
                None,
            ),

            # ------------------------------------------
            # Diseased
            # ------------------------------------------

            (
                "Diseased",
                "Damage",
                "Disease",
                None,
                None,
            ),

            # ------------------------------------------
            # Hemorrhaging
            # ------------------------------------------

            (
                "Hemorrhaging",
                "Damage",
                "Bleed",
                None,
                None,
            ),

            # ------------------------------------------
            # Sundered
            # ------------------------------------------

            (
                "Sundered",
                "Damage",
                "Physical",
                None,
                None,
            ),

            # ------------------------------------------
            # Overcharged
            # ------------------------------------------

            (
                "Overcharged",
                "Damage",
                "Magic",
                None,
                None,
            ),
        ]

        for (
            effect_name,
            trigger_type,
            damage_type,
            weapon_requirement,
            condition,
        ) in triggers:

            db.execute(
                """
                INSERT INTO
                combat_effect_trigger (
                    combat_effect_id,
                    trigger_type,
                    damage_type,
                    weapon_requirement,
                    condition,
                    raw_source
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    effect_ids[
                        effect_name
                    ],
                    trigger_type,
                    damage_type,
                    weapon_requirement,
                    condition,
                    "ESO Wiki combat effects",
                ),
            )

    # ==================================================
    # INTERACTIONS
    # ==================================================

    def _insert_interactions(
        self,
        db: sqlite3.Connection,
        effect_ids: dict,
    ):

        interactions = [

            # ------------------------------------------
            # Chilled
            # ------------------------------------------

            {
                "source": "Chilled",
                "target": "Minor Maim",
                "interaction": "Applies",
                "condition": None,
                "duration": 4,
                "value": 5,
                "unit": "percent",
                "scope": "Target",
            },

            {
                "source": "Chilled",
                "target": "Minor Brittle",
                "interaction": "Applies",
                "condition": (
                    "Ice Staff active weapon"
                ),
                "duration": None,
                "value": 10,
                "unit": "percent",
                "scope": "Target",
            },

            # ------------------------------------------
            # Concussion
            # ------------------------------------------

            {
                "source": "Concussion",
                "target": "Minor Vulnerability",
                "interaction": "Applies",
                "condition": None,
                "duration": 4,
                "value": 5,
                "unit": "percent",
                "scope": "Target",
            },

            # ------------------------------------------
            # Diseased
            # ------------------------------------------

            {
                "source": "Diseased",
                "target": "Minor Defile",
                "interaction": "Applies",
                "condition": None,
                "duration": 4,
                "value": 6,
                "unit": "percent",
                "scope": "Target",
            },

            # ------------------------------------------
            # Sundered
            # ------------------------------------------

            {
                "source": "Sundered",
                "target": "Minor Breach",
                "interaction": "Applies",
                "condition": None,
                "duration": 4,
                "value": 2974,
                "unit": "resistance",
                "scope": "Target",
            },

            {
                "source": "Sundered",
                "target": "Weapon and Spell Damage",
                "interaction": "Grants",
                "condition": None,
                "duration": 4,
                "value": 100,
                "unit": "flat",
                "scope": "Caster",
            },

            # ------------------------------------------
            # Overcharged
            # ------------------------------------------

            {
                "source": "Overcharged",
                "target": "Minor Magickasteal",
                "interaction": "Applies",
                "condition": None,
                "duration": 4,
                "value": 168,
                "unit": "magicka_per_second",
                "scope": "Players damaging target",
            },

            # ------------------------------------------
            # Off Balance
            # ------------------------------------------

            {
                "source": "Off Balance",
                "target": "Heavy Attack",
                "interaction": "Empowers",
                "condition": None,
                "duration": None,
                "value": 70,
                "unit": "percent",
                "scope": "Attacker",
            },
        ]

        for interaction in interactions:

            db.execute(
                """
                INSERT INTO
                combat_effect_interaction (
                    source_effect_id,
                    target_name,
                    interaction_type,
                    condition,
                    duration,
                    target_value,
                    target_unit,
                    target_scope,
                    raw_source
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    effect_ids[
                        interaction["source"]
                    ],
                    interaction["target"],
                    interaction["interaction"],
                    interaction["condition"],
                    interaction["duration"],
                    interaction["value"],
                    interaction["unit"],
                    interaction["scope"],
                    "ESO Wiki combat effects",
                ),
            )

    # ==================================================
    # REPORT
    # ==================================================

    def _report(
        self,
        db: sqlite3.Connection,
    ):

        effects = db.execute(
            """
            SELECT
                category,
                COUNT(*)
            FROM combat_effect
            GROUP BY category
            ORDER BY category
            """
        ).fetchall()

        trigger_count = db.execute(
            """
            SELECT COUNT(*)
            FROM combat_effect_trigger
            """
        ).fetchone()[0]

        interaction_count = db.execute(
            """
            SELECT COUNT(*)
            FROM combat_effect_interaction
            """
        ).fetchone()[0]

        print()
        print("## Combat Effects Import Complete")
        print()

        for category, count in effects:

            print(
                f"{category + ' effects:':20}"
                f"{count}"
            )

        print(
            f"{'Triggers:':20}"
            f"{trigger_count}"
        )

        print(
            f"{'Interactions:':20}"
            f"{interaction_count}"
        )

        print()

        print(
            "Combat effects:"
        )

        rows = db.execute(
            """
            SELECT
                id,
                name,
                category,
                duration,
                immunity_duration
            FROM combat_effect
            ORDER BY category, name
            """
        ).fetchall()

        for row in rows:

            print(
                f"{row[0]:3} | "
                f"{row[1]:20} | "
                f"{row[2]:8} | "
                f"duration={row[3]} | "
                f"immunity={row[4]}"
            )

        print()


def main():

    importer = (
        CombatEffectImporter()
    )

    importer.run()


if __name__ == "__main__":
    main()