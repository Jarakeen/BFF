#!/usr/bin/env python3
"""Read-only preflight audit for Alchemy DB imports.

Lists source Alchemy effect names that already exist in ``effect`` and shows
those rows' current categories and variant types. This makes shared canonical
effect reuse visible before the Alchemy importer is allowed to commit.

Never modifies ``eso.db``.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "processed" / "alchemy_effects.json"
DEFAULT_DB = ROOT / "data" / "eso.db"


def load_names(path: Path) -> tuple[str, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("effects", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Alchemy dataset has no effects list")
    return tuple(
        str(row.get("effect_name") or row.get("name") or "").strip()
        for row in rows
        if isinstance(row, dict) and str(row.get("effect_name") or row.get("name") or "").strip()
    )


def audit(*, database_path: Path, input_path: Path) -> int:
    names = load_names(input_path)
    print("========================================")
    print(" PHASE 5 ALCHEMY DB COLLISION AUDIT")
    print("========================================")
    print(f"Input:    {input_path}")
    print(f"Database: {database_path}")
    print(f"Source effects: {len(names)}")
    print()

    collisions = 0
    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        for name in names:
            row = db.execute(
                """
                SELECT id, name, category
                FROM effect
                WHERE lower(trim(name)) = lower(trim(?))
                ORDER BY id
                LIMIT 1
                """,
                (name,),
            ).fetchone()
            if row is None:
                continue
            collisions += 1
            variants = db.execute(
                """
                SELECT type, COUNT(*) AS count
                FROM effect_variant
                WHERE effect_id = ?
                GROUP BY lower(trim(COALESCE(type, ''))), type
                ORDER BY lower(trim(COALESCE(type, '')))
                """,
                (int(row["id"]),),
            ).fetchall()
            variant_text = ", ".join(
                f"{str(item['type'] or '<blank>')} x{int(item['count'])}" for item in variants
            ) or "none"
            print(
                f"  - {row['name']} | effect_id={row['id']} | "
                f"category={row['category']!r} | variants={variant_text}"
            )

    print()
    print(f"Existing-name collisions: {collisions}")
    print(f"New effect names:          {len(names) - collisions}")
    print("Database unchanged.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit existing effect names before Alchemy DB import")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(audit(database_path=args.db, input_path=args.input))
