from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


_ESO_COLOR_OPEN_RE = re.compile(r"\|c[0-9a-fA-F]{6}", re.IGNORECASE)
_ESO_COLOR_RESET_RE = re.compile(r"\|r", re.IGNORECASE)


def clean_eso_markup(value: object) -> str:
    """Remove ESO client color tags while preserving the text/value they wrap."""
    text = html.unescape(str(value or ""))
    text = _ESO_COLOR_OPEN_RE.sub("", text)
    text = _ESO_COLOR_RESET_RE.sub("", text)
    return " ".join(text.split())


@dataclass(frozen=True)
class CraftedScriptDescriptionRow:
    source_row_id: int
    crafted_ability_id: int
    script_id: int
    class_id: int
    ability_id: int
    name: str
    description_raw: str
    description: str


@dataclass(frozen=True)
class CraftedScriptDescriptionImportSummary:
    rows: int
    crafted_abilities: int
    scripts: int
    classes: int
    abilities: int
    names: int
    source_key: str


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_target_table = False
        self.in_row = False
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs = dict(attrs)
        if tag == "table" and attrs.get("id") == "esologtable":
            self.in_target_table = True
        elif self.in_target_table and tag == "tr":
            self.in_row = True
            self.current_row = []
        elif self.in_row and tag in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []
        elif self.in_cell and tag == "br":
            self.current_cell.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.in_cell and tag in {"td", "th"}:
            self.current_row.append("".join(self.current_cell).strip())
            self.current_cell = []
            self.in_cell = False
        elif self.in_row and tag == "tr":
            if self.current_row:
                self.rows.append(self.current_row)
            self.current_row = []
            self.in_row = False
        elif self.in_target_table and tag == "table":
            self.in_target_table = False

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current_cell.append(data)


class UespCraftedScriptDescriptionImporter:
    SOURCE_KEY = "uesp:esolog:craftedScriptDescriptions51pts"
    SOURCE_RECORD = "craftedScriptDescriptions51pts"
    SOURCE_TITLE = "ESO Log Data Viewer: Update 51 PTS Crafted Script Descriptions"
    GAME_UPDATE = 51
    CHANNEL = "PTS"

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def parse_html(path: str | Path) -> list[CraftedScriptDescriptionRow]:
        source = Path(path)
        parser = _TableParser()
        parser.feed(source.read_text(encoding="utf-8", errors="replace"))
        rows: list[CraftedScriptDescriptionRow] = []
        for cells in parser.rows:
            if len(cells) < 8:
                continue
            try:
                source_row_id = int(cells[1].strip())
                crafted_ability_id = int(cells[2].strip())
                script_id = int(cells[3].strip())
                class_id = int(cells[4].strip())
                ability_id = int(cells[5].strip())
            except (TypeError, ValueError):
                continue
            raw_description = html.unescape(cells[7]).strip()
            rows.append(
                CraftedScriptDescriptionRow(
                    source_row_id=source_row_id,
                    crafted_ability_id=crafted_ability_id,
                    script_id=script_id,
                    class_id=class_id,
                    ability_id=ability_id,
                    name=clean_eso_markup(cells[6]),
                    description_raw=raw_description,
                    description=clean_eso_markup(raw_description),
                )
            )
        return rows

    @staticmethod
    def normalized_payload(path: str | Path) -> dict:
        source = Path(path)
        rows = UespCraftedScriptDescriptionImporter.parse_html(source)
        return {
            "source": {
                "source_key": UespCraftedScriptDescriptionImporter.SOURCE_KEY,
                "record": UespCraftedScriptDescriptionImporter.SOURCE_RECORD,
                "title": UespCraftedScriptDescriptionImporter.SOURCE_TITLE,
                "game_update": UespCraftedScriptDescriptionImporter.GAME_UPDATE,
                "channel": UespCraftedScriptDescriptionImporter.CHANNEL,
                "source_file": source.name,
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "row_count": len(rows),
            },
            "rows": [row.__dict__ for row in rows],
        }

    @staticmethod
    def write_normalized_json(source_path: str | Path, target_path: str | Path) -> Path:
        target = Path(target_path)
        payload = UespCraftedScriptDescriptionImporter.normalized_payload(source_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return target

    @staticmethod
    def ensure_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS scribing_crafted_description_source (
                source_key TEXT PRIMARY KEY,
                source_record TEXT NOT NULL,
                source_title TEXT NOT NULL DEFAULT '',
                game_update INTEGER,
                channel TEXT NOT NULL DEFAULT '',
                source_file TEXT NOT NULL DEFAULT '',
                source_sha256 TEXT NOT NULL DEFAULT '',
                row_count INTEGER NOT NULL DEFAULT 0,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scribing_crafted_script_description (
                source_key TEXT NOT NULL,
                source_row_id INTEGER NOT NULL,
                crafted_ability_id INTEGER NOT NULL,
                script_id INTEGER NOT NULL,
                class_id INTEGER NOT NULL DEFAULT 0,
                ability_id INTEGER NOT NULL DEFAULT 0,
                name TEXT NOT NULL DEFAULT '',
                description_raw TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (source_key, source_row_id),
                FOREIGN KEY (source_key)
                    REFERENCES scribing_crafted_description_source(source_key)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_scribing_crafted_description_combo
                ON scribing_crafted_script_description(crafted_ability_id, script_id, class_id);
            CREATE INDEX IF NOT EXISTS idx_scribing_crafted_description_ability
                ON scribing_crafted_script_description(ability_id);
            CREATE INDEX IF NOT EXISTS idx_scribing_crafted_description_name
                ON scribing_crafted_script_description(name COLLATE NOCASE);
            """
        )

    def run(self, *, source_path: str | Path) -> CraftedScriptDescriptionImportSummary:
        source = Path(source_path)
        rows = self.parse_html(source)
        if not rows:
            raise ValueError(f"No crafted-script description rows found in {source}")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()

        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            self.ensure_schema(connection)
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
                    self.SOURCE_KEY,
                    self.SOURCE_RECORD,
                    self.SOURCE_TITLE,
                    self.GAME_UPDATE,
                    self.CHANNEL,
                    source.name,
                    digest,
                    len(rows),
                ),
            )
            connection.execute(
                "DELETE FROM scribing_crafted_script_description WHERE source_key = ?",
                (self.SOURCE_KEY,),
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
                        self.SOURCE_KEY,
                        row.source_row_id,
                        row.crafted_ability_id,
                        row.script_id,
                        row.class_id,
                        row.ability_id,
                        row.name,
                        row.description_raw,
                        row.description,
                    )
                    for row in rows
                ],
            )
            connection.commit()

        return CraftedScriptDescriptionImportSummary(
            rows=len(rows),
            crafted_abilities=len({row.crafted_ability_id for row in rows}),
            scripts=len({row.script_id for row in rows}),
            classes=len({row.class_id for row in rows}),
            abilities=len({row.ability_id for row in rows}),
            names=len({row.name for row in rows}),
            source_key=self.SOURCE_KEY,
        )
