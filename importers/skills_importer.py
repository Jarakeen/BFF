from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# ============================================================
# Project Root
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================================
# Database
# ============================================================

from services.eso_database import EsoDatabase


# ============================================================
# Files
# ============================================================

DATABASE_FILE = ROOT / "data" / "eso.db"

SKILLS_RAW_FILE = (
    ROOT / "data" / "raw" / "skills_raw.json"
)

COEFFICIENT_RAW_FILE = (
    ROOT / "data" / "raw" / "skill_coef_raw.json"
)


# ============================================================
# Importer
# ============================================================

class SkillsImporter:

    def __init__(
        self,
        database: EsoDatabase,
        skills_file: Path = SKILLS_RAW_FILE,
        coefficient_file: Path = COEFFICIENT_RAW_FILE,
    ):
        self.database = database
        self.skills_file = Path(skills_file)
        self.coefficient_file = Path(coefficient_file)

    # ========================================================
    # RUN
    # ========================================================

    def run(self):

        print()
        print("=========================================")
        print(" Black Feather Foundry")
        print(" ESO Skills Importer")
        print("=========================================")
        print()

        print(f"Skills raw data:      {self.skills_file}")
        print(f"Coefficient raw data: {self.coefficient_file}")
        print(f"Database:             {self.database.database}")
        print()

        # ----------------------------------------------------
        # Load raw data
        # ----------------------------------------------------

        skill_records = self._load_skill_records()
        coefficient_records = self._load_coefficient_records()

        print(
            f"Raw skill records:       {len(skill_records):,}"
        )

        print(
            f"Raw coefficient records: {len(coefficient_records):,}"
        )

        print()

        # ----------------------------------------------------
        # Rebuild skill tables
        # ----------------------------------------------------

        self._create_tables()

        # ----------------------------------------------------
        # Canonical skills
        # ----------------------------------------------------

        skill_map: dict[int, int] = {}

        skill_count = 0
        rank_count = 0

        for record in skill_records:

            if not isinstance(record, dict):
                continue

            ability_id = self._int(record.get("id"))

            if ability_id is None:
                continue

            base_ability_id = self._int(
                record.get("baseAbilityId")
            )

            if base_ability_id is None:
                base_ability_id = ability_id

            # --------------------------------------------
            # Canonical skill
            # --------------------------------------------

            skill_id = skill_map.get(
                base_ability_id
            )

            if skill_id is None:

                skill_id = self._insert_skill(
                    record,
                    base_ability_id,
                )

                skill_map[
                    base_ability_id
                ] = skill_id

                skill_count += 1

            # --------------------------------------------
            # Rank / morph
            # --------------------------------------------

            if self._insert_skill_rank(
                skill_id,
                record,
            ):
                rank_count += 1

        print(
            f"Canonical skills created: {skill_count:,}"
        )

        print(
            f"Skill ranks imported:      {rank_count:,}"
        )

        print()

        # ----------------------------------------------------
        # Coefficients
        # ----------------------------------------------------

        coefficient_sources = 0
        coefficient_rows = 0
        unmatched = 0

        for record in coefficient_records:

            if not isinstance(record, dict):
                continue

            ability_id = self._int(
                record.get("id")
            )

            if ability_id is None:
                continue

            rank_id = self._find_rank_id(
                ability_id
            )

            if rank_id is None:

                unmatched += 1
                continue

            coefficient_sources += 1

            coefficient_rows += (
                self._insert_coefficients(
                    rank_id,
                    record,
                )
            )

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        self.database.commit()

        # ----------------------------------------------------
        # Final validation
        # ----------------------------------------------------

        skill_total = self._count("skill")
        rank_total = self._count("skill_rank")
        coefficient_total = self._count(
            "skill_coefficient"
        )

        print()
        print("Skills Import Complete")
        print("-----------------------------------------")

        print(
            f"Canonical skills:        {skill_total:,}"
        )

        print(
            f"Skill ranks:             {rank_total:,}"
        )

        print(
            f"Coefficient sources:     {coefficient_sources:,}"
        )

        print(
            f"Coefficient rows:        {coefficient_total:,}"
        )

        print(
            f"Unmatched coefficients:  {unmatched:,}"
        )

        print()

    # ========================================================
    # LOAD SKILLS
    # ========================================================

    def _load_skill_records(
        self,
    ) -> list[dict[str, Any]]:

        if not self.skills_file.exists():

            raise FileNotFoundError(
                f"Skills raw file not found:\n"
                f"{self.skills_file}"
            )

        with self.skills_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):

            raise ValueError(
                "Invalid skills JSON. "
                "Expected an object."
            )

        records = data.get("playerSkills")

        if not isinstance(records, list):

            raise ValueError(
                "Invalid skills JSON. "
                "Expected 'playerSkills' "
                "to be a list."
            )

        expected = self._int(
            data.get("numRecords")
        )

        if (
            expected is not None
            and expected != len(records)
        ):

            print(
                "WARNING: "
                f"numRecords={expected:,}, "
                f"playerSkills={len(records):,}"
            )

        return records

    # ========================================================
    # LOAD COEFFICIENTS
    # ========================================================

    def _load_coefficient_records(
        self,
    ) -> list[dict[str, Any]]:

        if not self.coefficient_file.exists():

            raise FileNotFoundError(
                f"Coefficient raw file not found:\n"
                f"{self.coefficient_file}"
            )

        with self.coefficient_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):

            raise ValueError(
                "Invalid coefficient JSON. "
                "Expected an object."
            )

        records = data.get("skillCoef")

        if not isinstance(records, list):

            raise ValueError(
                "Invalid coefficient JSON. "
                "Expected 'skillCoef' "
                "to be a list."
            )

        expected = self._int(
            data.get("numRecords")
        )

        if (
            expected is not None
            and expected != len(records)
        ):

            print(
                "WARNING: "
                f"numRecords={expected:,}, "
                f"skillCoef={len(records):,}"
            )

        return records

    # ========================================================
    # CREATE TABLES
    # ========================================================

    def _create_tables(self):

        # ----------------------------------------------------
        # Drop old skill tables
        # ----------------------------------------------------

        self.database.execute(
            "DROP TABLE IF EXISTS skill_coefficient"
        )

        self.database.execute(
            "DROP TABLE IF EXISTS skill_rank"
        )

        self.database.execute(
            "DROP TABLE IF EXISTS skill"
        )

        # ----------------------------------------------------
        # Canonical Skill
        # ----------------------------------------------------

        self.database.execute(
            """
            CREATE TABLE skill (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                base_ability_id INTEGER NOT NULL UNIQUE,

                name TEXT,
                index_name TEXT,
                description TEXT,
                texture TEXT,

                class_type INTEGER,
                skill_line INTEGER,

                target INTEGER,
                skill_type INTEGER,

                is_passive INTEGER NOT NULL DEFAULT 0,
                is_player INTEGER NOT NULL DEFAULT 0,
                is_crafted INTEGER NOT NULL DEFAULT 0,

                crafted_id INTEGER
            )
            """
        )

        # ----------------------------------------------------
        # Skill Rank / Morph
        # ----------------------------------------------------

        self.database.execute(
            """
            CREATE TABLE skill_rank (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                skill_id INTEGER NOT NULL,

                ability_id INTEGER NOT NULL UNIQUE,
                display_id INTEGER,

                rank INTEGER,
                morph INTEGER,

                prev_skill INTEGER,
                next_skill INTEGER,
                next_skill2 INTEGER,

                skill_index INTEGER,
                learned_level INTEGER,

                cost REAL,
                duration REAL,

                start_time REAL,
                tick_time REAL,

                cooldown REAL,

                cast_time REAL,
                channel_time REAL,

                radius REAL,
                min_range REAL,
                max_range REAL,

                angle_distance REAL,

                mechanic INTEGER,
                mechanic_time REAL,

                buff_type INTEGER,

                is_toggle INTEGER NOT NULL DEFAULT 0,

                num_coef_vars INTEGER,

                coef_description TEXT,

                raw_description TEXT,
                raw_name TEXT,
                raw_tooltip TEXT,
                raw_coef TEXT,
                coef_types TEXT,

                is_mastery INTEGER NOT NULL DEFAULT 0,

                raw_json TEXT,

                FOREIGN KEY (skill_id)
                    REFERENCES skill(id)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # Individual Coefficients
        # ----------------------------------------------------

        self.database.execute(
            """
            CREATE TABLE skill_coefficient (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                skill_rank_id INTEGER NOT NULL,

                coefficient_number INTEGER NOT NULL,

                type TEXT,

                a REAL,
                b REAL,
                c REAL,
                r REAL,
                avg REAL,

                FOREIGN KEY (skill_rank_id)
                    REFERENCES skill_rank(id)
                    ON DELETE CASCADE,

                UNIQUE (
                    skill_rank_id,
                    coefficient_number
                )
            )
            """
        )

        self.database.commit()

    # ========================================================
    # INSERT SKILL
    # ========================================================

    def _insert_skill(
        self,
        record: dict[str, Any],
        base_ability_id: int,
    ) -> int:

        cursor = self.database.execute(
            """
            INSERT INTO skill (

                base_ability_id,

                name,
                index_name,
                description,
                texture,

                class_type,
                skill_line,

                target,
                skill_type,

                is_passive,
                is_player,
                is_crafted,

                crafted_id
            )

            VALUES (
                ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?
            )
            """,
            (
                base_ability_id,

                self._text(
                    record.get("name")
                ),

                self._text(
                    record.get("indexName")
                ),

                self._text(
                    record.get("description")
                ),

                self._text(
                    record.get("texture")
                ),

                self._int(
                    record.get("classType")
                ),

                self._int(
                    record.get("skillLine")
                ),

                self._int(
                    record.get("target")
                ),

                self._int(
                    record.get("skillType")
                ),

                self._bool_int(
                    record.get("isPassive")
                ),

                self._bool_int(
                    record.get("isPlayer")
                ),

                self._bool_int(
                    record.get("isCrafted")
                ),

                self._int(
                    record.get("craftedId")
                ),
            ),
        )

        return int(cursor.lastrowid)

    # ========================================================
    # INSERT SKILL RANK
    # ========================================================

    def _insert_skill_rank(
        self,
        skill_id: int,
        record: dict[str, Any],
    ) -> bool:

        ability_id = self._int(
            record.get("id")
        )

        if ability_id is None:
            return False

        cursor = self.database.execute(
            """
            INSERT OR IGNORE INTO skill_rank (

                skill_id,

                ability_id,
                display_id,

                rank,
                morph,

                prev_skill,
                next_skill,
                next_skill2,

                skill_index,
                learned_level,

                cost,
                duration,

                start_time,
                tick_time,

                cooldown,

                cast_time,
                channel_time,

                radius,
                min_range,
                max_range,

                angle_distance,

                mechanic,
                mechanic_time,

                buff_type,

                is_toggle,

                num_coef_vars,

                coef_description,

                raw_description,
                raw_name,
                raw_tooltip,
                raw_coef,
                coef_types,

                is_mastery,

                raw_json
            )

            VALUES (

                ?,

                ?,
                ?,

                ?,
                ?,

                ?,
                ?,
                ?,

                ?,
                ?,

                ?,
                ?,

                ?,
                ?,

                ?,

                ?,
                ?,

                ?,
                ?,
                ?,

                ?,

                ?,
                ?,

                ?,

                ?,

                ?,

                ?,

                ?,
                ?,
                ?,
                ?,
                ?,

                ?,

                ?
            )
            """,
            (

                skill_id,

                ability_id,

                self._int(
                    record.get("displayId")
                ),

                self._int(
                    record.get("rank")
                ),

                self._int(
                    record.get("morph")
                ),

                self._int(
                    record.get("prevSkill")
                ),

                self._int(
                    record.get("nextSkill")
                ),

                self._int(
                    record.get("nextSkill2")
                ),

                self._int(
                    record.get("skillIndex")
                ),

                self._int(
                    record.get("learnedLevel")
                ),

                self._number(
                    record.get("cost")
                ),

                self._number(
                    record.get("duration")
                ),

                self._number(
                    record.get("startTime")
                ),

                self._number(
                    record.get("tickTime")
                ),

                self._number(
                    record.get("cooldown")
                ),

                self._number(
                    record.get("castTime")
                ),

                self._number(
                    record.get("channelTime")
                ),

                self._number(
                    record.get("radius")
                ),

                self._number(
                    record.get("minRange")
                ),

                self._number(
                    record.get("maxRange")
                ),

                self._number(
                    record.get("angleDistance")
                ),

                self._int(
                    record.get("mechanic")
                ),

                self._number(
                    record.get("mechanicTime")
                ),

                self._int(
                    record.get("buffType")
                ),

                self._bool_int(
                    record.get("isToggle")
                ),

                self._int(
                    record.get("numCoefVars")
                ),

                self._text(
                    record.get("coefDescription")
                ),

                self._text(
                    record.get("rawDescription")
                ),

                self._text(
                    record.get("rawName")
                ),

                self._text(
                    record.get("rawTooltip")
                ),

                self._text(
                    record.get("rawCoef")
                ),

                self._text(
                    record.get("coefTypes")
                ),

                self._bool_int(
                    record.get("isMastery")
                ),

                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            ),
        )

        return cursor.rowcount > 0

    # ========================================================
    # FIND RANK
    # ========================================================

    def _find_rank_id(
        self,
        ability_id: int,
    ) -> int | None:

        row = self.database.execute(
            """
            SELECT id
            FROM skill_rank
            WHERE ability_id = ?
            """,
            (ability_id,),
        ).fetchone()

        if row is None:
            return None

        return int(row[0])

    # ========================================================
    # INSERT COEFFICIENTS
    # ========================================================

    def _insert_coefficients(
        self,
        skill_rank_id: int,
        record: dict[str, Any],
    ) -> int:

        inserted = 0

        for number in range(1, 7):

            type_value = self._text(
                record.get(
                    f"type{number}"
                )
            )

            a = self._number(
                record.get(
                    f"a{number}"
                )
            )

            b = self._number(
                record.get(
                    f"b{number}"
                )
            )

            c = self._number(
                record.get(
                    f"c{number}"
                )
            )

            r = self._number(
                record.get(
                    f"R{number}"
                )
            )

            avg = self._number(
                record.get(
                    f"avg{number}"
                )
            )

            # Empty coefficient slot
            if (
                type_value is None
                and a is None
                and b is None
                and c is None
                and r is None
                and avg is None
            ):
                continue

            self.database.execute(
                """
                INSERT INTO skill_coefficient (

                    skill_rank_id,
                    coefficient_number,

                    type,

                    a,
                    b,
                    c,
                    r,
                    avg
                )

                VALUES (
                    ?, ?,
                    ?,
                    ?, ?, ?, ?, ?
                )
                """,
                (
                    skill_rank_id,
                    number,

                    type_value,

                    a,
                    b,
                    c,
                    r,
                    avg,
                ),
            )

            inserted += 1

        return inserted

    # ========================================================
    # COUNT
    # ========================================================

    def _count(
        self,
        table: str,
    ) -> int:

        row = self.database.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()

        return int(row[0])

    # ========================================================
    # VALUE HELPERS
    # ========================================================

    @staticmethod
    def _text(
        value: Any,
    ) -> str | None:

        if value is None:
            return None

        text = str(value).strip()

        if not text:
            return None

        return text

    @staticmethod
    def _int(
        value: Any,
    ) -> int | None:

        if value is None:
            return None

        if isinstance(value, bool):
            return int(value)

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _number(
        value: Any,
    ) -> float | None:

        if value is None:
            return None

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _bool_int(
        value: Any,
    ) -> int:

        if value is None:
            return 0

        if isinstance(value, bool):
            return int(value)

        if isinstance(value, str):

            return int(
                value.strip().lower()
                in (
                    "true",
                    "1",
                    "yes",
                )
            )

        return int(bool(value))


# ============================================================
# MAIN
# ============================================================

def main():

    database = EsoDatabase(
        DATABASE_FILE
    )

    importer = SkillsImporter(
        database
    )

    try:

        importer.run()

    except Exception:

        database.rollback()
        raise

    finally:

        database.close()


if __name__ == "__main__":
    main()