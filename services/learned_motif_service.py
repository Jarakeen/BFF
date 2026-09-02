from __future__ import annotations

import sqlite3
from pathlib import Path


class LearnedMotifService:
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

    def _table_exists(self, name: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None

    def _ensure_ready(self) -> None:
        try:
            if not self._table_exists("learnable_motif") or not self._table_exists("learnable_motif_progress"):
                self.bootstrap_message = "Motif reference data has not been imported."
                return
            count = int(self.connection.execute("SELECT COUNT(*) FROM learnable_motif").fetchone()[0])
            self.available = count > 0
            self.bootstrap_message = (
                f"Motif catalog ready ({count:,} learnables)."
                if self.available else "Motif reference data has not been imported."
            )
        except sqlite3.Error as exc:
            self.bootstrap_message = f"Motif database unavailable: {exc}"

    @staticmethod
    def _normalize_profile_name(name) -> str:
        return " ".join(str(name or "").strip().split())

    @property
    def active_profile(self) -> str:
        return self._active_profile

    def set_active_profile(self, name: str) -> str:
        normalized = self._normalize_profile_name(name)
        if not normalized:
            raise ValueError("Profile name cannot be empty.")
        self._active_profile = normalized
        return normalized

    def progress_summary(self) -> tuple[int, int]:
        if not self.available:
            return 0, 0
        row = self.connection.execute(
            """
            SELECT
                SUM(CASE WHEN COALESCE(p.learned, 0) = 1 THEN 1 ELSE 0 END) AS learned_count,
                COUNT(*) AS total_count
            FROM learnable_motif m
            LEFT JOIN learnable_motif_progress p
              ON p.item_id = m.item_id AND p.profile_name = ?
            """,
            (self._active_profile,),
        ).fetchone()
        return int(row["learned_count"] or 0), int(row["total_count"] or 0)

    def items(self, query: str = "") -> list[dict]:
        if not self.available:
            return []
        query = str(query or "").strip()
        params: list[object] = [self._active_profile]
        where = ""
        if query:
            pattern = f"%{query}%"
            where = "WHERE m.display_name LIKE ? OR m.style_name LIKE ? OR m.part_name LIKE ?"
            params.extend([pattern, pattern, pattern])
        rows = self.connection.execute(
            f"""
            SELECT
                m.item_id AS id,
                m.motif_number,
                m.style_name,
                m.part_name,
                m.is_full_style,
                m.display_name AS name,
                m.quality,
                m.icon,
                m.description,
                m.source_variant_count,
                COALESCE(p.learned, 0) AS owned,
                COALESCE(p.learned_on, '') AS acquired_on,
                COALESCE(p.notes, '') AS notes
            FROM learnable_motif m
            LEFT JOIN learnable_motif_progress p
              ON p.item_id = m.item_id AND p.profile_name = ?
            {where}
            ORDER BY m.motif_number, m.is_full_style DESC, m.part_name COLLATE NOCASE
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def item(self, item_id: int) -> dict | None:
        if not self.available:
            return None
        row = self.connection.execute(
            """
            SELECT
                m.item_id AS id,
                m.motif_number,
                m.style_name,
                m.part_name,
                m.is_full_style,
                m.display_name AS name,
                m.quality,
                m.icon,
                m.description,
                m.source_variant_count,
                COALESCE(p.learned, 0) AS owned,
                COALESCE(p.learned_on, '') AS acquired_on,
                COALESCE(p.notes, '') AS notes
            FROM learnable_motif m
            LEFT JOIN learnable_motif_progress p
              ON p.item_id = m.item_id AND p.profile_name = ?
            WHERE m.item_id = ?
            LIMIT 1
            """,
            (self._active_profile, int(item_id)),
        ).fetchone()
        return dict(row) if row else None

    def set_progress(self, item_id: int, *, learned: bool, learned_on: str = "", notes: str = "") -> None:
        if not self.available:
            raise RuntimeError("Motif database is not available.")
        self.connection.execute(
            """
            INSERT INTO learnable_motif_progress(profile_name, item_id, learned, learned_on, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(profile_name, item_id) DO UPDATE SET
                learned = excluded.learned,
                learned_on = excluded.learned_on,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                self._active_profile,
                int(item_id),
                1 if learned else 0,
                learned_on.strip() or None,
                notes.strip(),
            ),
        )
        self.connection.commit()

    def set_learned_batch(self, learned_by_id: dict[int, bool]) -> int:
        if not learned_by_id:
            return 0
        db = self.connection
        db.execute("BEGIN")
        try:
            for item_id, learned in learned_by_id.items():
                db.execute(
                    """
                    INSERT INTO learnable_motif_progress(profile_name, item_id, learned, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(profile_name, item_id) DO UPDATE SET
                        learned = excluded.learned,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (self._active_profile, int(item_id), 1 if learned else 0),
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
