from __future__ import annotations

import sqlite3
from pathlib import Path

from services.collection_progress_pydantic_schema import validate_collection_batch, validate_collection_progress


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
        payload = validate_collection_progress({
            "profile": self._active_profile,
            "item_id": int(item_id),
            "owned": bool(learned),
            "acquired_on": str(learned_on or "").strip(),
            "notes": str(notes or "").strip(),
        })
        db = self.connection
        if db.execute("SELECT 1 FROM learnable_motif WHERE item_id = ?", (payload["item_id"],)).fetchone() is None:
            raise KeyError(f"Unknown learnable motif item id: {item_id}")
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
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
                payload["profile"],
                payload["item_id"],
                1 if payload["owned"] else 0,
                payload["acquired_on"] or None,
                payload["notes"],
            ),
            )
            row = db.execute(
                "SELECT learned, COALESCE(learned_on, '') AS learned_on, notes FROM learnable_motif_progress WHERE profile_name = ? AND item_id = ?",
                (payload["profile"], payload["item_id"]),
            ).fetchone()
            if row is None or bool(row["learned"]) != payload["owned"] or str(row["learned_on"] or "") != payload["acquired_on"] or str(row["notes"] or "") != payload["notes"]:
                raise RuntimeError("Motif progress did not round-trip exactly")
            db.commit()
        except Exception:
            db.rollback()
            raise

    def set_learned_batch(self, learned_by_id: dict[int, bool]) -> int:
        if not learned_by_id:
            return 0
        payload = validate_collection_batch({
            "profile": self._active_profile,
            "owned_by_id": {int(k): bool(v) for k, v in learned_by_id.items()},
        })
        db = self.connection
        ids = tuple(payload["owned_by_id"])
        placeholders = ",".join("?" for _ in ids)
        known = {int(row[0]) for row in db.execute(f"SELECT item_id FROM learnable_motif WHERE item_id IN ({placeholders})", ids).fetchall()}
        missing = sorted(set(ids) - known)
        if missing:
            raise KeyError(f"Unknown learnable motif item ids: {missing}")
        db.execute("BEGIN IMMEDIATE")
        try:
            for item_id, learned in payload["owned_by_id"].items():
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
            rows = db.execute(
                f"SELECT item_id, learned FROM learnable_motif_progress WHERE profile_name = ? AND item_id IN ({placeholders})",
                (payload["profile"], *ids),
            ).fetchall()
            read_back = {int(row["item_id"]): bool(row["learned"]) for row in rows}
            if read_back != payload["owned_by_id"]:
                raise RuntimeError("Motif batch did not round-trip exactly")
            db.commit()
        except Exception:
            db.rollback()
            raise
        return len(payload["owned_by_id"])

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
