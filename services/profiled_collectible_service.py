from __future__ import annotations

"""Profile-aware ownership over the canonical ESO collectible catalog."""

import csv
from pathlib import Path

from services.eso_collectible_database_service import EsoCollectibleDatabaseService


class ProfiledCollectibleService(EsoCollectibleDatabaseService):
    """Add named-person ownership to the existing collectible catalog.

    The catalog remains shared. Only ownership/progress is profile-specific.
    Existing single-profile progress is migrated conservatively to ``Default``.
    """

    DEFAULT_PROFILE = "Default"

    def __init__(self, database_path: Path) -> None:
        super().__init__(database_path)
        self._active_profile = self.DEFAULT_PROFILE
        if self.available:
            self._ensure_profile_schema()

    @staticmethod
    def _normalize_profile_name(name) -> str:
        return " ".join(str(name or "").strip().split())

    def _ensure_profile_schema(self) -> None:
        columns = {
            str(row["name"])
            for row in self.connection.execute("PRAGMA table_info(collectible_progress)").fetchall()
        }
        if "profile_name" not in columns:
            db = self.connection
            db.execute("BEGIN")
            try:
                db.execute(
                    """
                    CREATE TABLE collectible_progress_profiled (
                        profile_name TEXT NOT NULL,
                        collectible_id INTEGER NOT NULL,
                        owned INTEGER NOT NULL DEFAULT 0 CHECK (owned IN (0, 1)),
                        acquired_on TEXT,
                        notes TEXT NOT NULL DEFAULT '',
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (profile_name, collectible_id),
                        FOREIGN KEY (collectible_id) REFERENCES collectible(id) ON DELETE CASCADE
                    )
                    """
                )
                db.execute(
                    """
                    INSERT INTO collectible_progress_profiled(
                        profile_name, collectible_id, owned, acquired_on, notes, updated_at
                    )
                    SELECT ?, collectible_id, owned, acquired_on, notes, updated_at
                    FROM collectible_progress
                    """,
                    (self.DEFAULT_PROFILE,),
                )
                db.execute("DROP TABLE collectible_progress")
                db.execute("ALTER TABLE collectible_progress_profiled RENAME TO collectible_progress")
                db.commit()
            except Exception:
                db.rollback()
                raise

        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_collectible_progress_profile_owned "
            "ON collectible_progress(profile_name, owned)"
        )
        self.connection.commit()

    @property
    def active_profile(self) -> str:
        return self._active_profile

    def profiles(self) -> list[str]:
        rows = self.connection.execute(
            "SELECT DISTINCT profile_name FROM collectible_progress ORDER BY profile_name COLLATE NOCASE"
        ).fetchall()
        names = [str(row[0]) for row in rows if str(row[0] or "").strip()]
        if self.DEFAULT_PROFILE not in names:
            names.insert(0, self.DEFAULT_PROFILE)
        return names

    def ensure_profile(self, name: str) -> str:
        normalized = self._normalize_profile_name(name)
        if not normalized:
            raise ValueError("Profile name cannot be empty.")
        # A profile does not need a dummy progress row. It becomes persistent
        # as soon as imported or edited ownership exists.
        return normalized

    def set_active_profile(self, name: str) -> str:
        self._active_profile = self.ensure_profile(name)
        return self._active_profile

    def progress_summary(self, category: str | None = None) -> tuple[int, int]:
        if not self.available:
            return 0, 0
        params: list[object] = [self._active_profile]
        where = ""
        if category:
            where = "WHERE c.sidebar_category_key = ?"
            params.append(category)
        row = self.connection.execute(
            f"""
            SELECT
                SUM(CASE WHEN COALESCE(p.owned, 0) = 1 THEN 1 ELSE 0 END) AS owned_count,
                COUNT(*) AS total_count
            FROM collectible c
            LEFT JOIN collectible_progress p
              ON p.collectible_id = c.id AND p.profile_name = ?
            {where}
            """,
            params,
        ).fetchone()
        return int(row["owned_count"] or 0), int(row["total_count"] or 0)

    def collectibles(self, category: str, query: str = "") -> list[dict]:
        if not self.available:
            return []
        query = query.strip()
        params: list[object] = [self._active_profile, category]
        where = "c.sidebar_category_key = ?"
        if query:
            pattern = f"%{query}%"
            where += " AND (c.name LIKE ? OR c.description LIKE ? OR c.hint LIKE ? OR c.source_subcategory_name LIKE ?)"
            params.extend([pattern, pattern, pattern, pattern])

        rows = self.connection.execute(
            f"""
            SELECT c.id, c.name, c.description, c.hint, c.icon,
                   c.canonical_type_key, c.source_subcategory_name,
                   c.is_unlocked, c.is_usable, c.is_renameable,
                   COALESCE(p.owned, 0) AS owned,
                   COALESCE(p.acquired_on, '') AS acquired_on,
                   COALESCE(p.notes, '') AS notes
            FROM collectible c
            LEFT JOIN collectible_progress p
              ON p.collectible_id = c.id AND p.profile_name = ?
            WHERE {where}
            ORDER BY c.name COLLATE NOCASE, c.id
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def collectible(self, collectible_id: int) -> dict | None:
        if not self.available:
            return None
        row = self.connection.execute(
            """
            SELECT cs.*,
                   COALESCE(p.owned, 0) AS owned,
                   COALESCE(p.acquired_on, '') AS acquired_on,
                   COALESCE(p.notes, '') AS notes,
                   COALESCE(p.updated_at, '') AS progress_updated_at
            FROM collectible_search cs
            LEFT JOIN collectible_progress p
              ON p.collectible_id = cs.id AND p.profile_name = ?
            WHERE cs.id = ?
            """,
            (self._active_profile, int(collectible_id)),
        ).fetchone()
        return dict(row) if row else None

    def set_progress(
        self,
        collectible_id: int,
        *,
        owned: bool,
        acquired_on: str = "",
        notes: str = "",
        profile: str | None = None,
    ) -> None:
        if not self.available:
            raise RuntimeError("Collectible database is not available.")

        exists = self.connection.execute(
            "SELECT 1 FROM collectible WHERE id = ?",
            (int(collectible_id),),
        ).fetchone()
        if exists is None:
            raise KeyError(f"Unknown collectible id: {collectible_id}")

        profile_name = self.ensure_profile(profile or self._active_profile)
        acquired_on_value = acquired_on.strip() or None
        notes_value = notes.strip()
        self.connection.execute(
            """
            INSERT INTO collectible_progress (
                profile_name, collectible_id, owned, acquired_on, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(profile_name, collectible_id) DO UPDATE SET
                owned = excluded.owned,
                acquired_on = excluded.acquired_on,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                profile_name,
                int(collectible_id),
                1 if owned else 0,
                acquired_on_value,
                notes_value,
            ),
        )
        self.connection.commit()

    def set_owned_batch(self, profile: str, owned_by_id: dict[int, bool]) -> int:
        profile_name = self.ensure_profile(profile)
        if not owned_by_id:
            return 0
        db = self.connection
        db.execute("BEGIN")
        try:
            for collectible_id, owned in owned_by_id.items():
                db.execute(
                    """
                    INSERT INTO collectible_progress(profile_name, collectible_id, owned, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(profile_name, collectible_id) DO UPDATE SET
                        owned = excluded.owned,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (profile_name, int(collectible_id), 1 if owned else 0),
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
        return len(owned_by_id)

    def export_progress_csv(self, target_path: Path) -> Path:
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        rows = self.connection.execute(
            """
            SELECT c.id, c.name, c.sidebar_category_key, c.canonical_type_key,
                   c.source_subcategory_name, COALESCE(p.owned, 0) AS owned,
                   COALESCE(p.acquired_on, '') AS acquired_on,
                   COALESCE(p.notes, '') AS notes
            FROM collectible c
            LEFT JOIN collectible_progress p
              ON p.collectible_id = c.id AND p.profile_name = ?
            ORDER BY c.sidebar_category_key, c.name COLLATE NOCASE, c.id
            """,
            (self._active_profile,),
        ).fetchall()
        with target_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["Profile", "Collectible ID", "Name", "Category", "Type", "Subtype", "Owned", "Acquired On", "Notes"]
            )
            for row in rows:
                writer.writerow(
                    [
                        self._active_profile,
                        row["id"], row["name"], row["sidebar_category_key"],
                        row["canonical_type_key"], row["source_subcategory_name"],
                        row["owned"], row["acquired_on"], row["notes"],
                    ]
                )
        return target_path
