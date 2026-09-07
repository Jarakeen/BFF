from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from importers.scribing_crafted_description_importer import (
    UespCraftedScriptDescriptionImporter,
)


@dataclass(frozen=True)
class U51ScribingCatalogImportSummary:
    scripts: int
    skills: int
    skill_abilities: int
    compatibility_rows: int
    descriptions: int
    source_key: str


class U51ScribingCatalogImporter:
    """Import the normalized UESP Update 51 PTS scribing catalog."""

    SOURCE_KEY = "uesp:esolog:u51pts:scribing"

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def load_payload(path: str | Path) -> dict:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("U51 scribing catalog must be a JSON object")
        for key in ("source", "scripts", "skills", "descriptions"):
            if key not in payload:
                raise ValueError(f"U51 scribing catalog is missing {key}")
        if not isinstance(payload["scripts"], list):
            raise ValueError("U51 scribing catalog scripts must be a list")
        if not isinstance(payload["skills"], list):
            raise ValueError("U51 scribing catalog skills must be a list")
        if not isinstance(payload["descriptions"], list):
            raise ValueError("U51 scribing catalog descriptions must be a list")
        return payload

    @staticmethod
    def ensure_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS scribing_u51_source (
                source_key TEXT PRIMARY KEY,
                game_update INTEGER NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                scripts_record TEXT NOT NULL DEFAULT '',
                skills_record TEXT NOT NULL DEFAULT '',
                descriptions_record TEXT NOT NULL DEFAULT '',
                scripts_sha256 TEXT NOT NULL DEFAULT '',
                skills_sha256 TEXT NOT NULL DEFAULT '',
                descriptions_sha256 TEXT NOT NULL DEFAULT '',
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scribing_u51_script (
                source_key TEXT NOT NULL,
                script_id INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                script_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                hint TEXT NOT NULL DEFAULT '',
                icon TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (source_key, script_id),
                FOREIGN KEY (source_key) REFERENCES scribing_u51_source(source_key)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS scribing_u51_crafted_skill (
                source_key TEXT NOT NULL,
                crafted_ability_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                skill_type INTEGER NOT NULL DEFAULT 0,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                hint TEXT NOT NULL DEFAULT '',
                icon TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (source_key, crafted_ability_id),
                FOREIGN KEY (source_key) REFERENCES scribing_u51_source(source_key)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS scribing_u51_crafted_skill_ability (
                source_key TEXT NOT NULL,
                crafted_ability_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                PRIMARY KEY (source_key, crafted_ability_id, ability_id),
                FOREIGN KEY (source_key, crafted_ability_id)
                    REFERENCES scribing_u51_crafted_skill(source_key, crafted_ability_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS scribing_u51_skill_script (
                source_key TEXT NOT NULL,
                crafted_ability_id INTEGER NOT NULL,
                script_id INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                PRIMARY KEY (source_key, crafted_ability_id, script_id, slot),
                FOREIGN KEY (source_key, crafted_ability_id)
                    REFERENCES scribing_u51_crafted_skill(source_key, crafted_ability_id)
                    ON DELETE CASCADE,
                FOREIGN KEY (source_key, script_id)
                    REFERENCES scribing_u51_script(source_key, script_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_scribing_u51_script_name
                ON scribing_u51_script(name COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_scribing_u51_skill_name
                ON scribing_u51_crafted_skill(name COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_scribing_u51_skill_script_lookup
                ON scribing_u51_skill_script(crafted_ability_id, slot, script_id);
            """
        )
        UespCraftedScriptDescriptionImporter.ensure_schema(connection)

    @staticmethod
    def _script_type(slot: int) -> str:
        return {1: "focus", 2: "signature", 3: "affix"}.get(int(slot), "unknown")

    def run(self, *, catalog_path: str | Path) -> U51ScribingCatalogImportSummary:
        payload = self.load_payload(catalog_path)
        source = dict(payload["source"])
        source_key = self.SOURCE_KEY

        scripts = [row for row in payload["scripts"] if isinstance(row, dict)]
        skills = [row for row in payload["skills"] if isinstance(row, dict)]
        descriptions = [row for row in payload["descriptions"] if isinstance(row, dict)]

        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            self.ensure_schema(connection)

            connection.execute(
                """
                INSERT INTO scribing_u51_source(
                    source_key, game_update, channel,
                    scripts_record, skills_record, descriptions_record,
                    scripts_sha256, skills_sha256, descriptions_sha256, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_key) DO UPDATE SET
                    game_update = excluded.game_update,
                    channel = excluded.channel,
                    scripts_record = excluded.scripts_record,
                    skills_record = excluded.skills_record,
                    descriptions_record = excluded.descriptions_record,
                    scripts_sha256 = excluded.scripts_sha256,
                    skills_sha256 = excluded.skills_sha256,
                    descriptions_sha256 = excluded.descriptions_sha256,
                    imported_at = CURRENT_TIMESTAMP
                """,
                (
                    source_key,
                    int(source.get("game_update") or 51),
                    str(source.get("channel") or "PTS"),
                    str(source.get("scripts_record") or ""),
                    str(source.get("skills_record") or ""),
                    str(source.get("description_record") or ""),
                    str(source.get("scripts_sha256") or ""),
                    str(source.get("skills_sha256") or ""),
                    str(source.get("description_sha256") or ""),
                ),
            )

            for table in (
                "scribing_u51_skill_script",
                "scribing_u51_crafted_skill_ability",
                "scribing_u51_crafted_skill",
                "scribing_u51_script",
            ):
                connection.execute(f"DELETE FROM {table} WHERE source_key = ?", (source_key,))

            script_rows = []
            for row in scripts:
                script_id = int(row["script_id"])
                slot = int(row["slot"])
                script_rows.append(
                    (
                        source_key,
                        script_id,
                        slot,
                        self._script_type(slot),
                        str(row.get("name") or "").strip(),
                        str(row.get("description") or "").strip(),
                        str(row.get("hint") or "").strip(),
                        str(row.get("icon") or "").strip(),
                    )
                )
            connection.executemany(
                """
                INSERT INTO scribing_u51_script(
                    source_key, script_id, slot, script_type,
                    name, description, hint, icon
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                script_rows,
            )

            skill_rows = []
            ability_rows = []
            compatibility_rows = []
            for row in skills:
                crafted_id = int(row["crafted_ability_id"])
                skill_rows.append(
                    (
                        source_key,
                        crafted_id,
                        int(row.get("ability_id") or 0),
                        int(row.get("skill_type") or 0),
                        str(row.get("name") or "").strip(),
                        str(row.get("description") or "").strip(),
                        str(row.get("hint") or "").strip(),
                        str(row.get("icon") or "").strip(),
                    )
                )
                for ability_id in row.get("ability_ids") or []:
                    ability_rows.append((source_key, crafted_id, int(ability_id)))
                for slot, key in (
                    (1, "focus_script_ids"),
                    (2, "signature_script_ids"),
                    (3, "affix_script_ids"),
                ):
                    for script_id in row.get(key) or []:
                        compatibility_rows.append(
                            (source_key, crafted_id, int(script_id), slot)
                        )

            connection.executemany(
                """
                INSERT INTO scribing_u51_crafted_skill(
                    source_key, crafted_ability_id, ability_id, skill_type,
                    name, description, hint, icon
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                skill_rows,
            )
            connection.executemany(
                """
                INSERT INTO scribing_u51_crafted_skill_ability(
                    source_key, crafted_ability_id, ability_id
                ) VALUES (?, ?, ?)
                """,
                ability_rows,
            )
            connection.executemany(
                """
                INSERT INTO scribing_u51_skill_script(
                    source_key, crafted_ability_id, script_id, slot
                ) VALUES (?, ?, ?, ?)
                """,
                compatibility_rows,
            )

            desc_source_key = UespCraftedScriptDescriptionImporter.SOURCE_KEY
            connection.execute(
                """
                INSERT INTO scribing_crafted_description_source(
                    source_key, source_record, source_title, game_update, channel,
                    source_file, source_sha256, row_count, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_key) DO UPDATE SET
                    source_record = excluded.source_record,
                    source_title = excluded.source_title,
                    game_update = excluded.game_update,
                    channel = excluded.channel,
                    source_file = excluded.source_file,
                    source_sha256 = excluded.source_sha256,
                    row_count = excluded.row_count,
                    imported_at = CURRENT_TIMESTAMP
                """,
                (
                    desc_source_key,
                    str(source.get("description_record") or "craftedScriptDescriptions51pts"),
                    "ESO Log Data Viewer: Update 51 PTS Crafted Script Descriptions",
                    int(source.get("game_update") or 51),
                    str(source.get("channel") or "PTS"),
                    "bundled:data/scribing/u51_pts_catalog.json",
                    str(source.get("description_sha256") or ""),
                    len(descriptions),
                ),
            )
            connection.execute(
                "DELETE FROM scribing_crafted_script_description WHERE source_key = ?",
                (desc_source_key,),
            )
            connection.executemany(
                """
                INSERT INTO scribing_crafted_script_description(
                    source_key, source_row_id, crafted_ability_id, script_id,
                    class_id, ability_id, name, description_raw, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        desc_source_key,
                        int(row["source_row_id"]),
                        int(row["crafted_ability_id"]),
                        int(row["script_id"]),
                        int(row.get("class_id") or 0),
                        int(row.get("ability_id") or 0),
                        str(row.get("name") or "").strip(),
                        str(row.get("description_raw") or "").strip(),
                        str(row.get("description") or "").strip(),
                    )
                    for row in descriptions
                ],
            )
            connection.commit()

        return U51ScribingCatalogImportSummary(
            scripts=len(script_rows),
            skills=len(skill_rows),
            skill_abilities=len(ability_rows),
            compatibility_rows=len(compatibility_rows),
            descriptions=len(descriptions),
            source_key=source_key,
        )
