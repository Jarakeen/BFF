from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ScribingReferenceImportSummary:
    grimoires: int
    scripts: int
    compatibility_rows: int
    sections: int
    revision_id: int | None


class UespScribingReferenceImporter:
    """Import normalized UESP Scribing reference data into the canonical DB.

    This importer deliberately stores source/provenance alongside normalized
    rows. It does not infer script effects or forbidden three-script
    combinations that the source does not explicitly provide.
    """

    SOURCE_KEY = "uesp:online:scribing"

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def load_payload(path: str | Path) -> dict[str, Any]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Scribing reference payload must be a JSON object")
        if not isinstance(payload.get("grimoires"), list):
            raise ValueError("Scribing reference payload is missing grimoires[]")
        if not isinstance(payload.get("scripts"), list):
            raise ValueError("Scribing reference payload is missing scripts[]")
        if not isinstance(payload.get("sections"), dict):
            raise ValueError("Scribing reference payload is missing sections{}")
        return payload

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS scribing_reference_source (
                source_key TEXT PRIMARY KEY,
                source_url TEXT NOT NULL,
                source_title TEXT NOT NULL DEFAULT '',
                revision_id INTEGER,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scribing_grimoire (
                name TEXT PRIMARY KEY,
                skill_line TEXT NOT NULL,
                requirement TEXT NOT NULL DEFAULT '',
                first_price_gold INTEGER,
                later_price_gold INTEGER,
                price_text TEXT NOT NULL DEFAULT '',
                uesp_path TEXT NOT NULL DEFAULT '',
                icon_url TEXT NOT NULL DEFAULT '',
                source_key TEXT NOT NULL,
                FOREIGN KEY (source_key) REFERENCES scribing_reference_source(source_key)
            );

            CREATE TABLE IF NOT EXISTS scribing_script (
                script_type TEXT NOT NULL CHECK (script_type IN ('focus','signature','affix')),
                name TEXT NOT NULL,
                effect_note TEXT NOT NULL DEFAULT '',
                requirement TEXT NOT NULL DEFAULT '',
                first_price_gold INTEGER,
                later_price_gold INTEGER,
                price_text TEXT NOT NULL DEFAULT '',
                uesp_path TEXT NOT NULL DEFAULT '',
                source_key TEXT NOT NULL,
                PRIMARY KEY (script_type, name),
                FOREIGN KEY (source_key) REFERENCES scribing_reference_source(source_key)
            );

            CREATE TABLE IF NOT EXISTS scribing_script_grimoire (
                script_type TEXT NOT NULL,
                script_name TEXT NOT NULL,
                grimoire_name TEXT NOT NULL,
                PRIMARY KEY (script_type, script_name, grimoire_name),
                FOREIGN KEY (script_type, script_name)
                    REFERENCES scribing_script(script_type, name) ON DELETE CASCADE,
                FOREIGN KEY (grimoire_name)
                    REFERENCES scribing_grimoire(name) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS scribing_reference_section (
                section_key TEXT PRIMARY KEY,
                heading TEXT NOT NULL,
                body_text TEXT NOT NULL,
                source_key TEXT NOT NULL,
                FOREIGN KEY (source_key) REFERENCES scribing_reference_source(source_key)
            );

            CREATE INDEX IF NOT EXISTS idx_scribing_script_type
                ON scribing_script(script_type, name COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_scribing_script_grimoire_name
                ON scribing_script_grimoire(grimoire_name, script_type);
            """
        )

    def run(self, *, source_path: str | Path) -> ScribingReferenceImportSummary:
        payload = self.load_payload(source_path)
        source = payload.get("source") or {}
        revision_id = source.get("revision_id")
        try:
            revision_id = int(revision_id) if revision_id is not None else None
        except (TypeError, ValueError):
            revision_id = None

        grimoires = payload["grimoires"]
        scripts = payload["scripts"]
        sections = payload["sections"]

        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            self._create_schema(connection)
            connection.execute(
                """
                INSERT INTO scribing_reference_source(
                    source_key, source_url, source_title, revision_id, imported_at
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_key) DO UPDATE SET
                    source_url = excluded.source_url,
                    source_title = excluded.source_title,
                    revision_id = excluded.revision_id,
                    imported_at = CURRENT_TIMESTAMP
                """,
                (
                    self.SOURCE_KEY,
                    str(source.get("source_url") or ""),
                    str(source.get("title") or ""),
                    revision_id,
                ),
            )

            grimoire_names: set[str] = set()
            for row in grimoires:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("name") or "").strip()
                skill_line = str(row.get("skill_line") or "").strip()
                if not name or not skill_line:
                    continue
                grimoire_names.add(name)
                connection.execute(
                    """
                    INSERT INTO scribing_grimoire(
                        name, skill_line, requirement,
                        first_price_gold, later_price_gold, price_text,
                        uesp_path, icon_url, source_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        skill_line = excluded.skill_line,
                        requirement = excluded.requirement,
                        first_price_gold = excluded.first_price_gold,
                        later_price_gold = excluded.later_price_gold,
                        price_text = excluded.price_text,
                        uesp_path = excluded.uesp_path,
                        icon_url = excluded.icon_url,
                        source_key = excluded.source_key
                    """,
                    (
                        name,
                        skill_line,
                        str(row.get("requirement") or ""),
                        row.get("first_price_gold"),
                        row.get("later_price_gold"),
                        str(row.get("price_text") or ""),
                        str(row.get("uesp_path") or ""),
                        str(row.get("icon_url") or ""),
                        self.SOURCE_KEY,
                    ),
                )

            compatibility_rows = 0
            represented_scripts: list[tuple[str, str]] = []
            for row in scripts:
                if not isinstance(row, dict):
                    continue
                script_type = str(row.get("script_type") or "").strip().casefold()
                name = str(row.get("name") or "").strip()
                if script_type not in {"focus", "signature", "affix"} or not name:
                    continue
                represented_scripts.append((script_type, name))
                connection.execute(
                    """
                    INSERT INTO scribing_script(
                        script_type, name, effect_note, requirement,
                        first_price_gold, later_price_gold, price_text,
                        uesp_path, source_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(script_type, name) DO UPDATE SET
                        effect_note = excluded.effect_note,
                        requirement = excluded.requirement,
                        first_price_gold = excluded.first_price_gold,
                        later_price_gold = excluded.later_price_gold,
                        price_text = excluded.price_text,
                        uesp_path = excluded.uesp_path,
                        source_key = excluded.source_key
                    """,
                    (
                        script_type,
                        name,
                        str(row.get("effect_note") or ""),
                        str(row.get("requirement") or ""),
                        row.get("first_price_gold"),
                        row.get("later_price_gold"),
                        str(row.get("price_text") or ""),
                        str(row.get("uesp_path") or ""),
                        self.SOURCE_KEY,
                    ),
                )
                connection.execute(
                    "DELETE FROM scribing_script_grimoire WHERE script_type = ? AND script_name = ?",
                    (script_type, name),
                )
                for grimoire in row.get("compatible_grimoires") or []:
                    grimoire = str(grimoire or "").strip()
                    if not grimoire or grimoire not in grimoire_names:
                        continue
                    connection.execute(
                        """
                        INSERT INTO scribing_script_grimoire(
                            script_type, script_name, grimoire_name
                        ) VALUES (?, ?, ?)
                        """,
                        (script_type, name, grimoire),
                    )
                    compatibility_rows += 1

            for key, row in sections.items():
                if not isinstance(row, dict):
                    continue
                connection.execute(
                    """
                    INSERT INTO scribing_reference_section(
                        section_key, heading, body_text, source_key
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(section_key) DO UPDATE SET
                        heading = excluded.heading,
                        body_text = excluded.body_text,
                        source_key = excluded.source_key
                    """,
                    (
                        str(key),
                        str(row.get("heading") or key),
                        str(row.get("body") or ""),
                        self.SOURCE_KEY,
                    ),
                )

            connection.commit()

        return ScribingReferenceImportSummary(
            grimoires=len(grimoire_names),
            scripts=len(represented_scripts),
            compatibility_rows=compatibility_rows,
            sections=len(sections),
            revision_id=revision_id,
        )
