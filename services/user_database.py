from __future__ import annotations

"""Resolve the writable FoundryDock user database at application boundaries."""

from pathlib import Path

from engine.config import get_data_dir, get_user_database_path
from services.eso_database import EsoDatabase
from services.user_data_migration_service import migrate_legacy_user_data


def user_database_for(database: EsoDatabase | Path | str | None = None) -> EsoDatabase:
    """Return the user-owned DB for the canonical app DB, preserving test DBs.

    Unit tests and explicit tools often pass temporary SQLite paths and should
    keep using those isolated files. Only the real application data/eso.db is
    redirected to user_data/foundrydock.db.
    """

    if isinstance(database, EsoDatabase):
        path = Path(database.database)
    elif database is None:
        path = get_data_dir() / "eso.db"
    else:
        path = Path(database)

    try:
        is_canonical = path.resolve() == (get_data_dir() / "eso.db").resolve()
    except OSError:
        is_canonical = path == (get_data_dir() / "eso.db")

    if not is_canonical:
        return database if isinstance(database, EsoDatabase) else EsoDatabase(path)

    migrate_legacy_user_data()
    return EsoDatabase(get_user_database_path())


__all__ = ["user_database_for"]
