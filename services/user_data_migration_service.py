from __future__ import annotations

"""One-way, additive migration of user-owned state out of the canonical ESO DB.

The legacy application stored replaceable ESO reference data and irreplaceable
user state in the same SQLite file. This module creates/updates foundrydock.db
without deleting or replacing the legacy source. Migration is deliberately
idempotent: existing user rows win, and legacy data is only copied into empty
or missing user-owned stores.
"""

import json
import sqlite3
from pathlib import Path

from engine.config import ensure_user_database, get_data_dir, get_user_database_path


_USER_TABLES_IN_COPY_ORDER = (
    "roster_member",
    "team",
    "team_member",
    "roster_member_assignment",
    "roster_member_availability",
    "roster_recruitment_candidate",
    "roster_archive_record",
    "roster_player_alias",
    "roster_assignment_context",
    "generated_roster_plan",
    "generated_roster_plan_slot",
    "generated_roster_draft",
    "generated_roster_draft_slot",
)


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(Path(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _table_count(connection: sqlite3.Connection, table: str) -> int:
    if not _table_exists(connection, table):
        return 0
    return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def _clone_table_schema(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    table: str,
) -> bool:
    if _table_exists(target, table):
        return True
    row = source.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    if row is None or not str(row["sql"] or "").strip():
        return False
    target.execute(str(row["sql"]))
    return True


def _copy_table_if_target_empty(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    table: str,
) -> int:
    if not _table_exists(source, table):
        return 0
    if not _clone_table_schema(source, target, table):
        return 0
    if _table_count(target, table):
        return 0

    source_columns = [
        str(row["name"])
        for row in source.execute(f'PRAGMA table_info("{table}")').fetchall()
    ]
    target_columns = {
        str(row["name"])
        for row in target.execute(f'PRAGMA table_info("{table}")').fetchall()
    }
    columns = [name for name in source_columns if name in target_columns]
    if not columns:
        return 0

    quoted = ", ".join(f'"{name}"' for name in columns)
    rows = source.execute(f'SELECT {quoted} FROM "{table}"').fetchall()
    if not rows:
        return 0
    placeholders = ", ".join("?" for _ in columns)
    target.executemany(
        f'INSERT OR IGNORE INTO "{table}" ({quoted}) VALUES ({placeholders})',
        [tuple(row[name] for name in columns) for row in rows],
    )
    return len(rows)


def _ensure_collectible_user_schema(target: sqlite3.Connection) -> None:
    target.executescript(
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


def _migrate_collectible_progress(
    legacy: sqlite3.Connection,
    target: sqlite3.Connection,
) -> int:
    _ensure_collectible_user_schema(target)
    if _table_count(target, "collectible_progress"):
        return 0
    if not _table_exists(legacy, "collectible_progress"):
        return 0

    columns = {
        str(row["name"])
        for row in legacy.execute("PRAGMA table_info(collectible_progress)").fetchall()
    }
    if "profile_name" in columns:
        rows = legacy.execute(
            """
            SELECT profile_name, collectible_id, owned, acquired_on, notes, updated_at
            FROM collectible_progress
            """
        ).fetchall()
    else:
        rows = legacy.execute(
            """
            SELECT 'Default' AS profile_name, collectible_id, owned, acquired_on,
                   notes, updated_at
            FROM collectible_progress
            """
        ).fetchall()

    profiles = {
        str(row["profile_name"] or "Default").strip() or "Default"
        for row in rows
    }
    target.executemany(
        "INSERT OR IGNORE INTO collectible_profile(profile_name) VALUES (?)",
        [(name,) for name in sorted(profiles)],
    )
    target.executemany(
        """
        INSERT OR IGNORE INTO collectible_progress(
            profile_name, collectible_id, owned, acquired_on, notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                str(row["profile_name"] or "Default").strip() or "Default",
                int(row["collectible_id"]),
                int(row["owned"] or 0),
                row["acquired_on"],
                str(row["notes"] or ""),
                str(row["updated_at"] or ""),
            )
            for row in rows
        ],
    )

    if _table_exists(legacy, "collectible_rumor_progress") and not _table_count(
        target, "collectible_rumor_progress"
    ):
        rumor_rows = legacy.execute(
            """
            SELECT profile_name, rumor_id, owned, acquired_on, notes, updated_at
            FROM collectible_rumor_progress
            """
        ).fetchall()
        target.executemany(
            """
            INSERT OR IGNORE INTO collectible_rumor_progress(
                profile_name, rumor_id, owned, acquired_on, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    str(row["profile_name"] or "Default").strip() or "Default",
                    int(row["rumor_id"]),
                    int(row["owned"] or 0),
                    row["acquired_on"],
                    str(row["notes"] or ""),
                    str(row["updated_at"] or "") or None,
                )
                for row in rumor_rows
            ],
        )
    return len(rows)


def _ensure_achievement_schema(target: sqlite3.Connection) -> None:
    target.executescript(
        """
        CREATE TABLE IF NOT EXISTS achievement_profile (
            profile_name TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS achievement_progress (
            profile_name TEXT NOT NULL,
            achievement_id TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 1 CHECK (completed IN (0, 1)),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (profile_name, achievement_id)
        );

        CREATE TABLE IF NOT EXISTS user_state_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );
        """
    )


def _migrate_achievement_json(
    achievement_path: Path,
    target: sqlite3.Connection,
) -> int:
    _ensure_achievement_schema(target)
    if _table_count(target, "achievement_progress") or not achievement_path.is_file():
        return 0
    try:
        raw = json.loads(achievement_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return 0

    raw_profiles = raw.get("Profiles")
    active = str(raw.get("ActiveProfile") or "Default").strip() or "Default"
    if isinstance(raw_profiles, dict):
        profiles = raw_profiles
    else:
        profiles = {"Default": {"Completed": raw.get("Completed", [])}}
        active = "Default"

    inserted = 0
    for raw_name, payload in profiles.items():
        profile = " ".join(str(raw_name or "").strip().split()) or "Default"
        target.execute(
            "INSERT OR IGNORE INTO achievement_profile(profile_name) VALUES (?)",
            (profile,),
        )
        completed = payload.get("Completed", []) if isinstance(payload, dict) else []
        if not isinstance(completed, list):
            completed = []
        for achievement_id in completed:
            target.execute(
                """
                INSERT OR IGNORE INTO achievement_progress(
                    profile_name, achievement_id, completed
                ) VALUES (?, ?, 1)
                """,
                (profile, str(achievement_id)),
            )
            inserted += 1

    target.execute(
        """
        INSERT INTO user_state_meta(key, value)
        VALUES ('active_achievement_profile', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        (active,),
    )
    return inserted


def migrate_legacy_user_data(
    *,
    legacy_database: Path | None = None,
    user_database: Path | None = None,
    achievement_progress: Path | None = None,
) -> dict[str, int]:
    """Copy legacy user state into foundrydock.db without mutating the source."""

    source_path = Path(legacy_database or (get_data_dir() / "eso.db"))
    target_path = Path(user_database or ensure_user_database())
    achievement_path = Path(
        achievement_progress or (get_data_dir() / "achievement_progress.json")
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    target = _connect(target_path)
    try:
        target.execute(
            """
            CREATE TABLE IF NOT EXISTS user_data_migration (
                migration_key TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        if source_path.is_file():
            source = _connect(source_path)
            try:
                for table in _USER_TABLES_IN_COPY_ORDER:
                    counts[table] = _copy_table_if_target_empty(source, target, table)
                counts["collectible_progress"] = _migrate_collectible_progress(
                    source, target
                )
            finally:
                source.close()
        else:
            _ensure_collectible_user_schema(target)
        counts["achievement_progress"] = _migrate_achievement_json(
            achievement_path, target
        )
        target.execute(
            """
            INSERT OR IGNORE INTO user_data_migration(migration_key)
            VALUES ('legacy_user_state_split_v1')
            """
        )
        target.commit()
    except Exception:
        target.rollback()
        raise
    finally:
        target.close()

    return counts


__all__ = [
    "get_user_database_path",
    "migrate_legacy_user_data",
]
