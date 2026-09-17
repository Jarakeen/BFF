from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "eso.db"
DEFAULT_RUMORS_PATH = ROOT / "data" / "raw" / "uesp" / "rumors.htm"
DEFAULT_HINTS_PATH = ROOT / "data" / "raw" / "uesp" / "rumorhints.htm"


@dataclass
class Cell:
    text_parts: list[str] = field(default_factory=list)
    hrefs: list[str] = field(default_factory=list)
    image_sources: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.text_parts).split()).strip()


class UespTableParser(HTMLParser):
    """Parse the single ``#esologtable`` table emitted by UESP's ESO log viewer."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_target_table = False
        self.table_depth = 0
        self.current_row: list[Cell] | None = None
        self.current_cell: Cell | None = None
        self.headers: list[str] = []
        self.rows: list[dict[str, Cell]] = []
        self._row_is_header = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table":
            if self.in_target_table:
                self.table_depth += 1
            elif attributes.get("id") == "esologtable":
                self.in_target_table = True
                self.table_depth = 1
            return

        if not self.in_target_table:
            return

        if tag == "tr":
            self.current_row = []
            self._row_is_header = False
        elif tag in {"th", "td"} and self.current_row is not None:
            self.current_cell = Cell()
            self.current_row.append(self.current_cell)
            if tag == "th":
                self._row_is_header = True
        elif tag == "a" and self.current_cell is not None:
            href = attributes.get("href")
            if href:
                self.current_cell.hrefs.append(href)
        elif tag == "img" and self.current_cell is not None:
            src = attributes.get("src")
            if src:
                self.current_cell.image_sources.append(src)

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self.in_target_table:
            self.table_depth -= 1
            if self.table_depth <= 0:
                self.in_target_table = False
            return

        if not self.in_target_table:
            return

        if tag in {"th", "td"}:
            self.current_cell = None
        elif tag == "tr" and self.current_row is not None:
            cells = self.current_row
            if self._row_is_header:
                self.headers = [cell.text for cell in cells]
            elif self.headers and len(cells) == len(self.headers):
                self.rows.append(dict(zip(self.headers, cells)))
            self.current_row = None
            self.current_cell = None
            self._row_is_header = False

    def handle_data(self, data: str) -> None:
        if self.in_target_table and self.current_cell is not None:
            stripped = data.strip()
            if stripped:
                self.current_cell.text_parts.append(stripped)


def parse_uesp_table(path: Path) -> list[dict[str, Cell]]:
    parser = UespTableParser()
    parser.feed(path.read_text(encoding="utf-8"))
    if not parser.headers:
        raise ValueError(f"No UESP table headers found in {path}")
    if not parser.rows:
        raise ValueError(f"No UESP table rows found in {path}")
    return parser.rows


def _int(value: str, *, field_name: str, allow_blank: bool = False) -> int | None:
    value = value.strip()
    if not value and allow_blank:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {field_name}: {value!r}") from exc


def _cell(row: dict[str, Cell], name: str) -> Cell:
    try:
        return row[name]
    except KeyError as exc:
        raise ValueError(f"UESP table is missing expected column {name!r}") from exc


def _source_payload(row: dict[str, Cell]) -> str:
    payload = {
        key: {
            "text": cell.text,
            "hrefs": cell.hrefs,
            "image_sources": cell.image_sources,
        }
        for key, cell in row.items()
        if key
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _normalize_icon(cell: Cell) -> str:
    candidate = next(iter(cell.image_sources or cell.hrefs), "").strip()
    if candidate.startswith("//"):
        return "https:" + candidate
    return candidate


def _extract_book_id(row: dict[str, Cell]) -> int | None:
    direct = _cell(row, "book").text
    if direct:
        return _int(direct, field_name="book", allow_blank=True)

    for cell in row.values():
        for href in cell.hrefs:
            match = re.search(r"(?:[?&])bookId=(\d+)", href)
            if match:
                return int(match.group(1))
    return None


def _ensure_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migration (
            migration_key TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS collectible_rumor (
            id INTEGER PRIMARY KEY,
            rumor_type INTEGER NOT NULL,
            name TEXT NOT NULL,
            start_hint TEXT NOT NULL DEFAULT '',
            background_text TEXT NOT NULL DEFAULT '',
            complete_text TEXT NOT NULL DEFAULT '',
            declared_hint_count INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'UESP',
            source_raw_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS collectible_rumor_hint (
            id INTEGER PRIMARY KEY,
            rumor_id INTEGER NOT NULL,
            hint_index INTEGER NOT NULL,
            rumor_name TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            icon TEXT NOT NULL DEFAULT '',
            book_id INTEGER,
            source TEXT NOT NULL DEFAULT 'UESP',
            source_raw_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rumor_id) REFERENCES collectible_rumor(id) ON DELETE CASCADE,
            UNIQUE (rumor_id, hint_index)
        );

        CREATE INDEX IF NOT EXISTS idx_collectible_rumor_name
            ON collectible_rumor(name);
        CREATE INDEX IF NOT EXISTS idx_collectible_rumor_hint_parent
            ON collectible_rumor_hint(rumor_id, hint_index);
        CREATE INDEX IF NOT EXISTS idx_collectible_rumor_hint_book
            ON collectible_rumor_hint(book_id);
        """
    )


