from __future__ import annotations

"""Profile-aware collectible ownership with split reference/user persistence."""

import csv
import sqlite3
from pathlib import Path

from engine.config import get_data_dir, get_user_database_path
from services.eso_collectible_database_service import EsoCollectibleDatabaseService
from services.user_data_migration_service import migrate_legacy_user_data


class ProfiledCollectibleService(EsoCollectibleDatabaseService):
    """Keep the ESO collectible catalog in eso.db and ownership in foundrydock.db.

    Existing single-profile progress is migrated conservatively to Default.
    """

    DEFAULT_PROFILE = "Default"

    def __init__(
        self,
        database_path: Path,
        progress_database_path: Path | None = None,
    ) -> None:
        self._requested_catalog_path = Path(database_path)
        if progress_database_path is None:
            try:
                is_app_catalog = self._requested_catalog_path.resolve() == (
                    get_data_dir() / "eso.db"
                ).resolve()
            except OSError:
                is_app_catalog = self._requested_catalog_path == (get_data_dir() / "eso.db")
            if is_app_catalog:
                migrate_legacy_user_data(legacy_database=self._requested_catalog_path)
            progress_database_path = (
                get_user_database_path() if is_app_catalog else self._requested_catalog_path
            )

        self.progress_database_path = Path(progress_database_path)
        self._progress_connection: sqlite3.Connection | None = None
        self._active_profile = self.DEFAULT_PROFILE
        super().__init__(self._requested_catalog_path)
        if self.available:
            self._ensure_profile_schema()

    @property
    def progress_connection(self) -> sqlite3.Connection:
        if self.progress_database_path == self.database_path:
            return self.connection
        if self._progress_connection is None:
            self.progress_database_path.parent.mkdir(parents=True, exist_ok=True)
            self._progress_connection = sqlite3.connect(self.progress_database_path)
            self._progress_connection.row_factory = sqlite3.Row
            self._progress_connection.execute("PRAGMA foreign_keys = ON")
        return self._progress_connection

    @staticmethod
    def _normalize_profile_name(name) -> str:
        return " ".join(str(name or "").strip().split())

    def _ensure_profile_schema(self) -> None:
        db = self.progress_connection
        columns = {
            str(row["name"])
            for row in db.execute("PRAGMA table_info(collectible_progress)").fetchall()
        }

        # In an old single-DB workspace, preserve the legacy unprofiled rows by
        # migrating them in-place. A new foundrydock.db starts directly profiled.
        if columns and "profile_name" not in columns:
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
                        PRIMARY KEY (profile_name, collectible_id)
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
                db.execute(
                    "ALTER TABLE collectible_progress_profiled RENAME TO collectible_progress"
                )
                db.commit()
            except Exception:
                db.rollback()
                raise

        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS collectible_profile (
                profile_name TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS collectible_progress (
                profile_name TEXT NOT NULL,
                collectible_id INTEGER NOT NULL,
                owned INTEGER NOT NULL DEFAULT 0 CHECK (owned IN (0, 1)),
                acquired_on TEXT,
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (profile_name, collectible_id)
            );

            CREATE INDEX IF NOT EXISTS idx_collectible_progress_profile_owned
                ON collectible_progress(profile_name, owned);

            CREATE TABLE IF NOT EXISTS collectible_rumor_progress (
                profile_name TEXT NOT NULL,
                rumor_id INTEGER NOT NULL,
                owned INTEGER NOT NULL DEFAULT 0 CHECK (owned IN (0, 1)),
                acquired_on TEXT,
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (profile_name, rumor_id)
            );

            CREATE INDEX IF NOT EXISTS idx_collectible_rumor_progress_profile_owned
                ON collectible_rumor_progress(profile_name, owned);
            """
        )
        db.execute(
            "INSERT OR IGNORE INTO collectible_profile(profile_name) VALUES (?)",
            (self.DEFAULT_PROFILE,),
        )
        db.execute(
            """
            INSERT OR IGNORE INTO collectible_profile(profile_name)
            SELECT DISTINCT profile_name FROM collectible_progress
            WHERE profile_name IS NOT NULL AND TRIM(profile_name) <> ''
            """
        )
        db.commit()

    def _rumor_catalog_available(self) -> bool:
        return self._table_exists("collectible_rumor")

    @staticmethod
    def _rumor_virtual_id(rumor_id: int) -> int:
        return -int(rumor_id)

    @staticmethod
    def _rumor_id_from_virtual(collectible_id: int) -> int | None:
        value = int(collectible_id)
        return -value if value < 0 else None

    def _progress_map(self, collectible_ids: list[int] | tuple[int, ...]) -> dict[int, dict]:
        ids = [int(value) for value in collectible_ids]
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self.progress_connection.execute(
            f"""
            SELECT collectible_id, owned, acquired_on, notes, updated_at
            FROM collectible_progress
            WHERE profile_name = ?
              AND collectible_id IN ({placeholders})
            """,
            [self._active_profile, *ids],
        ).fetchall()
        return {int(row["collectible_id"]): dict(row) for row in rows}

    def _rumor_progress_map(self, rumor_ids: list[int] | tuple[int, ...]) -> dict[int, dict]:
        ids = [int(value) for value in rumor_ids]
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self.progress_connection.execute(
            f"""
            SELECT rumor_id, owned, acquired_on, notes, updated_at
            FROM collectible_rumor_progress
            WHERE profile_name = ?
              AND rumor_id IN ({placeholders})
            """,
            [self._active_profile, *ids],
        ).fetchall()
        return {int(row["rumor_id"]): dict(row) for row in rows}

    def _rumor_rows(self, query: str = "") -> list[dict]:
        if not self._rumor_catalog_available():
            return []
        query = str(query or "").strip()
        params: list[object] = []
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
            SELECT r.id AS rumor_id, r.name, r.start_hint, r.background_text,
                   r.complete_text, r.declared_hint_count
            FROM collectible_rumor r
            {where}
            ORDER BY r.name COLLATE NOCASE, r.id
            """,
            params,
        ).fetchall()
        progress = self._rumor_progress_map([int(row["rumor_id"]) for row in rows])

        result: list[dict] = []
        for row in rows:
            rumor_id = int(row["rumor_id"])
            state = progress.get(rumor_id, {})
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
                    "owned": int(state.get("owned") or 0),
                    "acquired_on": str(state.get("acquired_on") or ""),
                    "notes": str(state.get("notes") or ""),
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
        parts = []
        for hint in hints:
            label = str(hint["name"] or "").strip()
            description = str(hint["description"] or "").strip()
            text = " — ".join(part for part in (label, description) if part)
            if text:
                parts.append(f"{int(hint['hint_index']) + 1}. {text}")
        start = str(detail.get("hint") or "").strip()
        detail["hint"] = "\n".join(([start] if start else []) + parts)
        return detail

    @property
    def active_profile(self) -> str:
        return self._active_profile

    def profiles(self) -> list[str]:
        rows = self.progress_connection.execute(
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
        self.progress_connection.execute(
            "INSERT OR IGNORE INTO collectible_profile(profile_name) VALUES (?)",
            (normalized,),
        )
        self.progress_connection.commit()
        return normalized

    def set_active_profile(self, name: str) -> str:
        self._active_profile = self.ensure_profile(name)
        return self._active_profile

    def progress_summary(self, category: str | None = None) -> tuple[int, int]:
        if not self.available:
            return 0, 0
        if str(category or "").strip().casefold() == "rumors":
            rows = self._rumor_rows()
            return sum(1 for row in rows if row.get("owned")), len(rows)

        params: list[object] = []
        where = ""
        if category:
            where = "WHERE sidebar_category_key = ?"
            params.append(category)
        rows = self.connection.execute(
            f"SELECT id FROM collectible {where}",
            params,
        ).fetchall()
        ids = [int(row["id"]) for row in rows]
        progress = self._progress_map(ids)
        owned = sum(1 for cid in ids if int(progress.get(cid, {}).get("owned") or 0) == 1)
        total = len(ids)
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
        params: list[object] = [category]
        where = "c.sidebar_category_key = ?"
        if query:
            pattern = f"%{query}%"
            where += " AND (c.name LIKE ? OR c.description LIKE ? OR c.hint LIKE ? OR c.source_subcategory_name LIKE ?)"
            params.extend([pattern] * 4)

        rows = self.connection.execute(
            f"""
            SELECT c.id, c.name, c.description, c.hint, c.icon,
                   c.canonical_type_key, c.source_subcategory_name,
                   c.is_unlocked, c.is_usable, c.is_renameable
            FROM collectible c
            WHERE {where}
            ORDER BY c.name COLLATE NOCASE, c.id
            """,
            params,
        ).fetchall()
        progress = self._progress_map([int(row["id"]) for row in rows])
        result = []
        for row in rows:
            item = dict(row)
            state = progress.get(int(row["id"]), {})
            item["owned"] = int(state.get("owned") or 0)
            item["acquired_on"] = str(state.get("acquired_on") or "")
            item["notes"] = str(state.get("notes") or "")
            result.append(item)
        return result

    def collectible(self, collectible_id: int) -> dict | None:
        if not self.available:
            return None
        rumor_id = self._rumor_id_from_virtual(collectible_id)
        if rumor_id is not None:
            return self._rumor_detail(rumor_id)

        row = self.connection.execute(
            "SELECT * FROM collectible_search WHERE id = ?",
            (int(collectible_id),),
        ).fetchone()
        if row is None:
            return None
        item = dict(row)
        state = self._progress_map([int(collectible_id)]).get(int(collectible_id), {})
        item["owned"] = int(state.get("owned") or 0)
        item["acquired_on"] = str(state.get("acquired_on") or "")
        item["notes"] = str(state.get("notes") or "")
        item["progress_updated_at"] = str(state.get("updated_at") or "")
        return item

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
        profile_name = self.ensure_profile(profile or self._active_profile)
        rumor_id = self._rumor_id_from_virtual(collectible_id)
        db = self.progress_connection

        if rumor_id is not None:
            if not self._rumor_catalog_available():
                raise KeyError(f"Unknown rumor id: {rumor_id}")
            exists = self.connection.execute(
                "SELECT 1 FROM collectible_rumor WHERE id = ?",
                (int(rumor_id),),
            ).fetchone()
            if exists is None:
                raise KeyError(f"Unknown rumor id: {rumor_id}")
            db.execute(
                """
                INSERT INTO collectible_rumor_progress(
                    profile_name, rumor_id, owned, acquired_on, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(profile_name, rumor_id) DO UPDATE SET
                    owned=excluded.owned,
                    acquired_on=excluded.acquired_on,
                    notes=excluded.notes,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    profile_name,
                    int(rumor_id),
                    1 if owned else 0,
                    acquired_on.strip() or None,
                    notes.strip(),
                ),
            )
            db.commit()
            return

        exists = self.connection.execute(
            "SELECT 1 FROM collectible WHERE id = ?",
            (int(collectible_id),),
        ).fetchone()
        if exists is None:
            raise KeyError(f"Unknown collectible id: {collectible_id}")

        db.execute(
            """
            INSERT INTO collectible_progress(
                profile_name, collectible_id, owned, acquired_on, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(profile_name, collectible_id) DO UPDATE SET
                owned=excluded.owned,
                acquired_on=excluded.acquired_on,
                notes=excluded.notes,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                profile_name,
                int(collectible_id),
                1 if owned else 0,
                acquired_on.strip() or None,
                notes.strip(),
            ),
        )
        db.commit()

    def set_owned_batch(self, profile: str, owned_by_id: dict[int, bool]) -> int:
        profile_name = self.ensure_profile(profile)
        if not owned_by_id:
            return 0
        db = self.progress_connection
        db.execute("BEGIN")
        try:
            for collectible_id, owned in owned_by_id.items():
                rumor_id = self._rumor_id_from_virtual(collectible_id)
                if rumor_id is not None:
                    db.execute(
                        """
                        INSERT INTO collectible_rumor_progress(
                            profile_name, rumor_id, owned, updated_at
                        ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(profile_name, rumor_id) DO UPDATE SET
                            owned=excluded.owned,
                            updated_at=CURRENT_TIMESTAMP
                        """,
                        (profile_name, int(rumor_id), 1 if owned else 0),
                    )
                else:
                    db.execute(
                        """
                        INSERT INTO collectible_progress(
                            profile_name, collectible_id, owned, updated_at
                        ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(profile_name, collectible_id) DO UPDATE SET
                            owned=excluded.owned,
                            updated_at=CURRENT_TIMESTAMP
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
            SELECT id, name, sidebar_category_key, canonical_type_key,
                   source_subcategory_name
            FROM collectible
            ORDER BY sidebar_category_key, name COLLATE NOCASE, id
            """
        ).fetchall()
        progress = self._progress_map([int(row["id"]) for row in rows])
        with target_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["Profile", "Collectible ID", "Name", "Category", "Type", "Subtype", "Owned", "Acquired On", "Notes"]
            )
            for row in rows:
                state = progress.get(int(row["id"]), {})
                writer.writerow(
                    [
                        self._active_profile,
                        row["id"],
                        row["name"],
                        row["sidebar_category_key"],
                        row["canonical_type_key"],
                        row["source_subcategory_name"],
                        int(state.get("owned") or 0),
                        str(state.get("acquired_on") or ""),
                        str(state.get("notes") or ""),
                    ]
                )
        return target_path

    def close(self) -> None:
        if self._progress_connection is not None:
            self._progress_connection.close()
            self._progress_connection = None
        super().close()
