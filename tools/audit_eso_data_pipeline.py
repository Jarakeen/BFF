from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


IMPORT_FILE_RE = re.compile(r'["\']([^"\']+\.json)["\']', re.IGNORECASE)


def json_shape(path: Path) -> tuple[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return "INVALID", str(exc)

    if isinstance(payload, dict):
        keys = ", ".join(list(payload.keys())[:8])
        return "object", keys
    if isinstance(payload, list):
        return "list", f"records={len(payload)}"
    return type(payload).__name__, str(payload)[:80]


def raw_inventory(raw_dir: Path) -> list[tuple[str, int, str, str]]:
    rows = []
    for path in sorted(raw_dir.glob("*.json")):
        kind, detail = json_shape(path)
        rows.append((path.name, path.stat().st_size, kind, detail))
    return rows


def importer_references(importers_dir: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for path in sorted(importers_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        refs = set(IMPORT_FILE_RE.findall(text))
        if refs:
            result[path.name] = refs
    return result


def tables(db: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]


def table_count(db: sqlite3.Connection, table: str) -> int:
    try:
        return int(db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    except sqlite3.Error:
        return -1


def print_fk_check(db: sqlite3.Connection, child: str, child_col: str, parent: str, parent_col: str) -> None:
    if child not in tables(db) or parent not in tables(db):
        return
    row = db.execute(
        f'''SELECT COUNT(*) FROM "{child}" c
            LEFT JOIN "{parent}" p ON c."{child_col}" = p."{parent_col}"
            WHERE c."{child_col}" IS NOT NULL AND p."{parent_col}" IS NULL'''
    ).fetchone()
    print(f"  orphan {child}.{child_col} -> {parent}.{parent_col}: {row[0]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit ESO raw-data/import/database completeness without changing data")
    parser.add_argument("--db", default="data/eso.db")
    parser.add_argument("--raw", default="data/raw")
    parser.add_argument("--importers", default="importers")
    args = parser.parse_args()

    raw_dir = Path(args.raw)
    importers_dir = Path(args.importers)
    db = sqlite3.connect(args.db)

    try:
        print("=== ESO DATA PIPELINE AUDIT ===")
        print(f"database={args.db}")
        print(f"raw_dir={args.raw}")
        print()

        print("=== RAW JSON INVENTORY ===")
        raw = raw_inventory(raw_dir) if raw_dir.exists() else []
        for name, size, kind, detail in raw:
            print(f"{name:45} {size:10} bytes  {kind:8}  {detail}")
        print(f"Raw JSON files: {len(raw)}")
        print()

        refs = importer_references(importers_dir) if importers_dir.exists() else {}
        referenced = set().union(*refs.values()) if refs else set()
        print("=== IMPORTER SOURCE REFERENCES ===")
        for importer, names in refs.items():
            print(f"{importer}")
            for name in sorted(names):
                print(f"  {name}")
        print()

        raw_names = {row[0] for row in raw}
        print("=== RAW FILES NOT REFERENCED BY ANY IMPORTER ===")
        unreferenced = sorted(raw_names - referenced)
        for name in unreferenced:
            print(f"  {name}")
        print(f"Count: {len(unreferenced)}")
        print()

        print("=== REFERENCED FILES MISSING FROM data/raw ===")
        missing = sorted(referenced - raw_names)
        for name in missing:
            print(f"  {name}")
        print(f"Count: {len(missing)}")
        print()

        print("=== DATABASE TABLE COUNTS ===")
        db_tables = tables(db)
        for table in db_tables:
            print(f"{table:35} {table_count(db, table):10}")
        print()

        print("=== KEY IDENTITY / RELATIONSHIP CHECKS ===")
        for table in ("entity", "entity_source", "effect", "effect_variant", "effect_source", "ability", "ability_effect_link", "combat_effect", "combat_effect_trigger", "combat_effect_interaction", "gear_set", "gear_set_bonus", "gear_set_item", "achievement", "achievement_category", "achievement_criterion", "content", "content_npc", "encounter", "encounter_npc", "encounter_ability", "log_report", "log_fight", "log_actor", "log_event"):
            if table in db_tables:
                print(f"  {table}: {table_count(db, table)}")

        print("\n=== CANONICAL EFFECT SPOT CHECKS ===")
        if "entity" in db_tables:
            rows = db.execute(
                "SELECT id, entity_type, name FROM entity WHERE id IN ('buff:major_force','debuff:major_breach') ORDER BY id"
            ).fetchall()
            for row in rows:
                print(f"  entity: {tuple(row)}")
        if "entity_source" in db_tables:
            for entity_id in ("buff:major_force", "debuff:major_breach"):
                rows = db.execute(
                    "SELECT source, source_entity_type, source_id, source_name FROM entity_source WHERE entity_id=? ORDER BY source, source_id",
                    (entity_id,),
                ).fetchall()
                print(f"  sources for {entity_id}: {len(rows)}")
                for row in rows[:20]:
                    print(f"    {tuple(row)}")

        print("\n=== FOREIGN-KEY ORPHAN CHECKS ===")
        checks = [
            ("entity_source", "entity_id", "entity", "id"),
            ("effect_variant", "effect_id", "effect", "id"),
            ("effect_source", "effect_variant_id", "effect_variant", "id"),
            ("ability_effect_link", "effect_variant_id", "effect_variant", "id"),
            ("ability_effect_link", "effect_source_id", "effect_source", "id"),
            ("ability_effect_link", "ability_id", "ability", "ability_id"),
            ("ability_combat_effect", "ability_id", "ability", "ability_id"),
            ("ability_combat_effect", "combat_effect_id", "combat_effect", "id"),
            ("combat_effect_trigger", "combat_effect_id", "combat_effect", "id"),
            ("combat_effect_interaction", "combat_effect_id", "combat_effect", "id"),
            ("gear_set_bonus", "set_id", "gear_set", "id"),
            ("gear_set_item", "set_id", "gear_set", "id"),
            ("log_fight", "report_code", "log_report", "report_code"),
            ("log_actor", "report_code", "log_report", "report_code"),
            ("log_event", "report_code", "log_report", "report_code"),
            ("log_event", "fight_id", "log_fight", "fight_id"),
        ]
        for check in checks:
            try:
                print_fk_check(db, *check)
            except sqlite3.Error as exc:
                print(f"  CHECK ERROR {check}: {exc}")

        print("\n=== AUDIT COMPLETE ===")
        print("This audit is read-only. It does not modify the database or raw files.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
