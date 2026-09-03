from __future__ import annotations

from pathlib import Path
import sqlite3

from tools.import_boss_encounter_structure import (
    _backup_database,
    _default_backup_path,
)


def test_backup_database_creates_independent_sqlite_copy(tmp_path: Path) -> None:
    source_path = tmp_path / "eso.db"
    backup_path = tmp_path / "eso.db.backup"

    source = sqlite3.connect(source_path)
    try:
        source.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
        source.execute("INSERT INTO sample(value) VALUES ('before')")
        source.commit()

        _backup_database(source, backup_path)

        source.execute("INSERT INTO sample(value) VALUES ('after')")
        source.commit()
    finally:
        source.close()

    backup = sqlite3.connect(backup_path)
    try:
        assert backup.execute("SELECT value FROM sample ORDER BY id").fetchall() == [
            ("before",)
        ]
    finally:
        backup.close()


def test_default_backup_path_is_timestamped_sibling(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"

    backup = _default_backup_path(database)

    assert backup.parent == database.parent
    assert backup != database
    assert backup.name.startswith("eso.db.before-boss-structural-import.")
