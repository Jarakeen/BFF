from __future__ import annotations

"""Profile-aware achievement progress.

Legacy/source tests may still point this service at achievement_progress.json.
Production now points it at foundrydock.db so user-owned progress is separated
from replaceable ESO reference data.
"""

import copy
import json
import os
import sqlite3
from pathlib import Path
from tempfile import NamedTemporaryFile

from services.achievement_progress_pydantic_schema import validate_achievement_progress_snapshot


class AchievementProgressService:
    VERSION = 2
    DEFAULT_PROFILE = "Default"

    def __init__(self, progress_path: Path) -> None:
        self.progress_path = Path(progress_path)
        self._database_mode = self.progress_path.suffix.casefold() in {".db", ".sqlite", ".sqlite3"}
        self._profiles: dict[str, set[str]] | None = None
        self._active_profile = self.DEFAULT_PROFILE
        if self._database_mode:
            self.progress_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_database_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.progress_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_database_schema(self) -> None:
        with self._connect() as db:
            db.executescript(
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
            db.execute(
                "INSERT OR IGNORE INTO achievement_profile(profile_name) VALUES (?)",
                (self.DEFAULT_PROFILE,),
            )

    def _ensure_loaded(self) -> None:
        if self._profiles is not None:
            return
        if self._database_mode:
            self._load_database()
            return

        self._profiles = {}
        if self.progress_path.exists():
            try:
                data = json.loads(self.progress_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError, TypeError) as exc:
                raise RuntimeError(
                    f"Achievement progress failed to load safely: {exc}"
                ) from exc
            if not isinstance(data, dict):
                raise RuntimeError("Achievement progress must contain a JSON object")

            raw_profiles = data.get("Profiles")
            if isinstance(raw_profiles, dict):
                for raw_name, raw_progress in raw_profiles.items():
                    name = self._normalize_profile_name(raw_name)
                    if not name or not isinstance(raw_progress, dict):
                        continue
                    completed = raw_progress.get("Completed", [])
                    if not isinstance(completed, list):
                        completed = []
                    self._profiles[name] = {str(value) for value in completed}
                requested = self._normalize_profile_name(data.get("ActiveProfile"))
                if requested in self._profiles:
                    self._active_profile = requested
            else:
                completed = data.get("Completed", [])
                if not isinstance(completed, list):
                    completed = []
                self._profiles[self.DEFAULT_PROFILE] = {
                    str(value) for value in completed
                }

        if not self._profiles:
            self._profiles[self.DEFAULT_PROFILE] = set()
        if self._active_profile not in self._profiles:
            self._active_profile = next(iter(self._profiles))

    def _load_database(self) -> None:
        self._profiles = {}
        self._ensure_database_schema()
        with self._connect() as db:
            profile_rows = db.execute(
                "SELECT profile_name FROM achievement_profile ORDER BY created_at, profile_name"
            ).fetchall()
            for row in profile_rows:
                name = self._normalize_profile_name(row["profile_name"])
                if name:
                    self._profiles[name] = set()

            for row in db.execute(
                """
                SELECT profile_name, achievement_id
                FROM achievement_progress
                WHERE completed = 1
                ORDER BY profile_name, achievement_id
                """
            ).fetchall():
                profile = self._normalize_profile_name(row["profile_name"]) or self.DEFAULT_PROFILE
                self._profiles.setdefault(profile, set()).add(str(row["achievement_id"]))

            meta = db.execute(
                "SELECT value FROM user_state_meta WHERE key='active_achievement_profile'"
            ).fetchone()
            requested = self._normalize_profile_name(meta["value"]) if meta else ""
            if requested in self._profiles:
                self._active_profile = requested

        if not self._profiles:
            self._profiles[self.DEFAULT_PROFILE] = set()
        if self._active_profile not in self._profiles:
            self._active_profile = next(iter(self._profiles))

    def reload(self, *, preserve_active_profile: bool = True) -> None:
        previous = self._active_profile if preserve_active_profile else self.DEFAULT_PROFILE
        self._profiles = None
        self._active_profile = self.DEFAULT_PROFILE
        self._ensure_loaded()
        if preserve_active_profile:
            normalized = self._normalize_profile_name(previous)
            if normalized in self._profiles:
                self._active_profile = normalized

    @staticmethod
    def _normalize_profile_name(name) -> str:
        return " ".join(str(name or "").strip().split())

    @property
    def active_profile(self) -> str:
        self._ensure_loaded()
        return self._active_profile

    def profiles(self) -> list[str]:
        self._ensure_loaded()
        return list(self._profiles)

    def ensure_profile(self, name: str) -> str:
        self._ensure_loaded()
        normalized = self._normalize_profile_name(name)
        if not normalized:
            raise ValueError("Profile name cannot be empty.")
        if normalized not in self._profiles:
            self._profiles[normalized] = set()
            self._save()
        return normalized

    def set_active_profile(self, name: str) -> str:
        normalized = self.ensure_profile(name)
        if normalized != self._active_profile:
            self._active_profile = normalized
            self._save()
        return self._active_profile

    def is_complete(self, achievement_id: str) -> bool:
        self._ensure_loaded()
        return str(achievement_id) in self._profiles[self._active_profile]

    def set_complete(self, achievement_id: str, complete: bool) -> None:
        self._ensure_loaded()
        achievement_id = str(achievement_id)
        completed = self._profiles[self._active_profile]
        if complete:
            completed.add(achievement_id)
        else:
            completed.discard(achievement_id)
        self._save()

    def completed_ids(self, profile: str | None = None) -> set[str]:
        self._ensure_loaded()
        profile_name = self._active_profile if profile is None else self._normalize_profile_name(profile)
        if profile_name not in self._profiles:
            return set()
        return set(self._profiles[profile_name])

    def completed_count(self, profile: str | None = None) -> int:
        return len(self.completed_ids(profile))

    def merge_completed(self, profile: str, achievement_ids) -> int:
        profile_name = self.ensure_profile(profile)
        before = len(self._profiles[profile_name])
        self._profiles[profile_name].update(str(value) for value in achievement_ids)
        added = len(self._profiles[profile_name]) - before
        if added:
            self._save()
        return added

    def replace_completed(self, profile: str, achievement_ids) -> None:
        profile_name = self.ensure_profile(profile)
        self._profiles[profile_name] = {str(value) for value in achievement_ids}
        self._save()

    def _validated_snapshot(self) -> dict:
        self._ensure_loaded()
        return validate_achievement_progress_snapshot(
            {
                "active_profile": self._active_profile,
                "profiles": {
                    name: tuple(sorted(completed))
                    for name, completed in self._profiles.items()
                },
            }
        )

    def _save(self) -> None:
        snapshot = self._validated_snapshot()
        if self._database_mode:
            self._save_database(snapshot)
            return
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "Version": self.VERSION,
            "ActiveProfile": snapshot["active_profile"],
            "Profiles": {
                name: {"Completed": list(completed)}
                for name, completed in snapshot["profiles"].items()
            },
        }
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.progress_path.parent,
                prefix=f".{self.progress_path.name}.", suffix=".tmp", delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.progress_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        read_back = json.loads(self.progress_path.read_text(encoding="utf-8"))
        if read_back != payload:
            raise RuntimeError("Achievement progress JSON did not round-trip exactly")

    def _save_database(self, snapshot: dict) -> None:
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("BEGIN")
            try:
                for profile, achievement_ids in snapshot["profiles"].items():
                    db.execute(
                        "INSERT OR IGNORE INTO achievement_profile(profile_name) VALUES (?)",
                        (profile,),
                    )
                    db.execute(
                        "DELETE FROM achievement_progress WHERE profile_name = ?",
                        (profile,),
                    )
                    db.executemany(
                        """
                        INSERT INTO achievement_progress(
                            profile_name, achievement_id, completed, updated_at
                        ) VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                        """,
                        [
                            (profile, achievement_id)
                            for achievement_id in achievement_ids
                        ],
                    )
                db.execute(
                    """
                    INSERT INTO user_state_meta(key, value)
                    VALUES ('active_achievement_profile', ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                    """,
                    (snapshot["active_profile"],),
                )
                persisted_profiles: dict[str, tuple[str, ...]] = {}
                for row in db.execute(
                    "SELECT profile_name FROM achievement_profile ORDER BY profile_name"
                ).fetchall():
                    profile_name = self._normalize_profile_name(row["profile_name"])
                    if profile_name in snapshot["profiles"]:
                        ids = tuple(
                            str(item["achievement_id"])
                            for item in db.execute(
                                """
                                SELECT achievement_id
                                FROM achievement_progress
                                WHERE profile_name = ? AND completed = 1
                                ORDER BY achievement_id
                                """,
                                (profile_name,),
                            ).fetchall()
                        )
                        persisted_profiles[profile_name] = ids
                meta = db.execute(
                    "SELECT value FROM user_state_meta WHERE key='active_achievement_profile'"
                ).fetchone()
                read_back = validate_achievement_progress_snapshot(
                    {
                        "active_profile": self._normalize_profile_name(meta["value"]) if meta else "",
                        "profiles": persisted_profiles,
                    }
                )
                if read_back != snapshot:
                    raise RuntimeError("Achievement progress did not round-trip exactly")
                db.commit()
            except Exception:
                db.rollback()
                raise
