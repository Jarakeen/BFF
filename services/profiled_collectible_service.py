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

        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS collectible_profile (
                profile_name TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_collectible_progress_profile_owned
                ON collectible_progress(profile_name, owned);
            """
        )
        if self._table_exists("collectible_rumor"):
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS collectible_rumor_progress (
                    profile_name TEXT NOT NULL,
                    rumor_id INTEGER NOT NULL,
                    owned INTEGER NOT NULL DEFAULT 0 CHECK (owned IN (0, 1)),
                    acquired_on TEXT,
                    notes TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (profile_name, rumor_id),
                    FOREIGN KEY (rumor_id) REFERENCES collectible_rumor(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_collectible_rumor_progress_profile_owned
                    ON collectible_rumor_progress(profile_name, owned);
                """
            )

        self.connection.execute(
            "INSERT OR IGNORE INTO collectible_profile(profile_name) VALUES (?)",
            (self.DEFAULT_PROFILE,),
        )
        self.connection.execute(
            """
            INSERT OR IGNORE INTO collectible_profile(profile_name)
            SELECT DISTINCT profile_name FROM collectible_progress
            WHERE profile_name IS NOT NULL AND TRIM(profile_name) <> ''
            """
        )
        self.connection.commit()

    def _rumor_catalog_available(self) -> bool:
        return self._table_exists("collectible_rumor")

    @staticmethod
    def _rumor_virtual_id(rumor_id: int) -> int:
        # Keep rumor rows distinct from canonical collectible ids without
        # mutating either catalog. The UI only requires a stable integer key.
        return -int(rumor_id)

    @staticmethod
    def _rumor_id_from_virtual(collectible_id: int) -> int | None:
        value = int(collectible_id)
        return -value if value < 0 else None

    def _rumor_rows(self, query: str = "") -> list[dict]:
        if not self._rumor_catalog_available():
            return []
        query = str(query or "").strip()
        params: list[object] = [self._active_profile]
        where = ""
        if query:
            pattern = f"%{query}%"
            where = """
            WHERE (
                r.name LIKE ?
                OR r.start_hint LIKE ?
                OR r.background_text LIKE ?
                OR r.complete_text LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM collectible_rumor_hint h
                    WHERE h.rumor_id = r.id
                      AND (h.name LIKE ? OR h.description LIKE ?)
                )
            )
            """
            params.extend([pattern] * 6)

        rows = self.connection.execute(
            f"""
            SELECT
                r.id AS rumor_id,
                r.name,
                r.start_hint,
                r.background_text,
                r.complete_text,
                r.declared_hint_count,
                COALESCE(p.owned, 0) AS owned,
                COALESCE(p.acquired_on, '') AS acquired_on,
                COALESCE(p.notes, '') AS notes
            FROM collectible_rumor r
            LEFT JOIN collectible_rumor_progress p
              ON p.rumor_id = r.id AND p.profile_name = ?
            {where}
            ORDER BY r.name COLLATE NOCASE, r.id
            """,
            params,
        ).fetchall()

        result: list[dict] = []
        for row in rows:
            rumor_id = int(row["rumor_id"])
            result.append(
                {
                    "id": self._rumor_virtual_id(rumor_id),
                    "rumor_id": rumor_id,
                    "name": str(row["name"] or ""),
                    "description": str(row["background_text"] or row["complete_text"] or ""),
                    "hint": str(row["start_hint"] or ""),
                    "icon": "",
                    "canonical_type_key": "rumor",
                    "canonical_type_name": "Rumor",
                    "source_subcategory_name": f"{int(row['declared_hint_count'] or 0)} hints",
                    "is_unlocked": 0,
                    "is_usable": 0,
                    "is_renameable": 0,
                    "is_slottable": 0,
                    "has_appearance": 0,
                    "owned": int(row["owned"] or 0),
                    "acquired_on": str(row["acquired_on"] or ""),
                    "notes": str(row["notes"] or ""),
                }
            )
        return result

    def _rumor_detail(self, rumor_id: int) -> dict | None:
        rows = [row for row in self._rumor_rows() if int(row.get("rumor_id", 0)) == int(rumor_id)]
        if not rows:
            return None
        detail = dict(rows[0])
        hints = self.connection.execute(
            """
            SELECT hint_index, name, description
            FROM collectible_rumor_hint
            WHERE rumor_id = ?
            ORDER BY hint_index, id
            """,
            (int(rumor_id),),
        ).fetchall()
        hint_parts = []
        for hint in hints:
            label = str(hint["name"] or "").strip()
            description = str(hint["description"] or "").strip()
            text = " — ".join(part for part in (label, description) if part)
            if text:
                hint_parts.append(f"{int(hint['hint_index']) + 1}. {text}")
        start = str(detail.get("hint") or "").strip()
        combined = [start] if start else []
        combined.extend(hint_parts)
        detail["hint"] = "\n".join(combined)
        return detail

    @property
    def active_profile(self) -> str:
        return self._active_profile

    def profiles(self) -> list[str]:
        rows = self.connection.execute(
            "SELECT profile_name FROM collectible_profile ORDER BY profile_name COLLATE NOCASE"
        ).fetchall()
        names = [str(row[0]) for row in rows if str(row[0] or "").strip()]
        if self.DEFAULT_PROFILE in names:
            names.remove(self.DEFAULT_PROFILE)
            names.insert(0, self.DEFAULT_PROFILE)
        return names or [self.DEFAULT_PROFILE]

    def ensure_profile(self, name: str) -> str:
        normalized = self._normalize_profile_name(name)
        if not normalized:
            raise ValueError("Profile name cannot be empty.")
        self.connection.execute(
            "INSERT OR IGNORE INTO collectible_profile(profile_name) VALUES (?)",
            (normalized,),
        )
        self.connection.commit()
        return normalized

    def set_active_profile(self, name: str) -> str:
        self._active_profile = self.ensure_profile(name)
        return self._active_profile

    def progress_summary(self, category: str | None = None) -> tuple[int, int]:
        if not self.available:
            return 0, 0

        if str(category or "").strip().casefold() == "rumors":
            if not self._rumor_catalog_available():
                return 0, 0
            row = self.connection.execute(
                """
                SELECT
                    SUM(CASE WHEN COALESCE(p.owned, 0) = 1 THEN 1 ELSE 0 END) AS owned_count,
                    COUNT(*) AS total_count
                FROM collectible_rumor r
                LEFT JOIN collectible_rumor_progress p
                  ON p.rumor_id = r.id AND p.profile_name = ?
                """,
                (self._active_profile,),
            ).fetchone()
            return int(row["owned_count"] or 0), int(row["total_count"] or 0)

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
        owned = int(row["owned_count"] or 0)
        total = int(row["total_count"] or 0)
        if category is None:
            rumor_owned, rumor_total = self.progress_summary("Rumors")
            owned += rumor_owned
            total += rumor_total
        return owned, total

    def collectibles(self, category: str, query: str = "") -> list[dict]:
        if not self.available:
            return []
        if str(category or "").strip().casefold() == "rumors":
            return self._rumor_rows(query)
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
        rumor_id = self._rumor_id_from_virtual(collectible_id)
        if rumor_id is not None:
            return self._rumor_detail(rumor_id)
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

        rumor_id = self._rumor_id_from_virtual(collectible_id)
        if rumor_id is not None:
            if not self._rumor_catalog_available():
                raise KeyError(f"Unknown rumor id: {rumor_id}")
            profile_name = self.ensure_profile(profile or self._active_profile)
            exists = self.connection.execute(
                "SELECT 1 FROM collectible_rumor WHERE id = ?",
                (int(rumor_id),),
            ).fetchone()
            if exists is None:
                raise KeyError(f"Unknown rumor id: {rumor_id}")
            self.connection.execute(
                """
                INSERT INTO collectible_rumor_progress(
                    profile_name, rumor_id, owned, acquired_on, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(profile_name, rumor_id) DO UPDATE SET
                    owned = excluded.owned,
                    acquired_on = excluded.acquired_on,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    profile_name,
                    int(rumor_id),
                    1 if owned else 0,
                    acquired_on.strip() or None,
                    notes.strip(),
                ),
            )
            self.connection.commit()
            return

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
                rumor_id = self._rumor_id_from_virtual(collectible_id)
                if rumor_id is not None:
                    db.execute(
                        """
                        INSERT INTO collectible_rumor_progress(profile_name, rumor_id, owned, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(profile_name, rumor_id) DO UPDATE SET
                            owned = excluded.owned,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (profile_name, int(rumor_id), 1 if owned else 0),
                    )
                    continue
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
