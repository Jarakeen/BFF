"""Import explicit ESO-Hub Champion Point -> skill relationships.

Crawler records that contain ``skill_rank_id`` are persisted at rank/morph scope
in ``champion_point_skill_rank``. Older/base-skill harvests remain readable via
``champion_point_skill``. No CP applicability is inferred from descriptions.
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
    if value is None:
        return ""
    text = str(value).strip().lower()
    for old, new in {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
    }.items():
        text = text.replace(old, new)
    return " ".join(text.split())


class ChampionPointSkillImporter:
    def __init__(self, database: Path = DATABASE, source_file: Path = SOURCE_FILE) -> None:
        self.database_path = Path(database)
        self.source_file = Path(source_file)
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
            self._ensure_tables()
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
            raise FileNotFoundError(f"Champion Point skill source file was not found:\n{self.source_file}")
        data = json.loads(self.source_file.read_text(encoding="utf-8"))
        self.records = self._extract_records(data)
        if not self.records:
            raise ValueError("No skill -> Champion Point records were found in the source.")

    @staticmethod
    def _extract_records(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [record for record in data if isinstance(record, dict)]
        if not isinstance(data, dict):
            return []
        skills = data.get("skills")
        if isinstance(skills, list):
            return [record for record in skills if isinstance(record, dict)]
        result: list[dict[str, Any]] = []
        for skill_name, cp_values in data.items():
            if isinstance(cp_values, list):
                result.append({"skill": skill_name, "championPoints": cp_values})
        return result

    def _ensure_tables(self) -> None:
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
        legacy_columns = {row[1] for row in self.db.execute("PRAGMA table_info(champion_point_skill)")}
        for column, sql_type in {
            "condition": "TEXT",
            "source_url": "TEXT",
            "raw_source": "TEXT",
            "source": "TEXT",
            "confidence": "TEXT",
            "relationship": "TEXT",
        }.items():
            if column not in legacy_columns:
                self.db.execute(f'ALTER TABLE champion_point_skill ADD COLUMN "{column}" {sql_type}')

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS champion_point_skill_rank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                champion_point_id INTEGER NOT NULL,
                skill_rank_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER,
                relationship TEXT NOT NULL DEFAULT 'Buffs',
                condition TEXT,
                source TEXT,
                confidence TEXT,
                source_url TEXT,
                raw_source TEXT,
                UNIQUE (champion_point_id, skill_rank_id)
            )
            """
        )
        self.db.commit()

    def _load_skill_lookup(self) -> None:
        assert self.db is not None
        rows = self.db.execute(
            "SELECT id, name, index_name, base_ability_id FROM skill WHERE name IS NOT NULL"
        ).fetchall()
        for skill_id, name, index_name, base_ability_id in rows:
            entry = {
                "id": int(skill_id),
                "name": name,
                "index_name": index_name,
                "base_ability_id": base_ability_id,
            }
            for candidate in (name, index_name):
                key = normalize_name(candidate)
                if key:
                    self.skill_lookup.setdefault(key, []).append(entry)

    def _load_cp_lookup(self) -> None:
        assert self.db is not None
        rows = self.db.execute(
            "SELECT id, name, ability_id, skill_id, discipline_index FROM champion_point WHERE name IS NOT NULL"
        ).fetchall()
        for cp_id, name, ability_id, skill_id, discipline_index in rows:
            key = normalize_name(name)
            if key:
                self.cp_lookup.setdefault(key, []).append(
                    {
                        "id": int(cp_id),
                        "name": name,
                        "ability_id": ability_id,
                        "skill_id": skill_id,
                        "discipline_index": discipline_index,
                    }
                )

    def _rank_identity(self, record: dict[str, Any]) -> dict[str, int] | None:
        assert self.db is not None
        raw = record.get("skill_rank_id")
        if raw is None:
            return None
        try:
            rank_id = int(raw)
        except (TypeError, ValueError):
            return None
        row = self.db.execute(
            "SELECT id, skill_id, ability_id FROM skill_rank WHERE id = ?",
            (rank_id,),
        ).fetchone()
        if row is None:
            return None
        return {"skill_rank_id": int(row[0]), "skill_id": int(row[1]), "ability_id": int(row[2])}

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

            rank_identity = self._rank_identity(record)
            if record.get("skill_rank_id") is not None and rank_identity is None:
                self.unmatched_skills.append(f"{skill_name} [invalid skill_rank_id]")
                continue

            if rank_identity is not None:
                skill_matches = [{"id": rank_identity["skill_id"]}]
            else:
                explicit_skill_id = record.get("skill_id")
                skill_matches: list[dict[str, Any]] = []
                if explicit_skill_id is not None:
                    try:
                        wanted = int(explicit_skill_id)
                    except (TypeError, ValueError):
                        wanted = -1
                    if any(skill["id"] == wanted for values in self.skill_lookup.values() for skill in values):
                        skill_matches = [{"id": wanted}]
                if not skill_matches:
                    skill_matches = self.skill_lookup.get(normalize_name(skill_name), [])

            if not skill_matches:
                self.unmatched_skills.append(skill_name)
                continue
            if len(skill_matches) > 1:
                self.ambiguous_skills.append(skill_name)

            source_url = str(record.get("url") or "").strip() or None
            for skill in skill_matches:
                for cp_entry in cp_entries:
                    cp_name = cp_entry["name"]
                    cp_matches = self.cp_lookup.get(normalize_name(cp_name), [])
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
                                "skill_id": int(skill["id"]),
                                "skill_rank_id": rank_identity["skill_rank_id"] if rank_identity else None,
                                "ability_id": rank_identity["ability_id"] if rank_identity else None,
                                "relationship": "Buffs",
                                "condition": condition,
                                "source": source,
                                "confidence": "Explicit",
                                "source_url": source_url,
                                "raw_source": raw_source,
                            }
                        )

    @staticmethod
    def _get_skill_name(record: dict[str, Any]) -> str | None:
        for key in ("skill_name", "skill", "skillName", "name", "title"):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _get_cp_entries(record: dict[str, Any]) -> list[dict[str, str | None]]:
        for key in ("championPoints", "champion_points", "championPoint", "champion_point", "cp", "cps"):
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
                name = next(
                    (
                        str(item[k]).strip()
                        for k in ("champion_point_name", "championPointName", "name", "champion_point", "championPoint")
                        if isinstance(item.get(k), str) and str(item[k]).strip()
                    ),
                    "",
                )
                if name:
                    result.append(
                        {
                            "name": name,
                            "condition": str(item.get("condition") or "").strip() or None,
                            "source": str(item.get("source") or "").strip() or None,
                        }
                    )
            return result
        return []

    def _insert_relationships(self) -> None:
        assert self.db is not None
        for row in self.relationship_rows:
            if row["skill_rank_id"] is not None:
                table = "champion_point_skill_rank"
                key_column = "skill_rank_id"
                key_value = row["skill_rank_id"]
                existing = self.db.execute(
                    f"SELECT id FROM {table} WHERE champion_point_id=? AND {key_column}=?",
                    (row["champion_point_id"], key_value),
                ).fetchone()
                values = (
                    row["skill_id"], row["ability_id"], row["relationship"], row["condition"],
                    row["source"], row["confidence"], row["source_url"], row["raw_source"],
                )
                if existing:
                    self.db.execute(
                        f"""UPDATE {table} SET skill_id=?, ability_id=?, relationship=?, condition=?,
                            source=?, confidence=?, source_url=?, raw_source=? WHERE id=?""",
                        values + (existing[0],),
                    )
                    self.updated += 1
                else:
                    self.db.execute(
                        f"""INSERT INTO {table} (
                            champion_point_id, skill_rank_id, skill_id, ability_id, relationship,
                            condition, source, confidence, source_url, raw_source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (row["champion_point_id"], row["skill_rank_id"]) + values,
                    )
                    self.inserted += 1
                continue

            existing = self.db.execute(
                "SELECT id FROM champion_point_skill WHERE champion_point_id=? AND skill_id=?",
                (row["champion_point_id"], row["skill_id"]),
            ).fetchone()
            values = (
                row["relationship"], row["condition"], row["source"], row["confidence"],
                row["source_url"], row["raw_source"],
            )
            if existing:
                self.db.execute(
                    """UPDATE champion_point_skill SET relationship=?, condition=?, source=?, confidence=?,
                        source_url=?, raw_source=? WHERE id=?""",
                    values + (existing[0],),
                )
                self.updated += 1
            else:
                self.db.execute(
                    """INSERT INTO champion_point_skill (
                        champion_point_id, skill_id, relationship, condition, source,
                        confidence, source_url, raw_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row["champion_point_id"], row["skill_id"]) + values,
                )
                self.inserted += 1

    def _report(self) -> None:
        assert self.db is not None
        legacy = self.db.execute("SELECT COUNT(*) FROM champion_point_skill").fetchone()[0]
        ranked = self.db.execute("SELECT COUNT(*) FROM champion_point_skill_rank").fetchone()[0]
        print()
        print("=" * 49)
        print(" Champion Point -> Skill Import Complete")
        print("=" * 49)
        print()
        print(f"Source skill records:       {len(self.records):,}")
        print(f"Relationships parsed:       {len(self.relationship_rows):,}")
        print(f"Links inserted:             {self.inserted:,}")
        print(f"Links updated:              {self.updated:,}")
        print(f"Records skipped:            {self.skipped:,}")
        print(f"Legacy base-skill links:    {legacy:,}")
        print(f"Rank/morph-specific links:  {ranked:,}")
        print()
        print("=== UNMATCHED SKILLS ===")
        print("\n".join(sorted(set(self.unmatched_skills), key=str.lower)) if self.unmatched_skills else "(none)")
        print()
        print("=== UNMATCHED CHAMPION POINTS ===")
        print("\n".join(sorted(set(self.unmatched_cp), key=str.lower)) if self.unmatched_cp else "(none)")
        print()
        print("=== AMBIGUOUS SKILLS ===")
        print("\n".join(sorted(set(self.ambiguous_skills), key=str.lower)) if self.ambiguous_skills else "(none)")
        print()


def main() -> None:
    ChampionPointSkillImporter().run()


if __name__ == "__main__":
    main()
