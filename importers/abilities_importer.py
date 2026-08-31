from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

RAW_FILE = (
    ROOT
    / "data"
    / "raw"
    / "skills_raw.json"
)

DATABASE_FILE = (
    ROOT
    / "data"
    / "eso.db"
)


class AbilitiesImporter:

    def __init__(
        self,
        database_path: Path = DATABASE_FILE,
        raw_file: Path = RAW_FILE,
    ):
        self.database_path = Path(
            database_path
        )

        self.raw_file = Path(
            raw_file
        )

    # ======================================================
    # RUN
    # ======================================================

    def run(self):

        print()
        print("=========================================")
        print(" Black Feather Foundry")
        print(" ESO Ability Importer")
        print("=========================================")
        print()

        print(
            f"Raw data:  {self.raw_file}"
        )

        print(
            f"Database:  {self.database_path}"
        )

        print()

        records = self._load_records()

        print(
            f"Raw ability records: {len(records):,}"
        )

        print()

        db = sqlite3.connect(
            self.database_path
        )

        try:

            self._create_table(db)
            self._ensure_phase4_cost_timing_columns(db)
            self._verify_schema(db)
            db.execute(
                "DELETE FROM ability"
            )

            imported = 0

            for record in records:

                self._insert_ability(
                    db,
                    record,
                )

                imported += 1

            db.commit()

            self._report(
                db,
                imported,
            )

        except Exception:

            db.rollback()
            raise

        finally:

            db.close()

    # ======================================================
    # LOAD
    # ======================================================

    def _load_records(self) -> list[dict[str, Any]]:

        if not self.raw_file.exists():

            raise FileNotFoundError(
                f"Raw file not found:\n"
                f"{self.raw_file}"
            )

        with self.raw_file.open(
            "r",
            encoding="utf-8-sig",
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):

            records = data.get(
                "playerSkills"
            )

            if not isinstance(
                records,
                list,
            ):
                raise ValueError(
                    "Expected playerSkills list"
                )

            return records

        if isinstance(data, list):

            return data

        raise ValueError(
            "Unsupported skills JSON structure"
        )

    # ======================================================
    # TABLE
    # ======================================================

    def _create_table(
        self,
        db: sqlite3.Connection,
    ):

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS ability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                ability_id INTEGER NOT NULL UNIQUE,
                display_id INTEGER,

                name TEXT,
                index_name TEXT,
                description TEXT,
                texture TEXT,

                target TEXT,
                skill_type INTEGER,

                duration REAL,
                start_time REAL,
                tick_time REAL,
                cooldown REAL,

                cost REAL,
                cost_time REAL,
                base_cost REAL,
                base_mechanic INTEGER,
                base_is_cost_time INTEGER DEFAULT 0,
                charge_freq_raw TEXT,

                charge_freq REAL,

                min_range REAL,
                max_range REAL,
                radius REAL,

                is_passive INTEGER DEFAULT 0,
                is_channeled INTEGER DEFAULT 0,
                is_permanent INTEGER DEFAULT 0,

                is_crafted INTEGER DEFAULT 0,
                crafted_id INTEGER,

                cast_time REAL,
                channel_time REAL,
                angle_distance REAL,

                mechanic INTEGER,
                mechanic_time REAL,

                is_player INTEGER DEFAULT 0,

                race_type TEXT,
                class_type TEXT,
                skill_line TEXT,

                base_ability_id INTEGER,

                learned_level INTEGER,
                rank INTEGER,
                morph INTEGER,
                skill_index INTEGER,

                buff_type INTEGER,
                is_toggle INTEGER DEFAULT 0,

                num_coef_vars INTEGER,
                coef_description TEXT,

                type1 INTEGER,
                a1 REAL,
                b1 REAL,
                c1 REAL,
                r1 REAL,
                avg1 REAL,

                type2 INTEGER,
                a2 REAL,
                b2 REAL,
                c2 REAL,
                r2 REAL,
                avg2 REAL,

                type3 INTEGER,
                a3 REAL,
                b3 REAL,
                c3 REAL,
                r3 REAL,
                avg3 REAL,

                type4 INTEGER,
                a4 REAL,
                b4 REAL,
                c4 REAL,
                r4 REAL,
                avg4 REAL,

                type5 INTEGER,
                a5 REAL,
                b5 REAL,
                c5 REAL,
                r5 REAL,
                avg5 REAL,

                type6 INTEGER,
                a6 REAL,
                b6 REAL,
                c6 REAL,
                r6 REAL,
                avg6 REAL,

                raw_description TEXT,
                raw_name TEXT,
                raw_tooltip TEXT,
                raw_coef TEXT,
                coef_types TEXT,

                is_mastery INTEGER DEFAULT 0,

                raw_json TEXT
            )
            """
        )

    @staticmethod
    def _ensure_phase4_cost_timing_columns(db: sqlite3.Connection) -> None:
        """Add Phase 4 timing columns to an existing ability table safely."""

        columns = {
            row[1]
            for row in db.execute("PRAGMA table_info(ability)").fetchall()
        }
        if "base_is_cost_time" not in columns:
            db.execute(
                "ALTER TABLE ability ADD COLUMN base_is_cost_time INTEGER DEFAULT 0"
            )
        if "charge_freq_raw" not in columns:
            db.execute(
                "ALTER TABLE ability ADD COLUMN charge_freq_raw TEXT"
            )

    # ======================================================
    # INSERT
    # ======================================================

    def _insert_ability(
        self,
        db: sqlite3.Connection,
        record: dict[str, Any],
    ):
        values = self._values(record)

        columns = [
            "ability_id",
            "display_id",

            "name",
            "index_name",
            "description",
            "texture",

            "target",
            "skill_type",

            "duration",
            "start_time",
            "tick_time",
            "cooldown",

            "cost",
            "cost_time",
            "base_cost",
            "base_mechanic",
            "base_is_cost_time",
            "charge_freq_raw",

            "charge_freq",

            "min_range",
            "max_range",
            "radius",

            "is_passive",
            "is_channeled",
            "is_permanent",

            "is_crafted",
            "crafted_id",

            "cast_time",
            "channel_time",
            "angle_distance",

            "mechanic",
            "mechanic_time",

            "is_player",

            "race_type",
            "class_type",
            "skill_line",

            "base_ability_id",

            "learned_level",
            "rank",
            "morph",
            "skill_index",

            "buff_type",
            "is_toggle",

            "num_coef_vars",
            "coef_description",

            "type1",
            "a1",
            "b1",
            "c1",
            "r1",
            "avg1",

            "type2",
            "a2",
            "b2",
            "c2",
            "r2",
            "avg2",

            "type3",
            "a3",
            "b3",
            "c3",
            "r3",
            "avg3",

            "type4",
            "a4",
            "b4",
            "c4",
            "r4",
            "avg4",

            "type5",
            "a5",
            "b5",
            "c5",
            "r5",
            "avg5",

            "type6",
            "a6",
            "b6",
            "c6",
            "r6",
            "avg6",

            "raw_description",
            "raw_name",
            "raw_tooltip",
            "raw_coef",
            "coef_types",

            "is_mastery",
            "raw_json",
        ]

        if len(columns) != len(values):
            raise RuntimeError(
                "Ability INSERT mismatch: "
                f"{len(columns)} columns, "
                f"{len(values)} values"
            )

        placeholders = ", ".join(
            "?"
            for _ in columns
        )

        sql = f"""
            INSERT OR REPLACE INTO ability (
                {", ".join(columns)}
            )
            VALUES (
                {placeholders}
            )
        """

        db.execute(
            sql,
            values,
        )

    # ======================================================
    # VALUES
    # ======================================================

    def _values(
        self,
        r: dict[str, Any],
    ) -> tuple:

        return (

            self._int(r.get("id")),
            self._int(r.get("displayId")),

            r.get("name"),
            r.get("indexName"),
            r.get("description"),
            r.get("texture"),

            r.get("target"),
            self._int(r.get("skillType")),

            self._float(r.get("duration")),
            self._float(r.get("startTime")),
            self._float(r.get("tickTime")),
            self._float(r.get("cooldown")),

            self._float(r.get("cost")),
            r.get("costTime"),
            self._float(r.get("baseCost")),
            self._int(r.get("baseMechanic")),
            self._bool(r.get("baseIsCostTime")),
            None if r.get("chargeFreq") is None else str(r.get("chargeFreq")),

            self._float(r.get("chargeFreq")),

            self._float(r.get("minRange")),
            self._float(r.get("maxRange")),
            self._float(r.get("radius")),

            self._bool(r.get("isPassive")),
            self._bool(r.get("isChanneled")),
            self._bool(r.get("isPermanent")),

            self._bool(r.get("isCrafted")),
            self._int(r.get("craftedId")),

            self._float(r.get("castTime")),
            self._float(r.get("channelTime")),
            self._float(r.get("angleDistance")),

            self._int(r.get("mechanic")),
            self._float(r.get("mechanicTime")),

            self._bool(r.get("isPlayer")),

            r.get("raceType"),
            r.get("classType"),
            r.get("skillLine"),

            self._int(r.get("baseAbilityId")),

            self._int(r.get("learnedLevel")),
            self._int(r.get("rank")),
            self._int(r.get("morph")),
            self._int(r.get("skillIndex")),

            self._int(r.get("buffType")),
            self._bool(r.get("isToggle")),

            self._int(r.get("numCoefVars")),
            r.get("coefDescription"),

            self._int(r.get("type1")),
            self._float(r.get("a1")),
            self._float(r.get("b1")),
            self._float(r.get("c1")),
            self._float(r.get("R1")),
            self._float(r.get("avg1")),

            self._int(r.get("type2")),
            self._float(r.get("a2")),
            self._float(r.get("b2")),
            self._float(r.get("c2")),
            self._float(r.get("R2")),
            self._float(r.get("avg2")),

            self._int(r.get("type3")),
            self._float(r.get("a3")),
            self._float(r.get("b3")),
            self._float(r.get("c3")),
            self._float(r.get("R3")),
            self._float(r.get("avg3")),

            self._int(r.get("type4")),
            self._float(r.get("a4")),
            self._float(r.get("b4")),
            self._float(r.get("c4")),
            self._float(r.get("R4")),
            self._float(r.get("avg4")),

            self._int(r.get("type5")),
            self._float(r.get("a5")),
            self._float(r.get("b5")),
            self._float(r.get("c5")),
            self._float(r.get("R5")),
            self._float(r.get("avg5")),

            self._int(r.get("type6")),
            self._float(r.get("a6")),
            self._float(r.get("b6")),
            self._float(r.get("c6")),
            self._float(r.get("R6")),
            self._float(r.get("avg6")),

            r.get("rawDescription"),
            r.get("rawName"),
            r.get("rawTooltip"),
            r.get("rawCoef"),
            r.get("coefTypes"),

            self._int(r.get("isMastery")),

            json.dumps(
                r,
                ensure_ascii=False,
            ),
        )

    # ======================================================
    # REPORT
    # ======================================================

    def _report(
        self,
        db: sqlite3.Connection,
        imported: int,
    ):

        total = db.execute(
            "SELECT COUNT(*) FROM ability"
        ).fetchone()[0]

        crafted = db.execute(
            """
            SELECT COUNT(*)
            FROM ability
            WHERE is_crafted = 1
            """
        ).fetchone()[0]

        no_base = db.execute(
            """
            SELECT COUNT(*)
            FROM ability
            WHERE base_ability_id = -1
            """
        ).fetchone()[0]

        normal = total - no_base

        print()
        print("## Ability Import Complete")
        print()
        print(
            f"Abilities imported:       {imported:,}"
        )
        print(
            f"Database rows:             {total:,}"
        )
        print(
            f"Normal base abilities:     {normal:,}"
        )
        print(
            f"No base ability:           {no_base:,}"
        )
        print(
            f"Crafted / Scribing:        {crafted:,}"
        )
        print()

    # ======================================================
    # CONVERSION HELPERS
    # ======================================================

    @staticmethod
    def _int(value):

        if value in (
            None,
            "",
            "-1",
        ):
            return (
                None
                if value in (None, "")
                else -1
            )

        try:
            return int(value)

        except (
            ValueError,
            TypeError,
        ):
            return None

    @staticmethod
    def _float(value):

        if value in (
            None,
            "",
            "-1",
        ):
            return (
                None
                if value in (None, "")
                else -1.0
            )

        try:
            return float(value)

        except (
            ValueError,
            TypeError,
        ):
            return None

    @staticmethod
    def _bool(value):

        if value in (
            None,
            "",
        ):
            return 0

        if str(value).lower() in (
            "1",
            "true",
            "yes",
        ):
            return 1

        return 0

    def _verify_schema(
        self,
        db: sqlite3.Connection,
    ):
        rows = db.execute(
            "PRAGMA table_info(ability)"
        ).fetchall()

        database_columns = {
            row[1]
            for row in rows
        }

        expected_columns = {
            "ability_id",
            "display_id",
            "name",
            "index_name",
            "description",
            "texture",
            "target",
            "skill_type",
            "duration",
            "start_time",
            "tick_time",
            "cooldown",
            "cost",
            "cost_time",
            "base_cost",
            "base_mechanic",
            "base_is_cost_time",
            "charge_freq_raw",
            "charge_freq",
            "min_range",
            "max_range",
            "radius",
            "is_passive",
            "is_channeled",
            "is_permanent",
            "is_crafted",
            "crafted_id",
            "cast_time",
            "channel_time",
            "angle_distance",
            "mechanic",
            "mechanic_time",
            "is_player",
            "race_type",
            "class_type",
            "skill_line",
            "base_ability_id",
            "learned_level",
            "rank",
            "morph",
            "skill_index",
            "buff_type",
            "is_toggle",
            "num_coef_vars",
            "coef_description",
            "type1",
            "a1",
            "b1",
            "c1",
            "r1",
            "avg1",
            "type2",
            "a2",
            "b2",
            "c2",
            "r2",
            "avg2",
            "type3",
            "a3",
            "b3",
            "c3",
            "r3",
            "avg3",
            "type4",
            "a4",
            "b4",
            "c4",
            "r4",
            "avg4",
            "type5",
            "a5",
            "b5",
            "c5",
            "r5",
            "avg5",
            "type6",
            "a6",
            "b6",
            "c6",
            "r6",
            "avg6",
            "raw_description",
            "raw_name",
            "raw_tooltip",
            "raw_coef",
            "coef_types",
            "is_mastery",
            "raw_json",
        }

        missing = expected_columns - database_columns

        if missing:
            raise RuntimeError(
                "Ability table is missing columns:\n"
                + "\n".join(
                    sorted(missing)
                )
            )


def main():

    importer = AbilitiesImporter()

    importer.run()


if __name__ == "__main__":
    main()
