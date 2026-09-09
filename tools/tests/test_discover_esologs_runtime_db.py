from __future__ import annotations

import sqlite3
from pathlib import Path

from tools.discover_esologs_runtime_db import discover


def _db(path: Path, *, include_runtime_tables: bool) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE ordinary_table (id INTEGER)")
        if include_runtime_tables:
            connection.executescript(
                """
                CREATE TABLE log_fight (id INTEGER);
                CREATE TABLE log_actor (id INTEGER);
                CREATE TABLE log_event (id INTEGER);
                """
            )
        connection.commit()
    finally:
        connection.close()


def test_discover_finds_only_database_with_all_runtime_tables(tmp_path: Path) -> None:
    ordinary = tmp_path / "eso.db"
    runtime = tmp_path / "logs.sqlite"
    _db(ordinary, include_runtime_tables=False)
    _db(runtime, include_runtime_tables=True)

    assert discover(roots=(tmp_path,)) == (runtime.resolve(),)


def test_discover_deduplicates_overlapping_roots(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    runtime = nested / "combat.sqlite3"
    _db(runtime, include_runtime_tables=True)

    assert discover(roots=(tmp_path, nested)) == (runtime.resolve(),)


def test_discover_returns_empty_when_runtime_tables_were_never_imported(tmp_path: Path) -> None:
    ordinary = tmp_path / "eso.db"
    _db(ordinary, include_runtime_tables=False)

    assert discover(roots=(tmp_path,)) == ()
