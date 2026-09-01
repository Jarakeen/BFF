"""
Black Feather Foundry
Champion Point -> Skill Relationship Importer

Purpose
-------
Imports verified ESO-Hub Champion Point relationships for skills.

The preferred source is the direct output of
``crawlers/eso_hub_skill_cp_crawler.py``::

    {
        "source": "ESO-Hub",
        "skills": [
            {
                "skill_id": 123,
                "skill_name": "Energy Orb",
                "url": "https://eso-hub.com/.../energy-orb",
                "champion_points": [
                    {
                        "champion_point_name": "Rejuvenator",
                        "condition": "only while slotted",
                        "source": "ESO-Hub"
                    }
                ]
            }
        ]
    }

Legacy flat forms remain accepted for backward compatibility.

Safety rules
------------
- Only relationships explicitly present in the harvested source are imported.
- CP -> skill applicability is never inferred from descriptions.
- Skill and Champion Point names are resolved against canonical database rows.
- Unmatched names are reported instead of guessed.
- Harvested conditions such as ``only while slotted`` are preserved.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "eso.db"
SOURCE_FILE = ROOT / "data" / "raw" / "skill_champion_points.json"


def normalize_name(value: Any) -> str:
    """Normalize names only for conservative matching."""
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

    def _load_source(self) -> None:
        if not self.source_file.exists():
            raise FileNotFoundError(
                "Champion Point skill source file was not found:\n"
                f"{self.source_file}\n\n"
                "Create the ESO-Hub relationship file there before running this importer."
            )
        with self.source_file.open("r", encoding="utf-8") as file:
            data = json.load(file)
        self.records = self._extract_records(data)
        if not self.records:
            raise ValueError("No skill -> Champion Point records were found in the source.")

    def _extract_records(self, data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [record for record in data if isinstance(record, dict)]
        if not isinstance(data, dict):
            return []

        skills = data.get("skills")
        if isinstance(skills, list):
            return [record for record in skills if isinstance(record, dict)]

        records: list[dict[str, Any]] = []
        for skill_name, cp_values in data.items():
            if not isinstance(cp_values, list):
                continue
            records.append({"skill": skill_name, "championPoints": cp_values})
        return records

    def _ensure_table(self) -> None:
        assert self.db is not None
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS champion_point_skill (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                champion_point_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                relationship TEXT NOT NULL DEFAULT 'Buffs',
                condition TEXT,
                source TEXT,
                confidence TEXT,
                source_url TEXT,
                raw_source TEXT,
                UNIQUE (champion_point_id, skill_id)
            )
            """
        )
        self.db.commit()

        existing = set(self._table_columns())
        required = {
            "champion_point_id": "INTEGER",
            "skill_id": "INTEGER",
            "relationship": "TEXT",
            "condition": "TEXT",
            "source": "TEXT",
            "confidence": "TEXT",
            "source_url": "TEXT",
            "raw_source": "TEXT",
        }
        for column, sql_type in required.items():
            if column not in existing:
                self.db.execute(
                    f'ALTER TABLE champion_point_skill ADD COLUMN "{column}" {sql_type}'
                )
        self.db.commit()

    def _table_columns(self) -> list[str]:
        assert self.db is not None
        rows = self.db.execute("PRAGMA table_info(champion_point_skill)").fetchall()
        return [row[1] for row in rows]

    def _load_skill_lookup(self) -> None:
        assert self.db is not None
        rows = self.db.execute(
            """
            SELECT id, name, index_name, base_ability_id
            FROM skill
            WHERE name IS NOT NULL
            """
        ).fetchall()
        for skill_id, name, index_name, base_ability_id in rows:
            entry = {
                "id": skill_id,
                "name": name,
                "index_name": index_name,
                "base_ability_id": base_ability_id,
            }
            for candidate in (name, index_name):
                normalized = normalize_name(candidate)
                if normalized:
                    self.skill_lookup.setdefault(normalized, []).append(entry)

    def _load_cp_lookup(self) -> None:
        assert self.db is not None
        rows = self.db.execute(
            """
            SELECT id, name, ability_id, skill_id, discipline_index
            FROM champion_point
            WHERE name IS NOT NULL
            """
        ).fetchall()
        for cp_id, name, ability_id, skill_id, discipline_index in rows:
            normalized = normalize_name(name)
            if not normalized:
                continue
            self.cp_lookup.setdefault(normalized, []).append(
                {
                    "id": cp_id,
                    "name": name,
                    "ability_id": ability_id,
                    "skill_id": skill_id,
                    "discipline_index": discipline_index,
                }
            )

    def _build_relationships(self) -> None:
        for record in self.records:
            skill_name = self._get_skill_name(record)
            if not skill_name:
                self.skipped += 1
                continue

            cp_entries = self._get_cp_entries(record)
            if not cp_entries:
                self.skipped += 1
                continue

            skill_matches = self._match_skill(skill_name)
            if not skill_matches:
                if skill_name not in self.unmatched_skills:
                    self.unmatched_skills.append(skill_name)
                continue
            if len(skill_matches) > 1:
                self.ambiguous_skills.append(skill_name)

            source_url = str(record.get("url") or "").strip() or None
            for skill in skill_matches:
                for cp_entry in cp_entries:
                    cp_name = cp_entry["name"]
                    cp_matches = self._match_cp(cp_name)
                    if not cp_matches:
                        if cp_name not in self.unmatched_cp:
                            self.unmatched_cp.append(cp_name)
                        continue

                    condition = cp_entry.get("condition")
                    source = cp_entry.get("source") or "ESO-Hub"
                    raw_source = f"{skill_name} -> {cp_name}"
                    if condition:
                        raw_source += f" ({condition})"

                    for cp in cp_matches:
                        self.relationship_rows.append(
                            {
                                "champion_point_id": cp["id"],
                                "skill_id": skill["id"],
                                "relationship": "Buffs",
                                "condition": condition,
                                "source": source,
                                "confidence": "Explicit",
                                "source_url": source_url,
                                "raw_source": raw_source,
                            }
                        )

    def _get_skill_name(self, record: dict[str, Any]) -> str | None:
        for key in ("skill_name", "skill", "skillName", "name", "title"):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _get_cp_entries(self, record: dict[str, Any]) -> list[dict[str, str | None]]:
        for key in (
            "championPoints",
            "champion_points",
            "championPoint",
            "champion_point",
            "cp",
            "cps",
        ):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return [{"name": value.strip(), "condition": None, "source": None}]
            if not isinstance(value, list):
                continue

            result: list[dict[str, str | None]] = []
            for item in value:
                if isinstance(item, str) and item.strip():
                    result.append({"name": item.strip(), "condition": None, "source": None})
                    continue
                if not isinstance(item, dict):
                    continue
                name = ""
                for name_key in (
                    "champion_point_name",
                    "championPointName",
                    "name",
                    "champion_point",
                    "championPoint",
                ):
                    candidate = item.get(name_key)
                    if isinstance(candidate, str) and candidate.strip():
                        name = candidate.strip()
                        break
                if not name:
                    continue
                condition = str(item.get("condition") or "").strip() or None
                source = str(item.get("source") or "").strip() or None
                result.append({"name": name, "condition": condition, "source": source})
            return result
        return []

    def _match_skill(self, name: str) -> list[dict[str, Any]]:
        return self.skill_lookup.get(normalize_name(name), [])

    def _match_cp(self, name: str) -> list[dict[str, Any]]:
        return self.cp_lookup.get(normalize_name(name), [])

    def _insert_relationships(self) -> None:
        assert self.db is not None
        for row in self.relationship_rows:
            existing = self.db.execute(
                """
                SELECT id
                FROM champion_point_skill
                WHERE champion_point_id = ? AND skill_id = ?
                """,
                (row["champion_point_id"], row["skill_id"]),
            ).fetchone()
            values = (
                row["relationship"],
                row["condition"],
                row["source"],
                row["confidence"],
                row["source_url"],
                row["raw_source"],
            )
            if existing:
                self.db.execute(
                    """
                    UPDATE champion_point_skill
                    SET relationship = ?, condition = ?, source = ?, confidence = ?,
                        source_url = ?, raw_source = ?
                    WHERE id = ?
                    """,
                    values + (existing[0],),
                )
                self.updated += 1
            else:
                self.db.execute(
                    """
                    INSERT INTO champion_point_skill (
                        champion_point_id, skill_id, relationship, condition,
                        source, confidence, source_url, raw_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["champion_point_id"],
                        row["skill_id"],
                    ) + values,
                )
                self.inserted += 1

    def _report(self) -> None:
        assert self.db is not None
        total = self.db.execute("SELECT COUNT(*) FROM champion_point_skill").fetchone()[0]
        unique_skills = self.db.execute(
            "SELECT COUNT(DISTINCT skill_id) FROM champion_point_skill"
        ).fetchone()[0]
        unique_cp = self.db.execute(
            "SELECT COUNT(DISTINCT champion_point_id) FROM champion_point_skill"
        ).fetchone()[0]

        print()
        print("=" * 49)
        print(" Champion Point -> Skill Import Complete")
        print("=" * 49)
        print()
        print(f"Source skill records:    {len(self.records):,}")
        print(f"Relationships parsed:    {len(self.relationship_rows):,}")
        print(f"Links inserted:          {self.inserted:,}")
        print(f"Links updated:           {self.updated:,}")
        print(f"Records skipped:         {self.skipped:,}")
        print(f"Total CP -> skill links: {total:,}")
        print(f"Unique skills linked:    {unique_skills:,}")
        print(f"Unique CPs linked:       {unique_cp:,}")
        print()

        print("=== UNMATCHED SKILLS ===")
        if self.unmatched_skills:
            for name in sorted(self.unmatched_skills, key=str.lower):
                print(name)
        else:
            print("(none)")
        print()

        print("=== UNMATCHED CHAMPION POINTS ===")
        if self.unmatched_cp:
            for name in sorted(self.unmatched_cp, key=str.lower):
                print(name)
        else:
            print("(none)")
        print()

        print("=== AMBIGUOUS SKILLS ===")
        if self.ambiguous_skills:
            for name in sorted(set(self.ambiguous_skills), key=str.lower):
                print(name)
        else:
            print("(none)")
        print()

        self._wall_of_elements_check()

    def _wall_of_elements_check(self) -> None:
        assert self.db is not None
        rows = self.db.execute(
            """
            SELECT cp.name, cp.ability_id, cps.skill_id, cps.condition
            FROM champion_point_skill cps
            JOIN champion_point cp ON cp.id = cps.champion_point_id
            JOIN skill s ON s.id = cps.skill_id
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
    ChampionPointSkillImporter().run()


if __name__ == "__main__":
    main()
