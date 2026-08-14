"""
Black Feather Foundry
Champion Point -> Skill Relationship Importer

Purpose
-------
Imports verified ESO-Hub Champion Point relationships for skills.

The source file is expected to contain records in one of these forms:

1. A JSON object with a "skills" list:
   {
       "skills": [
           {
               "skill": "Wall of Elements",
               "championPoints": [
                   "Backstabber",
                   "Biting Aura",
                   ...
               ]
           }
       ]
   }

2. A JSON list:
   [
       {
           "skill": "Wall of Elements",
           "championPoints": ["Backstabber", ...]
       }
   ]

3. A JSON object mapping skill names to CP names:
   {
       "Wall of Elements": [
           "Backstabber",
           "Biting Aura",
           ...
       ]
   }

The importer is intentionally conservative:
- It only creates relationships explicitly present in the source.
- It does NOT infer CP relationships from descriptions.
- It matches ESO-Hub skill names against the Foundry skill table.
- It matches Champion Point names against champion_point.
- Unmatched names are reported instead of guessed.

Expected paths
--------------
Database:
    data/eso.db

Source:
    data/raw/champion_points_raw.json

You can change SOURCE_FILE below if your source file has another name.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "eso.db"
SOURCE_FILE = ROOT / "data" / "raw" / "champion_points_raw.json"


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

def normalize_name(value: Any) -> str:
    """
    Normalize names only for matching.

    We keep the original names in the database/source data.
    This is deliberately modest so we do not accidentally merge unrelated
    ESO skills.
    """
    if value is None:
        return ""

    text = str(value).strip().lower()

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


# ---------------------------------------------------------------------------
# Importer
# ---------------------------------------------------------------------------

class ChampionPointSkillImporter:

    def __init__(
        self,
        database: Path = DATABASE,
        source_file: Path = SOURCE_FILE,
    ) -> None:
        self.database_path = database
        self.source_file = source_file

        self.db: sqlite3.Connection | None = None

        self.records: list[dict[str, Any]] = []

        self.skill_lookup: dict[str, list[dict[str, Any]]] = {}
        self.cp_lookup: dict[str, list[dict[str, Any]]] = {}

        self.relationship_rows: list[dict[str, Any]] = []

        self.inserted = 0
        self.updated = 0
        self.skipped = 0

        self.unmatched_skills: list[str] = []
        self.unmatched_cp: list[str] = []
        self.ambiguous_skills: list[str] = []

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------

    def run(self) -> None:
        print("=" * 49)
        print(" Black Feather Foundry")
        print(" Champion Point -> Skill Importer")
        print("=" * 49)
        print()
        print(f"Source:   {self.source_file}")
        print(f"Database: {self.database_path}")
        print()

        self._load_source()
        print(f"Source skill records: {len(self.records):,}")
        print()

        self.db = sqlite3.connect(self.database_path)

        try:
            self._ensure_table()
            self._load_skill_lookup()
            self._load_cp_lookup()
            self._build_relationships()
            self._insert_relationships()
            self.db.commit()
            self._report()

        except Exception:
            self.db.rollback()
            raise

        finally:
            self.db.close()

    # ------------------------------------------------------------------
    # Source loading
    # ------------------------------------------------------------------

    def _load_source(self) -> None:
        if not self.source_file.exists():
            raise FileNotFoundError(
                "Champion Point skill source file was not found:\n"
                f"{self.source_file}\n\n"
                "Create the ESO-Hub relationship file there before running "
                "this importer."
            )

        with self.source_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        self.records = self._extract_records(data)

        if not self.records:
            raise ValueError(
                "No skill -> Champion Point records were found in the source."
            )

    def _extract_records(
        self,
        data: Any,
    ) -> list[dict[str, Any]]:
        """
        Accept several simple JSON shapes so the source file does not need
        to be rewritten just to satisfy the importer.
        """

        if isinstance(data, list):
            return [
                record
                for record in data
                if isinstance(record, dict)
            ]

        if not isinstance(data, dict):
            return []

        # Preferred shape:
        # {"skills": [{...}, {...}]}
        skills = data.get("skills")

        if isinstance(skills, list):
            return [
                record
                for record in skills
                if isinstance(record, dict)
            ]

        # Alternate shape:
        # {"skill": ["CP", "CP"]}
        records = []

        for skill_name, cp_values in data.items():

            if not isinstance(cp_values, list):
                continue

            records.append(
                {
                    "skill": skill_name,
                    "championPoints": cp_values,
                }
            )

        return records

    # ------------------------------------------------------------------
    # Database schema
    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        assert self.db is not None

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS champion_point_skill (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                champion_point_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,

                relationship TEXT NOT NULL DEFAULT 'Buffs',

                source TEXT,
                confidence TEXT,

                raw_source TEXT,

                UNIQUE (
                    champion_point_id,
                    skill_id
                )
            )
            """
        )

        self.db.commit()

        existing = set(self._table_columns())

        required = {
            "champion_point_id": "INTEGER",
            "skill_id": "INTEGER",
            "relationship": "TEXT",
            "source": "TEXT",
            "confidence": "TEXT",
            "raw_source": "TEXT",
        }

        for column, sql_type in required.items():

            if column not in existing:
                self.db.execute(
                    f"""
                    ALTER TABLE champion_point_skill
                    ADD COLUMN "{column}" {sql_type}
                    """
                )

        self.db.commit()

    def _table_columns(self) -> list[str]:
        assert self.db is not None

        rows = self.db.execute(
            "PRAGMA table_info(champion_point_skill)"
        ).fetchall()

        return [
            row[1]
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Existing skill data
    # ------------------------------------------------------------------

    def _load_skill_lookup(self) -> None:
        assert self.db is not None

        rows = self.db.execute(
            """
            SELECT
                id,
                name,
                index_name,
                base_ability_id
            FROM skill
            WHERE name IS NOT NULL
            """
        ).fetchall()

        for (
            skill_id,
            name,
            index_name,
            base_ability_id,
        ) in rows:

            entry = {
                "id": skill_id,
                "name": name,
                "index_name": index_name,
                "base_ability_id": base_ability_id,
            }

            for candidate in (
                name,
                index_name,
            ):
                normalized = normalize_name(candidate)

                if not normalized:
                    continue

                self.skill_lookup.setdefault(
                    normalized,
                    [],
                ).append(entry)

    # ------------------------------------------------------------------
    # Champion Point data
    # ------------------------------------------------------------------

    def _load_cp_lookup(self) -> None:
        assert self.db is not None

        rows = self.db.execute(
            """
            SELECT
                id,
                name,
                ability_id,
                skill_id,
                discipline_index
            FROM champion_point
            WHERE name IS NOT NULL
            """
        ).fetchall()

        for (
            cp_id,
            name,
            ability_id,
            skill_id,
            discipline_index,
        ) in rows:

            normalized = normalize_name(name)

            if not normalized:
                continue

            self.cp_lookup.setdefault(
                normalized,
                [],
            ).append(
                {
                    "id": cp_id,
                    "name": name,
                    "ability_id": ability_id,
                    "skill_id": skill_id,
                    "discipline_index": discipline_index,
                }
            )

    # ------------------------------------------------------------------
    # Relationship parsing
    # ------------------------------------------------------------------

    def _build_relationships(self) -> None:

        for record in self.records:

            skill_name = self._get_skill_name(record)

            if not skill_name:
                self.skipped += 1
                continue

            cp_names = self._get_cp_names(record)

            if not cp_names:
                self.skipped += 1
                continue

            skill_matches = self._match_skill(
                skill_name
            )

            if not skill_matches:
                if skill_name not in self.unmatched_skills:
                    self.unmatched_skills.append(
                        skill_name
                    )
                continue

            if len(skill_matches) > 1:
                self.ambiguous_skills.append(
                    skill_name
                )

            # A canonical ESO skill should normally resolve to one row.
            # If the database contains duplicates, preserve all exact
            # matches rather than silently picking one.
            for skill in skill_matches:

                for cp_name in cp_names:

                    cp_matches = self._match_cp(
                        cp_name
                    )

                    if not cp_matches:
                        if cp_name not in self.unmatched_cp:
                            self.unmatched_cp.append(
                                cp_name
                            )
                        continue

                    for cp in cp_matches:

                        self.relationship_rows.append(
                            {
                                "champion_point_id": cp["id"],
                                "skill_id": skill["id"],
                                "relationship": "Buffs",
                                "source": "ESO Hub",
                                "confidence": "Explicit",
                                "raw_source": (
                                    f"{skill_name} -> {cp_name}"
                                ),
                            }
                        )

    # ------------------------------------------------------------------
    # Source field helpers
    # ------------------------------------------------------------------

    def _get_skill_name(
        self,
        record: dict[str, Any],
    ) -> str | None:

        for key in (
            "skill",
            "skillName",
            "name",
            "title",
        ):
            value = record.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    def _get_cp_names(
        self,
        record: dict[str, Any],
    ) -> list[str]:

        for key in (
            "championPoints",
            "champion_points",
            "championPoint",
            "champion_point",
            "cp",
            "cps",
        ):

            value = record.get(key)

            if isinstance(value, list):

                return [
                    str(item).strip()
                    for item in value
                    if str(item).strip()
                ]

            if isinstance(value, str) and value.strip():
                return [
                    value.strip()
                ]

        return []

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def _match_skill(
        self,
        name: str,
    ) -> list[dict[str, Any]]:

        normalized = normalize_name(name)

        return self.skill_lookup.get(
            normalized,
            [],
        )

    def _match_cp(
        self,
        name: str,
    ) -> list[dict[str, Any]]:

        normalized = normalize_name(name)

        return self.cp_lookup.get(
            normalized,
            [],
        )

    # ------------------------------------------------------------------
    # Insert
    # ------------------------------------------------------------------

    def _insert_relationships(self) -> None:
        assert self.db is not None

        for row in self.relationship_rows:

            existing = self.db.execute(
                """
                SELECT id
                FROM champion_point_skill
                WHERE champion_point_id = ?
                  AND skill_id = ?
                """,
                (
                    row["champion_point_id"],
                    row["skill_id"],
                ),
            ).fetchone()

            if existing:

                self.db.execute(
                    """
                    UPDATE champion_point_skill
                    SET
                        relationship = ?,
                        source = ?,
                        confidence = ?,
                        raw_source = ?
                    WHERE id = ?
                    """,
                    (
                        row["relationship"],
                        row["source"],
                        row["confidence"],
                        row["raw_source"],
                        existing[0],
                    ),
                )

                self.updated += 1

            else:

                self.db.execute(
                    """
                    INSERT INTO champion_point_skill (
                        champion_point_id,
                        skill_id,
                        relationship,
                        source,
                        confidence,
                        raw_source
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["champion_point_id"],
                        row["skill_id"],
                        row["relationship"],
                        row["source"],
                        row["confidence"],
                        row["raw_source"],
                    ),
                )

                self.inserted += 1

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def _report(self) -> None:
        assert self.db is not None

        total = self.db.execute(
            """
            SELECT COUNT(*)
            FROM champion_point_skill
            """
        ).fetchone()[0]

        unique_skills = self.db.execute(
            """
            SELECT COUNT(DISTINCT skill_id)
            FROM champion_point_skill
            """
        ).fetchone()[0]

        unique_cp = self.db.execute(
            """
            SELECT COUNT(DISTINCT champion_point_id)
            FROM champion_point_skill
            """
        ).fetchone()[0]

        print()
        print("=" * 49)
        print(" Champion Point -> Skill Import Complete")
        print("=" * 49)
        print()

        print(
            f"Source skill records:    {len(self.records):,}"
        )
        print(
            f"Relationships parsed:    "
            f"{len(self.relationship_rows):,}"
        )
        print(
            f"Links inserted:          {self.inserted:,}"
        )
        print(
            f"Links updated:           {self.updated:,}"
        )
        print(
            f"Records skipped:         {self.skipped:,}"
        )
        print(
            f"Total CP -> skill links: {total:,}"
        )
        print(
            f"Unique skills linked:    {unique_skills:,}"
        )
        print(
            f"Unique CPs linked:       {unique_cp:,}"
        )
        print()

        print("=== UNMATCHED SKILLS ===")

        if self.unmatched_skills:
            for name in sorted(
                self.unmatched_skills,
                key=str.lower,
            ):
                print(name)
        else:
            print("(none)")

        print()

        print("=== UNMATCHED CHAMPION POINTS ===")

        if self.unmatched_cp:
            for name in sorted(
                self.unmatched_cp,
                key=str.lower,
            ):
                print(name)
        else:
            print("(none)")

        print()

        print("=== AMBIGUOUS SKILLS ===")

        if self.ambiguous_skills:
            for name in sorted(
                set(self.ambiguous_skills),
                key=str.lower,
            ):
                print(name)
        else:
            print("(none)")

        print()

        # Specific sanity check for Wall of Elements.
        self._wall_of_elements_check()

    # ------------------------------------------------------------------
    # Sanity check
    # ------------------------------------------------------------------

    def _wall_of_elements_check(self) -> None:
        assert self.db is not None

        rows = self.db.execute(
            """
            SELECT
                cp.name,
                cp.ability_id,
                cps.skill_id
            FROM champion_point_skill cps
            JOIN champion_point cp
              ON cp.id = cps.champion_point_id
            JOIN skill s
              ON s.id = cps.skill_id
            WHERE LOWER(s.name) = 'wall of elements'
            ORDER BY cp.name
            """
        ).fetchall()

        print("=== WALL OF ELEMENTS CHECK ===")

        if not rows:
            print("(no Wall of Elements relationships found)")
            print()
            return

        for row in rows:
            print(row)

        print()


def main() -> None:
    importer = ChampionPointSkillImporter()
    importer.run()


if __name__ == "__main__":
    main()
