# ==================================================
# Black Feather Foundry
#
# File:
# services/eso_database.py
#
# Purpose:
# Provides access to the ESO SQLite database.
#
# This class owns the database connection and
# provides convenience methods for executing SQL.
#
# ==================================================

from __future__ import annotations

import sqlite3

from pathlib import Path


class EsoDatabase:
    """
    SQLite connection for ESO data.
    """

    def __init__(self, database: Path):

        self.database = Path(database)

        self._connection: sqlite3.Connection | None = None

    # --------------------------------------------------
    # Connection
    # --------------------------------------------------

    @property
    def connection(self) -> sqlite3.Connection:

        if self._connection is None:

            self._connection = sqlite3.connect(
                self.database
            )

            self._connection.row_factory = sqlite3.Row

        return self._connection

    # --------------------------------------------------
    # SQL
    # --------------------------------------------------

    def execute(
        self,
        sql: str,
        parameters: tuple = (),
    ) -> sqlite3.Cursor:

        return self.connection.execute(
            sql,
            parameters,
        )

    def executemany(
        self,
        sql: str,
        parameters,
    ) -> sqlite3.Cursor:

        return self.connection.executemany(
            sql,
            parameters,
        )

    def commit(self):

        self.connection.commit()

    def rollback(self):

        self.connection.rollback()

    def close(self):

        if self._connection is not None:

            self._connection.close()

            self._connection = None          

    def table_exists(
        self,
        table: str,
    ) -> bool:

        row = self.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name=?
            """,
            (table,),
        ).fetchone()

        return row is not None