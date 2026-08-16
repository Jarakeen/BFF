#!/usr/bin/env python3
"""
Black Feather Foundry
UESP Alchemy Effects DB Importer

Imports the validated UESP alchemy dataset:

    data/processed/alchemy_effects.json

into:

    data/eso.db

Design goals
------------
- Safe by default: no DB changes unless --commit is supplied.
- Idempotent: running it repeatedly does not duplicate effects, variants,
  or UESP source rows.
- Reuses existing effects when their names already exist.
- Does NOT overwrite existing effect data.
- Stores the complete UESP alchemy record in effect_variant.raw_json so
  reagent/formula/tier data is not lost.
- Creates two alchemy variants per effect where available:
      Potion
      Poison
- Uses effect_source for UESP provenance.
- Wraps a commit in one transaction and makes a timestamped DB backup first.

Usage
-----
Dry run:
    python importers/import_uesp_alchemy_effects_db.py

Commit:
    python importers/import_uesp_alchemy_effects_db.py --commit

Optional:
    --input data/processed/alchemy_effects.json
    --db data/eso.db
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "processed" / "alchemy_effects.json"
DEFAULT_DB = ROOT / "data" / "eso.db"


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def norm(value: Any) -> str:
    return " ".join(clean(value).casefold().replace("’", "'").split())


def load_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Alchemy dataset not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        effects = data.get("effects")
    else:
        effects = data

    if not isinstance(effects, list):
        raise ValueError("Expected alchemy_effects.json to contain an 'effects' list.")

    valid = []
    for row in effects:
        if not isinstance(row, dict):
            continue
        name = clean(row.get("effect_name") or row.get("name"))
        if not name:
            continue
        row = dict(row)
        row["effect_name"] = name
        valid.append(row)

    if not valid:
        raise ValueError("No usable alchemy effects were found in the dataset.")

    return valid


def backup_database(db_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_name(f"{db_path.stem}.pre_alchemy_{stamp}{db_path.suffix}")
    shutil.copy2(db_path, backup)
    return backup


def get_effect_columns(db: sqlite3.Connection) -> set[str]:
    return {row[1] for row in db.execute("PRAGMA table_info(effect)")}


def get_variant_columns(db: sqlite3.Connection) -> set[str]:
    return {row[1] for row in db.execute("PRAGMA table_info(effect_variant)")}


def find_effect(db: sqlite3.Connection, name: str):
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
    return row


def create_effect(db: sqlite3.Connection, name: str) -> int:
    """
    Create an effect only when it does not already exist.

    Existing effect rows are intentionally left untouched.
    """
    columns = get_effect_columns(db)

    if "raw_section" in columns and "raw_json" in columns and "icon" in columns:
        cur = db.execute(
            """
            INSERT INTO effect (name, category, icon, raw_section, raw_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                "alchemy",
                None,
                "UESP Alchemy",
                json.dumps(
                    {
                        "name": name,
                        "category": "alchemy",
                        "section": "UESP Alchemy",
                    },
                    ensure_ascii=False,
                ),
            ),
        )
    else:
        cur = db.execute(
            """
            INSERT INTO effect (name, category)
            VALUES (?, ?)
            """,
            (name, "alchemy"),
        )

    return int(cur.lastrowid)


def find_variant(db: sqlite3.Connection, effect_id: int, variant_type: str):
    """
    Prefer an exact effect_id + type match.

    If an existing variant is found, it is reused and never overwritten.
    """
    return db.execute(
        """
        SELECT id, effect_id, type, description, icon, raw_json
        FROM effect_variant
        WHERE effect_id = ?
          AND lower(trim(COALESCE(type, ''))) = lower(trim(?))
        ORDER BY id
        LIMIT 1
        """,
        (effect_id, variant_type),
    ).fetchone()


def create_variant(
    db: sqlite3.Connection,
    effect_id: int,
    variant_type: str,
    description: str,
    raw_json: dict[str, Any],
) -> tuple[int, bool]:
    existing = find_variant(db, effect_id, variant_type)
    if existing:
        return int(existing[0]), False

    columns = get_variant_columns(db)

    payload = json.dumps(raw_json, ensure_ascii=False)

    if "icon" in columns:
        cur = db.execute(
            """
            INSERT INTO effect_variant
                (effect_id, type, description, icon, raw_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (effect_id, variant_type, description or None, None, payload),
        )
    else:
        cur = db.execute(
            """
            INSERT INTO effect_variant
                (effect_id, type, description, raw_json)
            VALUES (?, ?, ?, ?)
            """,
            (effect_id, variant_type, description or None, payload),
        )

    return int(cur.lastrowid), True


def source_exists(
    db: sqlite3.Connection,
    variant_id: int,
    source_name: str,
) -> bool:
    row = db.execute(
        """
        SELECT 1
        FROM effect_source
        WHERE effect_variant_id = ?
          AND source_type = ?
          AND source_name = ?
        LIMIT 1
        """,
        (variant_id, "UESP", source_name),
    ).fetchone()
    return row is not None


def add_source(
    db: sqlite3.Connection,
    variant_id: int,
    effect_name: str,
    variant_type: str,
    raw_record: dict[str, Any],
) -> bool:
    source_name = f"{effect_name} ({variant_type})"

    if source_exists(db, variant_id, source_name):
        return False

    source_files = raw_record.get("source_files", [])
    if not isinstance(source_files, list):
        source_files = []

    raw_text = ", ".join(clean(x) for x in source_files if clean(x))

    db.execute(
        """
        INSERT INTO effect_source
            (effect_variant_id, source_type, source_name, condition, raw_text)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            variant_id,
            "UESP",
            source_name,
            "Alchemy",
            raw_text or None,
        ),
    )
    return True


