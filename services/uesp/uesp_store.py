# services/uesp/uesp_store.py
"""
JSON storage for the local UESP knowledge base.

Layout (relative to ``root``):
    trials/<id>.json
    dungeons/<id>.json
    arenas/<id>.json
    bosses/<id>.json
    index.json

Every record is looked up and written by its stable id (a slug of
the UESP page title - see uesp_parser.slugify), so re-importing the
same page always updates the same file instead of creating a
duplicate. Change detection compares the UESP revision id already on
disk against the one just fetched, so the importer can skip
re-parsing pages that haven't changed on the wiki since last time.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any


_CONTENT_FOLDERS = {
    "trial": "trials",
    "dungeon": "dungeons",
    "arena": "arenas",
}


class UespStore:

    def __init__(self, root: Path) -> None:
        self.root = root
        self.index_path = root / "index.json"

        for folder in (*_CONTENT_FOLDERS.values(), "bosses"):
            (root / folder).mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # Change detection
    # --------------------------------------------------

    def existing_revision(self, category: str, record_id: str) -> int | None:
        """Return the stored UESP revision id for a record, or None
        if it isn't in the store yet."""

        path = self._record_path(category, record_id)

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        source = data.get("source") or {}
        return source.get("revision_id")

    def is_up_to_date(self, category: str, record_id: str, revision_id: int) -> bool:
        stored = self.existing_revision(category, record_id)
        return stored is not None and stored == revision_id

    @staticmethod
    def folder_for(content_type: str) -> str:
        return _CONTENT_FOLDERS[content_type]

    # --------------------------------------------------
    # Writes
    # --------------------------------------------------

    def save_boss(self, boss: Any) -> Path:
        return self._save("bosses", boss.id, asdict(boss))

    def save_content(self, content: Any) -> Path:
        folder = _CONTENT_FOLDERS[content.content_type]
        return self._save(folder, content.id, asdict(content))

    def _save(self, category: str, record_id: str, data: dict[str, Any]) -> Path:
        path = self._record_path(category, record_id)

        path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )

        self._update_index(category, record_id, data)
        return path

    def _record_path(self, category: str, record_id: str) -> Path:
        return self.root / category / f"{record_id}.json"

    # --------------------------------------------------
    # Index
    # --------------------------------------------------

    def _load_index(self) -> dict[str, Any]:

        default = {
            "schema_version": 1,
            "trials": {},
            "dungeons": {},
            "arenas": {},
            "bosses": {},
        }

        if not self.index_path.exists():
            return default

        text = self.index_path.read_text(encoding="utf-8").strip()

        if not text:
            return default

        loaded = json.loads(text)
        for key, value in default.items():
            loaded.setdefault(key, value)
        return loaded

    def _update_index(self, category: str, record_id: str, data: dict[str, Any]) -> None:

        index = self._load_index()
        index.setdefault(category, {})

        source = data.get("source") or {}

        index[category][record_id] = {
            "name": data.get("name", ""),
            "source_url": source.get("url", ""),
            "retrieved_at": source.get("retrieved_at", ""),
            "revision_id": source.get("revision_id"),
        }

        self.index_path.write_text(
            json.dumps(index, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
