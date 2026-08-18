# services/eso_db/eso_db_importer.py
"""
Loads the normalized JSON records under data/uesp/ into eso.db.

This is intentionally the *only* file that writes to the database,
and it has no import dependency on services/uesp/ - it reads plain
JSON dicts off disk (or in-memory dicts, for programmatic callers)
and writes rows. The UESP fetch/parse layer could be replaced
entirely and this module wouldn't need to change, as long as the
JSON shape stays the same.

Writes are idempotent: each parent record (content or boss) is
looked up by its stable id, its existing child rows are deleted, and
the current data is re-inserted, all inside one transaction per
record. Re-running an import never accumulates duplicate rows.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from services.eso_db.schema import connect


class EsoDbImportError(Exception):
    """Raised when a JSON record can't be loaded into the database."""


class EsoDbImporter:

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.connection = connect(db_path)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "EsoDbImporter":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # --------------------------------------------------
    # Directory-level import
    # --------------------------------------------------

    def import_directory(self, uesp_data_root: Path) -> dict[str, int]:
        """Import every record under data/uesp/{trials,dungeons,
        arenas,bosses}/*.json. Content is imported before bosses so
        the bosses.content_id foreign key always resolves."""

        counts = {"content": 0, "bosses": 0, "errors": 0}

        for folder in ("trials", "dungeons", "arenas"):
            for path in sorted((uesp_data_root / folder).glob("*.json")):
                try:
                    self.import_content_file(path)
                    counts["content"] += 1
                except (OSError, json.JSONDecodeError, EsoDbImportError):
                    counts["errors"] += 1

        for path in sorted((uesp_data_root / "bosses").glob("*.json")):
            try:
                self.import_boss_file(path)
                counts["bosses"] += 1
            except (OSError, json.JSONDecodeError, EsoDbImportError):
                counts["errors"] += 1

        return counts

    # --------------------------------------------------
    # File-level import
    # --------------------------------------------------

    def import_content_file(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self.import_content(data)

    def import_boss_file(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self.import_boss(data)

    # --------------------------------------------------
    # Record-level import
    # --------------------------------------------------

    def import_content(self, data: dict[str, Any]) -> None:

        record_id = data.get("id")
        if not record_id:
            raise EsoDbImportError("Content record is missing 'id'.")

        source = data.get("source") or {}

        with self.connection:
            self.connection.execute(
                            """
                INSERT INTO content (
                    id, name, content_type, summary, location, group_size,
                    source_url, source_title, revision_id, retrieved_at, license
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    content_type=excluded.content_type,
                    summary=excluded.summary,
                    location=excluded.location,
                    group_size=excluded.group_size,
                    source_url=excluded.source_url,
                    source_title=excluded.source_title,
                    revision_id=excluded.revision_id,
                    retrieved_at=excluded.retrieved_at,
                    license=excluded.license
                """,
                (
                    record_id,
                    data.get("name", ""),
                    data.get("content_type", ""),
                    data.get("summary", ""),
                    data.get("location", ""),
                    data.get("group_size"),
                    source.get("url", ""),
                    source.get("page_title", ""),
                    source.get("revision_id"),
                    source.get("retrieved_at", ""),
                    source.get("license", ""),
                ),
            )

            self._replace_child_rows(
                "content_bosses",
                "content_id",
                record_id,
                (
                    (record_id, boss_id, position)
                    for position, boss_id in enumerate(data.get("boss_ids", []))
                ),
                columns=("content_id", "boss_id", "position"),
            )

            self._replace_child_rows(
                "content_sets",
                "content_id",
                record_id,
                (
                    (record_id, set_id, position)
                    for position, set_id in enumerate(data.get("set_ids", []))
                ),
                columns=("content_id", "set_id", "position"),
            )

            self._replace_child_rows(
                "content_related_npcs",
                "content_id",
                record_id,
                (
                    (record_id, position, npc)
                    for position, npc in enumerate(data.get("related_npcs", []))
                ),
                columns=("content_id", "position", "npc_name"),
            )

            self._replace_child_rows(
                "content_achievements",
                "content_id",
                record_id,
                (
                    (
                        record_id,
                        achievement.get("id", ""),
                        position,
                        achievement.get("name", ""),
                        achievement.get("description", ""),
                        achievement.get("points"),
                    )
                    for position, achievement in enumerate(data.get("achievements", []))
                ),
                columns=(
                    "content_id",
                    "achievement_id",
                    "position",
                    "name",
                    "description",
                    "points",
                ),
            )

    def import_boss(self, data: dict[str, Any]) -> None:

        record_id = data.get("id")
        if not record_id:
            raise EsoDbImportError("Boss record is missing 'id'.")

        source = data.get("source") or {}
        health = data.get("health") or {}
        difficulty_notes = data.get("difficulty_notes") or {}

        with self.connection:
            self.connection.execute(
                """
                INSERT INTO bosses (
                    id, name, content_id, content_name, location, species, reaction,
                    health_normal, health_veteran, health_hardmode, summary,
                    source_url, source_title, revision_id, retrieved_at, license
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    content_id=excluded.content_id,
                    content_name=excluded.content_name,
                    location=excluded.location,
                    species=excluded.species,
                    reaction=excluded.reaction,
                    health_normal=excluded.health_normal,
                    health_veteran=excluded.health_veteran,
                    health_hardmode=excluded.health_hardmode,
                    summary=excluded.summary,
                    source_url=excluded.source_url,
                    source_title=excluded.source_title,
                    revision_id=excluded.revision_id,
                    retrieved_at=excluded.retrieved_at,
                    license=excluded.license
                """,
                (
                    record_id,
                    data.get("name", ""),
                    data.get("content_id") or None,
                    data.get("content_name", ""),
                    data.get("location", ""),
                    data.get("species", ""),
                    data.get("reaction", ""),
                    health.get("normal", ""),
                    health.get("veteran", ""),
                    health.get("hardmode", ""),
                    data.get("summary", ""),
                    source.get("url", ""),
                    source.get("page_title", ""),
                    source.get("revision_id"),
                    source.get("retrieved_at", ""),
                    source.get("license", ""),
                ),
            )

            self._replace_child_rows(
                "boss_abilities",
                "boss_id",
                record_id,
                (
                    (record_id, position, ability.get("name", ""), ability.get("description", ""))
                    for position, ability in enumerate(data.get("abilities", []))
                ),
                columns=("boss_id", "position", "name", "description"),
            )

            self._replace_child_rows(
                "boss_phases",
                "boss_id",
                record_id,
                (
                    (
                        record_id,
                        position,
                        phase.get("label", ""),
                        phase.get("threshold", ""),
                        phase.get("description", ""),
                    )
                    for position, phase in enumerate(data.get("phases", []))
                ),
                columns=("boss_id", "position", "label", "threshold", "description"),
            )

            self._replace_child_rows(
                "boss_dialogue",
                "boss_id",
                record_id,
                (
                    (
                        record_id,
                        position,
                        line.get("speaker", ""),
                        line.get("line", ""),
                        line.get("trigger", ""),
                    )
                    for position, line in enumerate(data.get("dialogue", []))
                ),
                columns=("boss_id", "position", "speaker", "line", "trigger_context"),
            )

            self._replace_child_rows(
                "boss_notes",
                "boss_id",
                record_id,
                (
                    (record_id, position, note)
                    for position, note in enumerate(data.get("notes", []))
                ),
                columns=("boss_id", "position", "note"),
            )

            self._replace_child_rows(
                "boss_related_npcs",
                "boss_id",
                record_id,
                (
                    (record_id, position, npc)
                    for position, npc in enumerate(data.get("related_npcs", []))
                ),
                columns=("boss_id", "position", "npc_name"),
            )

            self._replace_child_rows(
                "boss_related_quests",
                "boss_id",
                record_id,
                (
                    (record_id, position, quest)
                    for position, quest in enumerate(data.get("related_quests", []))
                ),
                columns=("boss_id", "position", "quest"),
            )

            self._replace_child_rows(
                "boss_achievements",
                "boss_id",
                record_id,
                (
                    (
                        record_id,
                        achievement.get("id", ""),
                        position,
                        achievement.get("name", ""),
                        achievement.get("description", ""),
                        achievement.get("points"),
                    )
                    for position, achievement in enumerate(data.get("achievements", []))
                ),
                columns=(
                    "boss_id",
                    "achievement_id",
                    "position",
                    "name",
                    "description",
                    "points",
                ),
            )

            difficulty_rows = [
                (record_id, "normal_veteran", position, note)
                for position, note in enumerate(
                    difficulty_notes.get("normal_veteran_differences", [])
                )
            ] + [
                (record_id, "hardmode", position, note)
                for position, note in enumerate(difficulty_notes.get("hardmode_info", []))
            ]

            self.connection.execute(
                "DELETE FROM boss_difficulty_notes WHERE boss_id = ?",
                (record_id,),
            )
            if difficulty_rows:
                self.connection.executemany(
                    "INSERT INTO boss_difficulty_notes "
                    "(boss_id, category, position, note) VALUES (?, ?, ?, ?)",
                    difficulty_rows,
                )

    # --------------------------------------------------
    # Internals
    # --------------------------------------------------

    def _replace_child_rows(
        self,
        table: str,
        parent_column: str,
        parent_id: str,
        rows: Iterable[tuple],
        columns: tuple[str, ...],
    ) -> None:
        """Delete all existing child rows for a parent id, then
        insert the current set. Keeps re-imports idempotent without
        needing per-row diffing."""

        self.connection.execute(
            f"DELETE FROM {table} WHERE {parent_column} = ?",
            (parent_id,),
        )

        rows = list(rows)
        if not rows:
            return

        placeholders = ", ".join("?" for _ in columns)
        column_list = ", ".join(columns)

        self.connection.executemany(
            f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})",
            rows,
        )
