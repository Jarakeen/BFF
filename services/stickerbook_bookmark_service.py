from __future__ import annotations

import sqlite3
from pathlib import Path


class StickerbookBookmarkService:
    """Profile-aware set shortlist for gear the user may want to try in raid comps."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stickerbook_set_bookmark (
                    profile_id TEXT NOT NULL,
                    set_id INTEGER NOT NULL,
                    bookmarked INTEGER NOT NULL DEFAULT 1,
                    note TEXT,
                    PRIMARY KEY (profile_id, set_id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_stickerbook_set_bookmark_profile "
                "ON stickerbook_set_bookmark(profile_id, bookmarked)"
            )
            connection.commit()

    @staticmethod
    def _profile(profile_id: str) -> str:
        return str(profile_id or "Default").strip() or "Default"

    def set_bookmarked(
        self,
        profile_id: str,
        set_id: int,
        bookmarked: bool,
        *,
        note: str | None = None,
    ) -> None:
        profile = self._profile(profile_id)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stickerbook_set_bookmark(profile_id, set_id, bookmarked, note)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(profile_id, set_id)
                DO UPDATE SET
                    bookmarked = excluded.bookmarked,
                    note = COALESCE(excluded.note, stickerbook_set_bookmark.note)
                """,
                (profile, int(set_id), int(bool(bookmarked)), note),
            )
            connection.commit()

    def is_bookmarked(self, profile_id: str, set_id: int) -> bool:
        profile = self._profile(profile_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT bookmarked
                FROM stickerbook_set_bookmark
                WHERE profile_id = ? AND set_id = ?
                """,
                (profile, int(set_id)),
            ).fetchone()
        return bool(row[0]) if row is not None else False

    def bookmarked_set_ids(self, profile_id: str) -> set[int]:
        profile = self._profile(profile_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT set_id
                FROM stickerbook_set_bookmark
                WHERE profile_id = ? AND bookmarked = 1
                ORDER BY set_id
                """,
                (profile,),
            ).fetchall()
        return {int(row[0]) for row in rows}

    def note(self, profile_id: str, set_id: int) -> str:
        profile = self._profile(profile_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT note
                FROM stickerbook_set_bookmark
                WHERE profile_id = ? AND set_id = ?
                """,
                (profile, int(set_id)),
            ).fetchone()
        return str(row[0] or "") if row is not None else ""