def _upsert_rumors(db: sqlite3.Connection, rows: Iterable[dict[str, Cell]]) -> dict[int, int]:
    declared_counts: dict[int, int] = {}
    for row in rows:
        rumor_id = _int(_cell(row, "id").text, field_name="rumor.id")
        rumor_type = _int(_cell(row, "type").text, field_name="rumor.type")
        declared_hint_count = _int(_cell(row, "numHints").text, field_name="rumor.numHints")
        assert rumor_id is not None
        assert rumor_type is not None
        assert declared_hint_count is not None

        name = html.unescape(_cell(row, "name").text).strip()
        if not name:
            raise ValueError(f"Rumor {rumor_id} is missing a name")

        declared_counts[rumor_id] = declared_hint_count
        db.execute(
            """
            INSERT INTO collectible_rumor (
                id,
                rumor_type,
                name,
                start_hint,
                background_text,
                complete_text,
                declared_hint_count,
                source,
                source_raw_json,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'UESP', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                rumor_type = excluded.rumor_type,
                name = excluded.name,
                start_hint = excluded.start_hint,
                background_text = excluded.background_text,
                complete_text = excluded.complete_text,
                declared_hint_count = excluded.declared_hint_count,
                source = excluded.source,
                source_raw_json = excluded.source_raw_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                rumor_id,
                rumor_type,
                name,
                html.unescape(_cell(row, "startHint").text),
                html.unescape(_cell(row, "backgroundText").text),
                html.unescape(_cell(row, "completeText").text),
                declared_hint_count,
                _source_payload(row),
            ),
        )
    return declared_counts


def _upsert_hints(
    db: sqlite3.Connection,
    rows: Iterable[dict[str, Cell]],
    valid_rumor_ids: set[int],
) -> dict[int, int]:
    actual_counts: dict[int, int] = {rumor_id: 0 for rumor_id in valid_rumor_ids}
    seen_positions: set[tuple[int, int]] = set()

    for row in rows:
        hint_id = _int(_cell(row, "id").text, field_name="hint.id")
        rumor_id = _int(_cell(row, "rumorId").text, field_name="hint.rumorId")
        hint_index = _int(_cell(row, "hintIndex").text, field_name="hint.hintIndex")
        assert hint_id is not None
        assert rumor_id is not None
        assert hint_index is not None

        if rumor_id not in valid_rumor_ids:
            raise ValueError(f"Hint {hint_id} references missing rumor {rumor_id}")

        position = (rumor_id, hint_index)
        if position in seen_positions:
            raise ValueError(f"Duplicate hint position rumor={rumor_id} index={hint_index}")
        seen_positions.add(position)
        actual_counts[rumor_id] += 1

        rumor_name = html.unescape(_cell(row, "rumorName").text).strip()
        parent_name = db.execute(
            "SELECT name FROM collectible_rumor WHERE id = ?",
            (rumor_id,),
        ).fetchone()[0]
        if rumor_name and rumor_name != parent_name:
            raise ValueError(
                f"Hint {hint_id} rumor name mismatch: {rumor_name!r} != {parent_name!r}"
            )

        db.execute(
            """
            INSERT INTO collectible_rumor_hint (
                id,
                rumor_id,
                hint_index,
                rumor_name,
                name,
                description,
                icon,
                book_id,
                source,
                source_raw_json,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'UESP', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                rumor_id = excluded.rumor_id,
                hint_index = excluded.hint_index,
                rumor_name = excluded.rumor_name,
                name = excluded.name,
                description = excluded.description,
                icon = excluded.icon,
                book_id = excluded.book_id,
                source = excluded.source,
                source_raw_json = excluded.source_raw_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                hint_id,
                rumor_id,
                hint_index,
                rumor_name or parent_name,
                html.unescape(_cell(row, "name").text),
                html.unescape(_cell(row, "description").text),
                _normalize_icon(_cell(row, "icon")),
                _extract_book_id(row),
                _source_payload(row),
            ),
        )

    return actual_counts


def import_rumors(
    db_path: Path,
    rumors_path: Path,
    hints_path: Path,
) -> tuple[int, int]:
    rumor_rows = parse_uesp_table(rumors_path)
    hint_rows = parse_uesp_table(hints_path)

    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys = ON")
    try:
        db.execute("BEGIN")
        _ensure_schema(db)
        declared_counts = _upsert_rumors(db, rumor_rows)
        actual_counts = _upsert_hints(db, hint_rows, set(declared_counts))

        mismatches = {
            rumor_id: (declared_counts[rumor_id], actual_counts.get(rumor_id, 0))
            for rumor_id in declared_counts
            if declared_counts[rumor_id] != actual_counts.get(rumor_id, 0)
        }
        if mismatches:
            details = ", ".join(
                f"{rumor_id}: declared={declared} actual={actual}"
                for rumor_id, (declared, actual) in sorted(mismatches.items())
            )
            raise ValueError(f"Rumor hint-count mismatch: {details}")

        db.execute(
            "INSERT OR REPLACE INTO schema_migration(migration_key) VALUES ('collectible_rumors_v1')"
        )
        db.commit()
        return len(rumor_rows), len(hint_rows)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import UESP rumor and rumor-hint HTML into FoundryDock collectibles data."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--rumors-html", type=Path, default=DEFAULT_RUMORS_PATH)
    parser.add_argument("--hints-html", type=Path, default=DEFAULT_HINTS_PATH)
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    for path, label in (
        (args.db, "database"),
        (args.rumors_html, "rumors HTML"),
        (args.hints_html, "rumor hints HTML"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{label} not found: {path}")

    rumor_count, hint_count = import_rumors(
        args.db,
        args.rumors_html,
        args.hints_html,
    )
    print("=" * 64)
    print(" FoundryDock UESP Rumor Import")
    print("=" * 64)
    print(f"Database:     {args.db}")
    print(f"Rumors:       {rumor_count:,}")
    print(f"Rumor hints:  {hint_count:,}")
    print("Mode:         additive upsert; existing unrelated data preserved")
    print("STATUS: IMPORT COMPLETE")


if __name__ == "__main__":
    main()
