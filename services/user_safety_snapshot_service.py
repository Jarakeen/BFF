from __future__ import annotations

"""Recoverable snapshots for high-risk user-state mutations."""

import re
import sqlite3
from datetime import datetime
from pathlib import Path

from engine.config import get_user_data_dir, get_user_database_path


class UserSafetySnapshotService:
    """Create consistent SQLite backups before destructive/bulk user actions."""

    def __init__(
        self,
        database_path: Path | None = None,
        backup_dir: Path | None = None,
        *,
        keep: int = 20,
    ) -> None:
        self.database_path = Path(database_path or get_user_database_path())
        self.backup_dir = Path(
            backup_dir or (get_user_data_dir() / "safety_snapshots")
        )
        self.keep = max(1, int(keep))

    @staticmethod
    def _slug(value: object) -> str:
        text = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip())
        return text.strip("-._") or "user-state"

    def create(self, reason: str) -> Path | None:
        if not self.database_path.is_file():
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        destination = self.backup_dir / (
            f"{stamp}__{self._slug(reason)}__foundrydock.db"
        )

        source = sqlite3.connect(self.database_path)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
            target.commit()
        finally:
            target.close()
            source.close()

        self._prune()
        return destination

    def _prune(self) -> None:
        rows = sorted(
            self.backup_dir.glob("*__foundrydock.db"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for stale in rows[self.keep :]:
            try:
                stale.unlink()
            except OSError:
                pass


__all__ = ["UserSafetySnapshotService"]