def variant_description(effect: dict[str, Any], kind: str) -> str:
    """
    Build a compact description without inventing game text.

    The source pages do not provide a dedicated description field in the
    normalized V3 schema, so this identifies what the variant contains.
    """
    tiers = effect.get(f"{kind}_tiers", [])
    if not isinstance(tiers, list):
        tiers = []

    formulas = effect.get("formulas", [])
    if not isinstance(formulas, list):
        formulas = []

    return (
        f"UESP Alchemy {kind.title()} data for {effect['effect_name']}. "
        f"{len(tiers)} tiers; {len(formulas)} formulas in source dataset."
    )


def variant_payload(effect: dict[str, Any], kind: str) -> dict[str, Any]:
    """
    Keep the entire effect record available from the variant.

    This deliberately stores the source structure instead of trying to
    squeeze reagent/formula data into effect_source.raw_text.
    """
    payload = {
        "source": "UESP",
        "source_kind": "alchemy_effect_page",
        "effect_name": effect["effect_name"],
        "effect_slug": effect.get("effect_slug"),
        "variant": kind,
        "reagents": effect.get("reagents", []),
        "tiers": effect.get(f"{kind}_tiers", []),
        "formulas": effect.get("formulas", []),
        "source_files": effect.get("source_files", []),
    }

    return payload


def import_effects(
    db: sqlite3.Connection,
    effects: list[dict[str, Any]],
    commit: bool,
) -> dict[str, int]:
    stats = {
        "effects_existing": 0,
        "effects_created": 0,
        "variants_existing": 0,
        "variants_created": 0,
        "sources_existing": 0,
        "sources_added": 0,
        "potion_variants": 0,
        "poison_variants": 0,
    }

    for effect in effects:
        name = effect["effect_name"]

        existing = find_effect(db, name)
        if existing:
            effect_id = int(existing[0])
            stats["effects_existing"] += 1
        else:
            effect_id = create_effect(db, name)
            stats["effects_created"] += 1

        for kind in ("potion", "poison"):
            tiers = effect.get(f"{kind}_tiers", [])
            if not isinstance(tiers, list) or not tiers:
                continue

            variant_type = kind.title()
            description = variant_description(effect, kind)
            payload = variant_payload(effect, kind)

            variant_id, created = create_variant(
                db,
                effect_id,
                variant_type,
                description,
                payload,
            )

            if created:
                stats["variants_created"] += 1
            else:
                stats["variants_existing"] += 1

            if kind == "potion":
                stats["potion_variants"] += 1
            else:
                stats["poison_variants"] += 1

            added = add_source(
                db,
                variant_id,
                name,
                variant_type,
                effect,
            )

            if added:
                stats["sources_added"] += 1
            else:
                stats["sources_existing"] += 1

    if commit:
        db.commit()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import UESP alchemy effects into Foundry's SQLite database."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Processed UESP alchemy JSON.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="Foundry SQLite database.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually write changes to eso.db.",
    )
    args = parser.parse_args()

    input_path = args.input.resolve()
    db_path = args.db.resolve()

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" UESP Alchemy Effects DB Importer")
    print("=" * 60)
    print()
    print("Input:", input_path)
    print("Database:", db_path)
    print("Mode:", "COMMIT" if args.commit else "DRY RUN")
    print()

    if not input_path.exists():
        print("ERROR: input JSON does not exist.")
        sys.exit(1)

    if not db_path.exists():
        print("ERROR: database does not exist.")
        sys.exit(1)

    effects = load_dataset(input_path)

    print(f"Source effects: {len(effects)}")
    print()

    # Sanity check the schema before touching anything.
    db = sqlite3.connect(db_path)

    try:
        required_tables = {"effect", "effect_variant", "effect_source"}
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        missing_tables = sorted(required_tables - tables)
        if missing_tables:
            raise RuntimeError(
                "Database is missing required tables: "
                + ", ".join(missing_tables)
            )

        if args.commit:
            backup = backup_database(db_path)
            print("Backup created:", backup)
            print()

        # One transaction for the whole import.
        db.execute("BEGIN")

        stats = import_effects(db, effects, commit=args.commit)

        if not args.commit:
            db.rollback()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("=" * 60)
    print(" UESP Alchemy Effects Import Complete")
    print("=" * 60)
    print()
    print(f"Source effects:        {len(effects):>5}")
    print(f"Effects created:       {stats['effects_created']:>5}")
    print(f"Effects existing:      {stats['effects_existing']:>5}")
    print()
    print(f"Variants created:      {stats['variants_created']:>5}")
    print(f"Variants existing:     {stats['variants_existing']:>5}")
    print(f"Potion variants:       {stats['potion_variants']:>5}")
    print(f"Poison variants:       {stats['poison_variants']:>5}")
    print()
    print(f"UESP sources added:    {stats['sources_added']:>5}")
    print(f"UESP sources existing: {stats['sources_existing']:>5}")
    print()

    if args.commit:
        print("STATUS: IMPORT COMPLETE")
    else:
        print("STATUS: DRY RUN - DATABASE UNCHANGED")
        print()
        print("Run with --commit when the numbers look correct.")


if __name__ == "__main__":
    main()
