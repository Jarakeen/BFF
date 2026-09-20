from __future__ import annotations

"""Targeted cleanup for Gear Lookup text stored in eso.db.

This is intentionally narrow: only color-rendering markup is removed from text
columns used by Gear Lookup. Rows, ids, relationships, mechanics, and schema are
left untouched.
"""

import sqlite3

from services.eso_text_cleanup import clean_eso_text


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _clean_column(
    connection: sqlite3.Connection,
    table: str,
    key_column: str,
    text_column: str,
    *,
    where: str = "",
) -> int:
    sql = f"SELECT {key_column}, {text_column} FROM {table}"
    if where:
        sql += f" WHERE {where}"
    changed = 0
    for key, raw in connection.execute(sql).fetchall():
        if raw is None:
            continue
        cleaned = clean_eso_text(raw)
        original = str(raw)
        if cleaned == original:
            continue
        connection.execute(
            f"UPDATE {table} SET {text_column} = ? WHERE {key_column} = ?",
            (cleaned, key),
        )
        changed += 1
    return changed


def clean_gear_lookup_database(connection: sqlite3.Connection) -> int:
    """Strip color markup from persisted Gear Lookup source rows in-place."""

    tables = _tables(connection)
    changed = 0

    if "gear_set" in tables:
        columns = _columns(connection, "gear_set")
        if "id" in columns and "name" in columns:
            changed += _clean_column(connection, "gear_set", "id", "name")
        if "id" in columns and "category" in columns:
            changed += _clean_column(connection, "gear_set", "id", "category")

    if "gear_set_bonus" in tables:
        columns = _columns(connection, "gear_set_bonus")
        if "id" in columns and "description" in columns:
            changed += _clean_column(
                connection,
                "gear_set_bonus",
                "id",
                "description",
            )

    if "entity" in tables:
        columns = _columns(connection, "entity")
        if {"id", "name", "entity_type"}.issubset(columns):
            changed += _clean_column(
                connection,
                "entity",
                "id",
                "name",
                where="entity_type = 'gear_set'",
            )

    if "content" in tables:
        columns = _columns(connection, "content")
        if "id" in columns and "name" in columns:
            changed += _clean_column(connection, "content", "id", "name")
        if "id" in columns and "location" in columns:
            changed += _clean_column(connection, "content", "id", "location")

    if changed:
        connection.commit()
    return changed


__all__ = ["clean_gear_lookup_database"]
