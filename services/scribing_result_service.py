from __future__ import annotations

import sqlite3
from pathlib import Path


class ScribingResultService:
    """Read verified Grimoire + Focus -> result-name mappings.

    A verified ESO client capture is preferred when present. Xbox-only users can
    fall back to a separately stored, probe-verified public reference source.
    Structured simulator API data is preferred over page-scraped public rows.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self._results: dict[tuple[str, str], str] = {}
        self.source_key = ""
        self.source_kind = ""
        self.api_version = 0
        self.game_version = ""
        self.available = False
        self._load()

    def _load_client_source(
        self,
        connection: sqlite3.Connection,
        tables: set[str],
    ) -> list[tuple[str, str, str]]:
        if not {"scribing_result_skill", "scribing_result_skill_source"}.issubset(tables):
            return []

        source = connection.execute(
            """
            SELECT source_key, api_version, game_version
            FROM scribing_result_skill_source
            WHERE probe_verified = 1
            ORDER BY imported_at DESC
            LIMIT 1
            """
        ).fetchone()
        if source is None:
            return []

        self.source_key = str(source[0] or "")
        self.source_kind = "eso_client_api"
        self.api_version = int(source[1] or 0)
        self.game_version = str(source[2] or "")
        return connection.execute(
            """
            SELECT grimoire_name, focus_name, result_name
            FROM scribing_result_skill
            WHERE source_key = ? AND TRIM(result_name) <> ''
            """,
            (self.source_key,),
        ).fetchall()

    def _load_public_reference(
        self,
        connection: sqlite3.Connection,
        tables: set[str],
    ) -> list[tuple[str, str, str]]:
        if not {
            "scribing_result_name_reference",
            "scribing_result_name_reference_source",
        }.issubset(tables):
            return []

        source = connection.execute(
            """
            SELECT source_key, source_kind
            FROM scribing_result_name_reference_source
            WHERE probe_verified = 1
            ORDER BY
                CASE source_kind
                    WHEN 'public_simulator_api' THEN 0
                    ELSE 1
                END,
                imported_at DESC
            LIMIT 1
            """
        ).fetchone()
        if source is None:
            return []

        self.source_key = str(source[0] or "")
        self.source_kind = str(source[1] or "public_web_reference")
        self.api_version = 0
        self.game_version = ""
        return connection.execute(
            """
            SELECT grimoire_name, focus_name, result_name
            FROM scribing_result_name_reference
            WHERE source_key = ? AND TRIM(result_name) <> ''
            """,
            (self.source_key,),
        ).fetchall()

    def _load(self) -> None:
        if not self.database_path.is_file():
            return

        rows: list[tuple[str, str, str]] = []
        try:
            with sqlite3.connect(self.database_path) as connection:
                tables = {
                    str(row[0])
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                rows = self._load_client_source(connection, tables)
                if not rows:
                    rows = self._load_public_reference(connection, tables)
        except sqlite3.Error:
            return

        self._results = {
            (str(grimoire).strip(), str(focus).strip()): str(result).strip()
            for grimoire, focus, result in rows
            if str(grimoire or "").strip()
            and str(focus or "").strip()
            and str(result or "").strip()
        }
        self.available = bool(self._results)

    def result_name(self, grimoire: str, focus: str) -> str:
        return self._results.get((str(grimoire).strip(), str(focus).strip()), "")

    @property
    def count(self) -> int:
        return len(self._results)
