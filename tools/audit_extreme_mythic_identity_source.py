from __future__ import annotations

"""Read-only audit of canonical Mythic identity evidence in eso.db."""

import argparse
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    "Torc of Tonal Constancy",
    "Stormweaver's Cavort",
    "Oakensoul Ring",
    "Ring of the Pale Order",
    "Harpooner's Wading Kilt",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def main() -> int:
    database = Path(_parser().parse_args().database)
    print("EXTREME MYTHIC IDENTITY SOURCE AUDIT")
    print(f"database={database}")

    connection = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    with connection:
        print("\nGEAR_SET ROWS")
        placeholders = ",".join("?" for _ in TARGETS)
        rows = connection.execute(
            f"SELECT * FROM gear_set WHERE name IN ({placeholders}) ORDER BY name",
            TARGETS,
        ).fetchall()
        for row in rows:
            values = {key: row[key] for key in row.keys()}
            print(repr(values))

        print("\nTABLE/COLUMN NAME REFERENCES")
        tables = tuple(
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        )
        for table in tables:
            columns = connection.execute(f"PRAGMA table_info({_quote(table)})").fetchall()
            candidate_columns = tuple(
                str(column[1])
                for column in columns
                if any(
                    token in str(column[1]).casefold()
                    for token in ("name", "set", "mythic", "antiqu", "category", "type")
                )
            )
            if not candidate_columns:
                continue
            for column in candidate_columns:
                try:
                    query = (
                        f"SELECT rowid, {_quote(column)} AS value FROM {_quote(table)} "
                        f"WHERE CAST({_quote(column)} AS TEXT) IN ({placeholders}) LIMIT 20"
                    )
                    matches = connection.execute(query, TARGETS).fetchall()
                except sqlite3.Error:
                    continue
                for match in matches:
                    print(f"table={table!r} column={column!r} rowid={match['rowid']!r} value={match['value']!r}")

        print("\nMYTHIC/ANTIQUITY-LIKE SCHEMA")
        for table in tables:
            columns = connection.execute(f"PRAGMA table_info({_quote(table)})").fetchall()
            names = tuple(str(column[1]) for column in columns)
            folded = " ".join((table, *names)).casefold()
            if "mythic" in folded or "antiqu" in folded:
                print(f"table={table!r} columns={names!r}")

    print("\nNEXT_STEP=use the printed canonical marker to fix shared one-Mythic legality, then rerun Torc")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
