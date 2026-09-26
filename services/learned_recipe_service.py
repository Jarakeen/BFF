from __future__ import annotations

import sqlite3
from pathlib import Path

from services.collection_progress_pydantic_schema import validate_collection_batch, validate_collection_progress


KIND_BY_CATEGORY = {
    "Recipes": "provisioning_recipe",
    "Furnishing Plans": "furnishing_plan",
}


class LearnedRecipeService:
    """Profile-aware access to provisioning recipes and furnishing plans."""

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
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone() is not None

    def _ensure_ready(self) -> None:
        try:
            if not self._table_exists("learnable_recipe") or not self._table_exists("learnable_recipe_progress"):
                self.bootstrap_message = "Recipe and furnishing-plan reference data has not been imported."
                return
            count = int(self.connection.execute("SELECT COUNT(*) FROM learnable_recipe").fetchone()[0])
            self.available = count > 0
            self.bootstrap_message = (
                f"Learned recipe catalog ready ({count:,} records)."
                if self.available
                else "Recipe and furnishing-plan reference data has not been imported."
            )
        except sqlite3.Error as exc:
            self.bootstrap_message = f"Learned recipe database unavailable: {exc}"

    @property
    def active_profile(self) -> str:
        return self._active_profile

    def profiles(self) -> list[str]:
        if not self.available:
            return [self.DEFAULT_PROFILE]
        rows = self.connection.execute(
            "SELECT DISTINCT profile_name FROM learnable_recipe_progress ORDER BY profile_name COLLATE NOCASE"
        ).fetchall()
        names = [str(row[0]) for row in rows if str(row[0] or "").strip()]
        if self.DEFAULT_PROFILE not in names:
            names.insert(0, self.DEFAULT_PROFILE)
        return names

    def ensure_profile(self, name: str) -> str:
        normalized = self._normalize_profile_name(name)
        if not normalized:
            raise ValueError("Profile name cannot be empty.")
        return normalized

    def set_active_profile(self, name: str) -> str:
        self._active_profile = self.ensure_profile(name)
        return self._active_profile

    def _kind(self, category: str) -> str:
        try:
            return KIND_BY_CATEGORY[category]
        except KeyError as exc:
            raise KeyError(f"Unknown learned collection category: {category}") from exc

    def progress_summary(self, category: str) -> tuple[int, int]:
        if not self.available:
            return 0, 0
        kind = self._kind(category)
        row = self.connection.execute(
            """
            SELECT
                SUM(CASE WHEN COALESCE(p.learned, 0) = 1 THEN 1 ELSE 0 END) AS learned_count,
                COUNT(*) AS total_count
            FROM learnable_recipe r
            LEFT JOIN learnable_recipe_progress p
              ON p.item_id = r.item_id AND p.profile_name = ?
            WHERE r.learnable_kind = ?
            """,
            (self._active_profile, kind),
        ).fetchone()
        return int(row["learned_count"] or 0), int(row["total_count"] or 0)

    def items(self, category: str, query: str = "") -> list[dict]:
        if not self.available:
            return []
        kind = self._kind(category)
        query = str(query or "").strip()
        params: list[object] = [self._active_profile, kind]
        where = "r.learnable_kind = ?"
        if query:
            pattern = f"%{query}%"
            where += " AND (r.name LIKE ? OR r.ability_description LIKE ? OR f.furnishing_name LIKE ?)"
            params.extend([pattern, pattern, pattern])
        rows = self.connection.execute(
            f"""
            SELECT
                r.item_id AS id,
                r.name,
                r.plan_type,
                r.quality,
                r.icon,
                r.craft_type,
                r.recipe_rank,
                r.recipe_quality,
                r.result_item_id,
                r.ability_description AS description,
                COALESCE(f.furnishing_name, '') AS result_name,
                COALESCE(p.learned, 0) AS owned,
                COALESCE(p.learned_on, '') AS acquired_on,
                COALESCE(p.notes, '') AS notes
            FROM learnable_recipe r
            LEFT JOIN furnishing_plan_result f ON f.plan_item_id = r.item_id
            LEFT JOIN learnable_recipe_progress p
              ON p.item_id = r.item_id AND p.profile_name = ?
            WHERE {where}
            GROUP BY r.item_id
            ORDER BY r.name COLLATE NOCASE, r.item_id
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
                r.item_id AS id,
                r.name,
                r.learnable_kind,
                r.plan_type,
                r.quality,
                r.icon,
                r.craft_type,
                r.special_type,
                r.recipe_rank,
                r.recipe_quality,
                r.recipe_list_index,
                r.recipe_index,
                r.result_item_id,
                r.result_item_link,
                r.ability_description AS description,
                COALESCE(f.furnishing_name, '') AS result_name,
                COALESCE(p.learned, 0) AS owned,
                COALESCE(p.learned_on, '') AS acquired_on,
                COALESCE(p.notes, '') AS notes
            FROM learnable_recipe r
            LEFT JOIN furnishing_plan_result f ON f.plan_item_id = r.item_id
            LEFT JOIN learnable_recipe_progress p
              ON p.item_id = r.item_id AND p.profile_name = ?
            WHERE r.item_id = ?
            LIMIT 1
            """,
            (self._active_profile, int(item_id)),
        ).fetchone()
        return dict(row) if row else None

    def set_progress(
        self,
        item_id: int,
        *,
        learned: bool,
        learned_on: str = "",
        notes: str = "",
        profile: str | None = None,
    ) -> None:
        if not self.available:
            raise RuntimeError("Learned recipe database is not available.")
        profile_name = self.ensure_profile(profile or self._active_profile)
        payload = validate_collection_progress({
            "profile": profile_name,
            "item_id": int(item_id),
            "owned": bool(learned),
            "acquired_on": str(learned_on or "").strip(),
            "notes": str(notes or "").strip(),
        })
        exists = self.connection.execute(
            "SELECT 1 FROM learnable_recipe WHERE item_id = ?",
            (int(item_id),),
        ).fetchone()
        if exists is None:
            raise KeyError(f"Unknown learnable recipe item id: {item_id}")
        db = self.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
            """
            INSERT INTO learnable_recipe_progress(
                profile_name, item_id, learned, learned_on, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
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
                "SELECT learned, COALESCE(learned_on, '') AS learned_on, notes FROM learnable_recipe_progress WHERE profile_name = ? AND item_id = ?",
                (payload["profile"], payload["item_id"]),
            ).fetchone()
            if row is None or bool(row["learned"]) != payload["owned"] or str(row["learned_on"] or "") != payload["acquired_on"] or str(row["notes"] or "") != payload["notes"]:
                raise RuntimeError("Recipe progress did not round-trip exactly")
            db.commit()
        except Exception:
            db.rollback()
            raise

    def set_learned_batch(self, profile: str, learned_by_id: dict[int, bool]) -> int:
        profile_name = self.ensure_profile(profile)
        if not learned_by_id:
            return 0
        payload = validate_collection_batch({
            "profile": profile_name,
            "owned_by_id": {int(k): bool(v) for k, v in learned_by_id.items()},
        })
        db = self.connection
        ids = tuple(payload["owned_by_id"])
        placeholders = ",".join("?" for _ in ids)
        known = {int(row[0]) for row in db.execute(f"SELECT item_id FROM learnable_recipe WHERE item_id IN ({placeholders})", ids).fetchall()}
        missing = sorted(set(ids) - known)
        if missing:
            raise KeyError(f"Unknown learnable recipe item ids: {missing}")
        db.execute("BEGIN IMMEDIATE")
        try:
            for item_id, learned in payload["owned_by_id"].items():
                db.execute(
                    """
                    INSERT INTO learnable_recipe_progress(profile_name, item_id, learned, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(profile_name, item_id) DO UPDATE SET
                        learned = excluded.learned,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (payload["profile"], int(item_id), 1 if learned else 0),
                )
            rows = db.execute(
                f"SELECT item_id, learned FROM learnable_recipe_progress WHERE profile_name = ? AND item_id IN ({placeholders})",
                (payload["profile"], *ids),
            ).fetchall()
            read_back = {int(row["item_id"]): bool(row["learned"]) for row in rows}
            if read_back != payload["owned_by_id"]:
                raise RuntimeError("Recipe batch did not round-trip exactly")
            db.commit()
        except Exception:
            db.rollback()
            raise
        return len(payload["owned_by_id"])

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
