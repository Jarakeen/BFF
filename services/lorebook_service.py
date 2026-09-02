from __future__ import annotations

import sqlite3
from pathlib import Path


class LorebookService:
    DEFAULT_PROFILE = "Default"

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self._connection: sqlite3.Connection | None = None
        self._active_profile = self.DEFAULT_PROFILE
        self.available = False
        self.bootstrap_message = ""
        self._ensure_ready()

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(self.database_path)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    @staticmethod
    def _normalize_profile_name(name) -> str:
        return " ".join(str(name or "").strip().split())

    def _table_exists(self, name: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None

    def _ensure_ready(self) -> None:
        try:
            if not self._table_exists("lorebook") or not self._table_exists("lorebook_progress"):
                self.bootstrap_message = "Lorebook reference data has not been imported."
                return
            count = int(self.connection.execute("SELECT COUNT(*) FROM lorebook").fetchone()[0])
            self.available = count > 0
            self.bootstrap_message = (
                f"Lorebook catalog ready ({count:,} books)."
                if self.available else "Lorebook reference data has not been imported."
            )
        except sqlite3.Error as exc:
            self.bootstrap_message = f"Lorebook database unavailable: {exc}"

    @property
    def active_profile(self) -> str:
        return self._active_profile

    def ensure_profile(self, name: str) -> str:
        normalized = self._normalize_profile_name(name)
        if not normalized:
            raise ValueError("Profile name cannot be empty.")
        return normalized

    def set_active_profile(self, name: str) -> str:
        self._active_profile = self.ensure_profile(name)
        return self._active_profile

    def progress_summary(self) -> tuple[int, int]:
        if not self.available:
            return 0, 0
        row = self.connection.execute(
            """
            SELECT SUM(CASE WHEN COALESCE(p.learned, 0)=1 THEN 1 ELSE 0 END) AS learned_count,
                   COUNT(*) AS total_count
            FROM lorebook b
            LEFT JOIN lorebook_progress p
              ON p.lorebook_id=b.lorebook_id AND p.profile_name=?
            """, (self._active_profile,)
        ).fetchone()
        return int(row["learned_count"] or 0), int(row["total_count"] or 0)

    def items(self, query: str = "") -> list[dict]:
        if not self.available:
            return []
        query = str(query or "").strip()
        params: list[object] = [self._active_profile]
        where = ""
        if query:
            where = "WHERE b.title LIKE ? OR b.body LIKE ? OR b.skill LIKE ?"
            pattern = f"%{query}%"
            params.extend([pattern, pattern, pattern])
        rows = self.connection.execute(
            f"""
            SELECT b.lorebook_id AS id, b.title AS name, b.skill,
                   b.source_occurrence_count,
                   COALESCE(p.learned,0) AS owned,
                   COALESCE(p.learned_on,'') AS acquired_on,
                   COALESCE(p.notes,'') AS notes
            FROM lorebook b
            LEFT JOIN lorebook_progress p
              ON p.lorebook_id=b.lorebook_id AND p.profile_name=?
            {where}
            ORDER BY b.title COLLATE NOCASE, b.lorebook_id
            """, params
        ).fetchall()
        return [dict(row) for row in rows]

    def item(self, lorebook_id: int) -> dict | None:
        if not self.available:
            return None
        row = self.connection.execute(
            """
            SELECT b.lorebook_id AS id, b.title AS name, b.body, b.icon, b.skill,
                   b.primary_book_id, b.primary_log_id,
                   b.category_index, b.collection_index, b.book_index,
                   b.source_occurrence_count,
                   COALESCE(p.learned,0) AS owned,
                   COALESCE(p.learned_on,'') AS acquired_on,
                   COALESCE(p.notes,'') AS notes
            FROM lorebook b
            LEFT JOIN lorebook_progress p
              ON p.lorebook_id=b.lorebook_id AND p.profile_name=?
            WHERE b.lorebook_id=? LIMIT 1
            """, (self._active_profile, int(lorebook_id))
        ).fetchone()
        return dict(row) if row else None

    def set_progress(self, lorebook_id: int, *, learned: bool, learned_on: str = "", notes: str = "") -> None:
        if not self.available:
            raise RuntimeError("Lorebook database is not available.")
        self.connection.execute(
            """
            INSERT INTO lorebook_progress(profile_name,lorebook_id,learned,learned_on,notes,updated_at)
            VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(profile_name,lorebook_id) DO UPDATE SET
              learned=excluded.learned, learned_on=excluded.learned_on,
              notes=excluded.notes, updated_at=CURRENT_TIMESTAMP
            """,
            (self._active_profile, int(lorebook_id), 1 if learned else 0,
             learned_on.strip() or None, notes.strip())
        )
        self.connection.commit()

    def set_learned_batch(self, learned_by_id: dict[int, bool]) -> int:
        if not learned_by_id:
            return 0
        db = self.connection
        db.execute("BEGIN")
        try:
            for lorebook_id, learned in learned_by_id.items():
                db.execute(
                    """
                    INSERT INTO lorebook_progress(profile_name,lorebook_id,learned,updated_at)
                    VALUES(?,?,?,CURRENT_TIMESTAMP)
                    ON CONFLICT(profile_name,lorebook_id) DO UPDATE SET
                      learned=excluded.learned, updated_at=CURRENT_TIMESTAMP
                    """,
                    (self._active_profile, int(lorebook_id), 1 if learned else 0),
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
        return len(learned_by_id)

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
