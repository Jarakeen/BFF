from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _canonical_id(title: str, body: str) -> int:
    payload = f"{_normalize_text(title)}\x1f{_normalize_text(body)}".encode("utf-8")
    # 60-bit deterministic positive integer. Stable across imports and safe for SQLite INTEGER.
    return int(hashlib.sha256(payload).hexdigest()[:15], 16)


@dataclass(frozen=True)
class LorebookImportSummary:
    source_records: int
    lore_source_records: int
    canonical_lorebooks: int
    collapsed_occurrences: int
    unresolved: tuple[str, ...]


class UespLorebookImporter:
    """Import UESP book rows marked as lore into a profile-trackable catalog.

    A logical lorebook is identified by normalized title + full body text. This
    deliberately keeps same-title/different-text works separate while collapsing
    repeated world occurrences of the same readable work. Every source row is
    retained in source_raw_json for provenance.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def load_export(path: str | Path) -> list[dict[str, Any]]:
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected an object in {source}")
        records = payload.get("book")
        if not isinstance(records, list):
            raise ValueError(f"Expected a book list in {source}")
        if any(not isinstance(record, dict) for record in records):
            raise ValueError(f"Non-object records found in {source}")
        declared = payload.get("numRecords")
        if declared not in (None, "") and int(declared) != len(records):
            raise ValueError(
                f"numRecords={declared} does not match book={len(records)} in {source}"
            )
        return list(records)

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS lorebook (
                lorebook_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                icon TEXT,
                skill TEXT,
                primary_book_id INTEGER,
                primary_log_id INTEGER,
                category_index INTEGER,
                collection_index INTEGER,
                book_index INTEGER,
                source_occurrence_count INTEGER NOT NULL DEFAULT 1,
                source_raw_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_lorebook_title
                ON lorebook(title COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_lorebook_collection
                ON lorebook(category_index, collection_index, book_index);

            CREATE TABLE IF NOT EXISTS lorebook_progress (
                profile_name TEXT NOT NULL,
                lorebook_id INTEGER NOT NULL,
                learned INTEGER NOT NULL DEFAULT 0 CHECK (learned IN (0, 1)),
                learned_on TEXT,
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (profile_name, lorebook_id),
                FOREIGN KEY (lorebook_id) REFERENCES lorebook(lorebook_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_lorebook_progress_profile
                ON lorebook_progress(profile_name, learned);
            """
        )

    def run(self, *, books_path: str | Path) -> LorebookImportSummary:
        records = self.load_export(books_path)
        lore_rows = [row for row in records if str(row.get("isLore") or "") == "1"]
        unresolved: list[str] = []
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for row in lore_rows:
            title = str(row.get("title") or "").strip()
            body = str(row.get("body") or "").strip()
            if not title:
                unresolved.append(f"Lore row {row.get('id')!r} has no title")
                continue
            grouped[(_normalize_text(title), _normalize_text(body))].append(row)

        seen_ids: dict[int, tuple[str, str]] = {}
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            self._create_schema(connection)

            for signature, variants in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1])):
                variants.sort(key=lambda row: int(row.get("id") or 0))
                canonical = variants[0]
                title = str(canonical.get("title") or "").strip()
                body = str(canonical.get("body") or "").strip()
                lorebook_id = _canonical_id(title, body)
                previous = seen_ids.get(lorebook_id)
                if previous is not None and previous != signature:
                    unresolved.append(f"Canonical hash collision for lorebook {title!r}")
                    continue
                seen_ids[lorebook_id] = signature

                def as_int(name: str) -> int | None:
                    try:
                        return int(canonical.get(name))
                    except (TypeError, ValueError):
                        return None

                connection.execute(
                    """
                    INSERT INTO lorebook (
                        lorebook_id, title, body, icon, skill,
                        primary_book_id, primary_log_id,
                        category_index, collection_index, book_index,
                        source_occurrence_count, source_raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(lorebook_id) DO UPDATE SET
                        title = excluded.title,
                        body = excluded.body,
                        icon = excluded.icon,
                        skill = excluded.skill,
                        primary_book_id = excluded.primary_book_id,
                        primary_log_id = excluded.primary_log_id,
                        category_index = excluded.category_index,
                        collection_index = excluded.collection_index,
                        book_index = excluded.book_index,
                        source_occurrence_count = excluded.source_occurrence_count,
                        source_raw_json = excluded.source_raw_json
                    """,
                    (
                        lorebook_id,
                        title,
                        body,
                        str(canonical.get("icon") or ""),
                        str(canonical.get("skill") or ""),
                        as_int("bookId"),
                        as_int("logId"),
                        as_int("categoryIndex"),
                        as_int("collectionIndex"),
                        as_int("bookIndex"),
                        len(variants),
                        json.dumps(variants, ensure_ascii=False),
                    ),
                )
            connection.commit()

        return LorebookImportSummary(
            source_records=len(records),
            lore_source_records=len(lore_rows),
            canonical_lorebooks=len(grouped),
            collapsed_occurrences=len(lore_rows) - len(grouped),
            unresolved=tuple(unresolved),
        )
