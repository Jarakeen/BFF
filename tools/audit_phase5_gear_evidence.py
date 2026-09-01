from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE


DEFAULT_SET_NAMES = (
    "Magma Incarnate",
    "Spaulder of Ruin",
    "Serpent's Disdain",
)


def _table_columns(db: sqlite3.Connection, table: str) -> tuple[str, ...]:
    try:
        rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    except sqlite3.DatabaseError:
        return ()
    return tuple(str(row[1]) for row in rows)


def _safe_rows(db: sqlite3.Connection, sql: str, parameters=()):
    try:
        return db.execute(sql, parameters).fetchall()
    except sqlite3.DatabaseError as exc:
        return [(f"<query failed: {exc}>",)]


def audit_set(db: sqlite3.Connection, requested_name: str) -> None:
    set_row = db.execute(
        """
        SELECT id, name, category, max_equip_count
        FROM gear_set
        WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
        """,
        (requested_name,),
    ).fetchone()

    print()
    print("----------------------------------------")
    print(requested_name)
    print("----------------------------------------")

    if set_row is None:
        print("gear_set row: NOT FOUND")
        return

    set_id, name, category, max_equip_count = set_row
    print(
        f"gear_set: id={set_id} | name={name!r} | "
        f"category={category!r} | max_equip_count={max_equip_count!r}"
    )

    piece_columns = _table_columns(db, "gear_set_piece")
    if piece_columns:
        print("pieces:")
        piece_rows = _safe_rows(
            db,
            """
            SELECT equip_type, armor_type, weapon_type
            FROM gear_set_piece
            WHERE set_id = ?
            ORDER BY equip_type, armor_type, weapon_type
            """,
            (set_id,),
        )
        if not piece_rows:
            print("  (none)")
        for equip_type, armor_type, weapon_type in piece_rows:
            print(
                f"  - equip_type={equip_type!r} | "
                f"armor_type={armor_type!r} | weapon_type={weapon_type!r}"
            )
    else:
        print("pieces: gear_set_piece table unavailable")

    item_columns = _table_columns(db, "gear_set_item")
    if item_columns:
        item_rows = _safe_rows(
            db,
            "SELECT item_id FROM gear_set_item WHERE set_id = ? ORDER BY item_id",
            (set_id,),
        )
        item_ids = [str(row[0]) for row in item_rows if row]
        print(
            "source item ids: "
            + (", ".join(item_ids[:20]) if item_ids else "(none)")
            + (f" ... ({len(item_ids)} total)" if len(item_ids) > 20 else "")
        )

    print("bonus rows:")
    bonus_rows = _safe_rows(
        db,
        """
        SELECT id, piece_count, description
        FROM gear_set_bonus
        WHERE set_id = ?
        ORDER BY piece_count, id
        """,
        (set_id,),
    )
    if not bonus_rows:
        print("  (none)")
    for bonus_id, piece_count, description in bonus_rows:
        text = " ".join(str(description or "").split())
        print(f"  - bonus_id={bonus_id} | pieces={piece_count} | {text}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only evidence audit for Phase 5 gear classification and "
            "verified EffectVariant mapping."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("sets", nargs="*", default=list(DEFAULT_SET_NAMES))
    args = parser.parse_args()

    if not args.database.exists():
        print(f"Database not found: {args.database}")
        return 1

    print("========================================")
    print(" PHASE 5 GEAR EVIDENCE AUDIT")
    print("========================================")
    print(f"Database: {args.database}")
    print("Read only: no database or saved-build data will be changed.")

    try:
        with sqlite3.connect(args.database) as db:
            required = {"gear_set", "gear_set_bonus"}
            missing = [table for table in required if not _table_columns(db, table)]
            if missing:
                print(f"Missing required table(s): {', '.join(sorted(missing))}")
                return 2
            for set_name in args.sets or DEFAULT_SET_NAMES:
                audit_set(db, set_name)
    except sqlite3.DatabaseError as exc:
        print(f"Database error: {exc}")
        return 3

    print()
    print("Audit only: no database or saved-build data were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
