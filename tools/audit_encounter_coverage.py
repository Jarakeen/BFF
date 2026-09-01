from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


MEANINGFUL_DESCRIPTION_LENGTH = 40


def table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def table_columns(db: sqlite3.Connection, table: str) -> set[str]:
    if not table_exists(db, table):
        return set()
    return {str(row[1]) for row in db.execute(f'PRAGMA table_info("{table}")')}


def scalar(db: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
    row = db.execute(sql, params).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def percent(part: int, whole: int) -> str:
    if whole <= 0:
        return "n/a"
    return f"{(part / whole) * 100:.1f}%"


def print_metric(label: str, value: int, total: int | None = None) -> None:
    if total is None:
        print(f"  {label:<42} {value:>7}")
    else:
        print(f"  {label:<42} {value:>7} / {total:<7} ({percent(value, total)})")


def load_raw_bosses(raw_dir: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    records: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    if not raw_dir.exists():
        return records, errors

    for path in sorted(raw_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{path.name}: root is {type(payload).__name__}, expected object")
            continue
        boss_id = str(payload.get("id") or path.stem).strip()
        if not boss_id:
            errors.append(f"{path.name}: missing boss id")
            continue
        records[boss_id] = payload
    return records, errors


def count_nonempty_strings(items: list[dict[str, Any]], key: str) -> int:
    return sum(1 for item in items if str(item.get(key) or "").strip())


def audit_raw(raw_dir: Path) -> dict[str, Any]:
    bosses, errors = load_raw_bosses(raw_dir)
    total_abilities = 0
    meaningful_abilities = 0
    bosses_with_abilities = 0
    total_mechanics = 0
    bosses_with_mechanics = 0
    total_phases = 0
    bosses_with_phases = 0
    total_dialogue = 0
    bosses_with_dialogue = 0
    hardmode_health = 0
    normal_health = 0
    veteran_health = 0
    hardmode_notes = 0
    normal_vet_notes = 0
    bosses_with_source = 0
    bosses_with_summary = 0
    bosses_with_content_id = 0

    for payload in bosses.values():
        abilities = payload.get("abilities") or []
        if isinstance(abilities, list):
            if abilities:
                bosses_with_abilities += 1
            total_abilities += len(abilities)
            meaningful_abilities += sum(
                1
                for item in abilities
                if isinstance(item, dict)
                and len(str(item.get("description") or "").strip()) >= MEANINGFUL_DESCRIPTION_LENGTH
            )

        mechanics = payload.get("mechanics") or []
        if isinstance(mechanics, list):
            if mechanics:
                bosses_with_mechanics += 1
            total_mechanics += len(mechanics)

        phases = payload.get("phases") or []
        if isinstance(phases, list):
            if phases:
                bosses_with_phases += 1
            total_phases += len(phases)

        dialogue = payload.get("dialogue") or []
        if isinstance(dialogue, list):
            if dialogue:
                bosses_with_dialogue += 1
            total_dialogue += len(dialogue)

        health = payload.get("health") or {}
        if isinstance(health, dict):
            normal_health += bool(str(health.get("normal") or "").strip())
            veteran_health += bool(str(health.get("veteran") or "").strip())
            hardmode_health += bool(str(health.get("hardmode") or "").strip())

        difficulty = payload.get("difficulty_notes") or {}
        if isinstance(difficulty, dict):
            nv = difficulty.get("normal_veteran_differences") or []
            hm = difficulty.get("hardmode_info") or []
            if isinstance(nv, list):
                normal_vet_notes += len(nv)
            if isinstance(hm, list):
                hardmode_notes += len(hm)

        source = payload.get("source") or {}
        if isinstance(source, dict) and str(source.get("url") or "").strip():
            bosses_with_source += 1
        bosses_with_summary += bool(str(payload.get("summary") or "").strip())
        bosses_with_content_id += bool(str(payload.get("content_id") or "").strip())

    return {
        "bosses": bosses,
        "errors": errors,
        "boss_count": len(bosses),
        "bosses_with_content_id": bosses_with_content_id,
        "bosses_with_summary": bosses_with_summary,
        "bosses_with_source": bosses_with_source,
        "bosses_with_abilities": bosses_with_abilities,
        "ability_count": total_abilities,
        "meaningful_abilities": meaningful_abilities,
        "bosses_with_mechanics": bosses_with_mechanics,
        "mechanic_count": total_mechanics,
        "bosses_with_phases": bosses_with_phases,
        "phase_count": total_phases,
        "bosses_with_dialogue": bosses_with_dialogue,
        "dialogue_count": total_dialogue,
        "normal_health": normal_health,
        "veteran_health": veteran_health,
        "hardmode_health": hardmode_health,
        "normal_vet_notes": normal_vet_notes,
        "hardmode_notes": hardmode_notes,
    }


def audit_legacy(db: sqlite3.Connection) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if not table_exists(db, "bosses"):
        return result

    total = scalar(db, "SELECT COUNT(*) FROM bosses")
    result["boss_count"] = total
    result["boss_ids"] = {str(row[0]) for row in db.execute("SELECT id FROM bosses")}

    boss_cols = table_columns(db, "bosses")
    for key, column in (
        ("with_content_id", "content_id"),
        ("with_summary", "summary"),
        ("with_source", "source_url"),
        ("normal_health", "health_normal"),
        ("veteran_health", "health_veteran"),
        ("hardmode_health", "health_hardmode"),
    ):
        if column in boss_cols:
            result[key] = scalar(
                db,
                f'SELECT COUNT(*) FROM bosses WHERE TRIM(COALESCE("{column}", "")) <> ""',
            )

    if table_exists(db, "boss_abilities"):
        result["ability_count"] = scalar(db, "SELECT COUNT(*) FROM boss_abilities")
        result["bosses_with_abilities"] = scalar(
            db, "SELECT COUNT(DISTINCT boss_id) FROM boss_abilities"
        )
        ability_cols = table_columns(db, "boss_abilities")
        if "description" in ability_cols:
            result["abilities_with_description"] = scalar(
                db,
                "SELECT COUNT(*) FROM boss_abilities WHERE TRIM(COALESCE(description, '')) <> ''",
            )
            result["meaningful_abilities"] = scalar(
                db,
                "SELECT COUNT(*) FROM boss_abilities WHERE LENGTH(TRIM(COALESCE(description, ''))) >= ?",
                (MEANINGFUL_DESCRIPTION_LENGTH,),
            )

    child_tables = {
        "phase_count": "boss_phases",
        "dialogue_count": "boss_dialogue",
        "note_count": "boss_notes",
        "related_npc_count": "boss_related_npcs",
        "related_quest_count": "boss_related_quests",
        "achievement_count": "boss_achievements",
    }
    for key, table in child_tables.items():
        if table_exists(db, table):
            result[key] = scalar(db, f'SELECT COUNT(*) FROM "{table}"')
            result[f"bosses_with_{key.removesuffix('_count')}"] = scalar(
                db, f'SELECT COUNT(DISTINCT boss_id) FROM "{table}"'
            )

    if table_exists(db, "boss_difficulty_notes"):
        result["difficulty_note_count"] = scalar(db, "SELECT COUNT(*) FROM boss_difficulty_notes")
        rows = db.execute(
            "SELECT category, COUNT(*) FROM boss_difficulty_notes GROUP BY category ORDER BY category"
        ).fetchall()
        result["difficulty_categories"] = {str(row[0]): int(row[1]) for row in rows}
        result["bosses_with_difficulty_notes"] = scalar(
            db, "SELECT COUNT(DISTINCT boss_id) FROM boss_difficulty_notes"
        )

    if table_exists(db, "content"):
        content_cols = table_columns(db, "content")
        if "content_type" in content_cols:
            rows = db.execute(
                "SELECT content_type, COUNT(*) FROM content GROUP BY content_type ORDER BY content_type"
            ).fetchall()
            result["content_by_type"] = {str(row[0]): int(row[1]) for row in rows}
            result["content_count"] = sum(result["content_by_type"].values())

    if table_exists(db, "content_bosses"):
        result["content_boss_links"] = scalar(db, "SELECT COUNT(*) FROM content_bosses")
        result["linked_bosses"] = scalar(db, "SELECT COUNT(DISTINCT boss_id) FROM content_bosses")
        result["linked_content"] = scalar(db, "SELECT COUNT(DISTINCT content_id) FROM content_bosses")
        result["orphan_boss_links"] = scalar(
            db,
            """SELECT COUNT(*) FROM content_bosses cb
               LEFT JOIN bosses b ON b.id = cb.boss_id
               WHERE b.id IS NULL""",
        )
        if table_exists(db, "content"):
            result["orphan_content_links"] = scalar(
                db,
                """SELECT COUNT(*) FROM content_bosses cb
                   LEFT JOIN content c ON c.id = cb.content_id
                   WHERE c.id IS NULL""",
            )
            result["content_without_bosses"] = scalar(
                db,
                """SELECT COUNT(*) FROM content c
                   LEFT JOIN content_bosses cb ON cb.content_id = c.id
                   WHERE cb.content_id IS NULL""",
            )

    return result


def audit_canonical(db: sqlite3.Connection) -> dict[str, Any]:
    if not table_exists(db, "encounter"):
        return {}

    result: dict[str, Any] = {
        "encounter_count": scalar(db, "SELECT COUNT(*) FROM encounter"),
    }
    encounter_cols = table_columns(db, "encounter")
    for key, column in (
        ("with_summary", "summary"),
        ("with_source", "source_url"),
    ):
        if column in encounter_cols:
            result[key] = scalar(
                db,
                f'SELECT COUNT(*) FROM encounter WHERE TRIM(COALESCE("{column}", "")) <> ""',
            )

    for key, table in (
        ("ability_count", "encounter_ability"),
        ("mechanic_count", "encounter_mechanic"),
        ("phase_count", "encounter_phase"),
        ("dialogue_count", "encounter_dialogue"),
        ("strategy_count", "encounter_strategy"),
    ):
        if table_exists(db, table):
            result[key] = scalar(db, f'SELECT COUNT(*) FROM "{table}"')
            result[f"encounters_with_{key.removesuffix('_count')}"] = scalar(
                db, f'SELECT COUNT(DISTINCT encounter_id) FROM "{table}"'
            )

    if table_exists(db, "encounter_mechanic"):
        cols = table_columns(db, "encounter_mechanic")
        if "interpretation_status" in cols:
            rows = db.execute(
                "SELECT interpretation_status, COUNT(*) FROM encounter_mechanic GROUP BY interpretation_status ORDER BY interpretation_status"
            ).fetchall()
            result["mechanic_status"] = {str(row[0]): int(row[1]) for row in rows}

    if table_exists(db, "encounter_health"):
        cols = table_columns(db, "encounter_health")
        for key, column in (
            ("normal_health", "normal"),
            ("veteran_health", "veteran"),
            ("hardmode_health", "hardmode"),
        ):
            if column in cols:
                result[key] = scalar(
                    db,
                    f'SELECT COUNT(*) FROM encounter_health WHERE TRIM(COALESCE("{column}", "")) <> ""',
                )

    return result


def print_raw(raw: dict[str, Any], raw_dir: Path) -> None:
    print("=== RAW UESP BOSS JSON ===")
    print(f"  directory: {raw_dir}")
    total = raw["boss_count"]
    print_metric("boss JSON records", total)
    print_metric("bosses with content_id", raw["bosses_with_content_id"], total)
    print_metric("bosses with summary", raw["bosses_with_summary"], total)
    print_metric("bosses with source URL", raw["bosses_with_source"], total)
    print_metric("bosses with abilities", raw["bosses_with_abilities"], total)
    print_metric("ability rows", raw["ability_count"])
    print_metric(
        f"ability descriptions >= {MEANINGFUL_DESCRIPTION_LENGTH} chars",
        raw["meaningful_abilities"],
        raw["ability_count"],
    )
    print_metric("bosses with structured mechanics", raw["bosses_with_mechanics"], total)
    print_metric("structured mechanic rows", raw["mechanic_count"])
    print_metric("bosses with structured phases", raw["bosses_with_phases"], total)
    print_metric("structured phase rows", raw["phase_count"])
    print_metric("bosses with dialogue", raw["bosses_with_dialogue"], total)
    print_metric("dialogue rows", raw["dialogue_count"])
    print_metric("normal health present", raw["normal_health"], total)
    print_metric("veteran health present", raw["veteran_health"], total)
    print_metric("hardmode health present", raw["hardmode_health"], total)
    print_metric("normal/veteran difficulty notes", raw["normal_vet_notes"])
    print_metric("hardmode difficulty notes", raw["hardmode_notes"])
    if raw["errors"]:
        print(f"  JSON read errors: {len(raw['errors'])}")
        for error in raw["errors"][:20]:
            print(f"    - {error}")
    print()


def print_legacy(legacy: dict[str, Any]) -> None:
    print("=== LEGACY ESO.DB ENCOUNTER IMPORT ===")
    if not legacy:
        print("  bosses table not present")
        print()
        return

    total = legacy["boss_count"]
    if legacy.get("content_by_type"):
        print("  content by type:")
        for content_type, count in legacy["content_by_type"].items():
            print(f"    {content_type:<16} {count:>7}")
    print_metric("boss rows", total)
    for key, label in (
        ("with_content_id", "bosses with content_id"),
        ("with_summary", "bosses with summary"),
        ("with_source", "bosses with source URL"),
        ("normal_health", "normal health present"),
        ("veteran_health", "veteran health present"),
        ("hardmode_health", "hardmode health present"),
        ("bosses_with_abilities", "bosses with abilities"),
    ):
        if key in legacy:
            print_metric(label, legacy[key], total)

    if "ability_count" in legacy:
        print_metric("ability rows", legacy["ability_count"])
        if "abilities_with_description" in legacy:
            print_metric(
                "abilities with non-empty description",
                legacy["abilities_with_description"],
                legacy["ability_count"],
            )
        if "meaningful_abilities" in legacy:
            print_metric(
                f"ability descriptions >= {MEANINGFUL_DESCRIPTION_LENGTH} chars",
                legacy["meaningful_abilities"],
                legacy["ability_count"],
            )

    for key, label in (
        ("phase_count", "phase rows"),
        ("dialogue_count", "dialogue rows"),
        ("note_count", "boss note rows"),
        ("related_npc_count", "related NPC rows"),
        ("related_quest_count", "related quest rows"),
        ("achievement_count", "boss achievement rows"),
        ("difficulty_note_count", "difficulty note rows"),
        ("content_boss_links", "content-boss links"),
        ("linked_bosses", "distinct bosses linked to content"),
        ("linked_content", "distinct content with boss links"),
        ("content_without_bosses", "content records without boss links"),
        ("orphan_boss_links", "orphan links to missing boss"),
        ("orphan_content_links", "orphan links to missing content"),
    ):
        if key in legacy:
            print_metric(label, legacy[key])

    if legacy.get("difficulty_categories"):
        print("  difficulty notes by category:")
        for category, count in legacy["difficulty_categories"].items():
            print(f"    {category:<24} {count:>7}")
    print()


def print_canonical(canonical: dict[str, Any]) -> None:
    print("=== CANONICAL ENCOUNTER KNOWLEDGE LAYER ===")
    if not canonical:
        print("  encounter table not present")
        print()
        return

    total = canonical["encounter_count"]
    print_metric("encounter rows", total)
    for key, label in (
        ("with_summary", "encounters with summary"),
        ("with_source", "encounters with source URL"),
        ("normal_health", "normal health present"),
        ("veteran_health", "veteran health present"),
        ("hardmode_health", "hardmode health present"),
    ):
        if key in canonical:
            print_metric(label, canonical[key], total)

    for key, label in (
        ("ability_count", "encounter ability rows"),
        ("mechanic_count", "structured mechanic rows"),
        ("phase_count", "structured phase rows"),
        ("dialogue_count", "encounter dialogue rows"),
        ("strategy_count", "strategy rows"),
    ):
        if key in canonical:
            print_metric(label, canonical[key])

    if canonical.get("mechanic_status"):
        print("  mechanic interpretation status:")
        for status, count in canonical["mechanic_status"].items():
            print(f"    {status:<24} {count:>7}")
    print()


def print_comparison(raw: dict[str, Any], legacy: dict[str, Any], canonical: dict[str, Any]) -> None:
    print("=== CROSS-LAYER FINDINGS ===")
    raw_ids = set(raw["bosses"])
    legacy_ids = set(legacy.get("boss_ids", set()))
    if raw_ids and legacy_ids:
        missing = sorted(raw_ids - legacy_ids)
        db_only = sorted(legacy_ids - raw_ids)
        print_metric("raw boss IDs missing from legacy DB", len(missing), len(raw_ids))
        if missing:
            print("    first missing IDs: " + ", ".join(missing[:20]))
        print_metric("legacy DB boss IDs absent from raw JSON", len(db_only), len(legacy_ids))
        if db_only:
            print("    first DB-only IDs: " + ", ".join(db_only[:20]))

    raw_phase_count = int(raw.get("phase_count", 0))
    legacy_phase_count = int(legacy.get("phase_count", 0))
    canonical_phase_count = int(canonical.get("phase_count", 0))
    if raw_phase_count == 0:
        print("  PHASE PIPELINE: raw boss JSON contains 0 structured phases.")
        print("                  The legacy DB cannot import phase rows that Stage 1 never produced.")
    elif legacy and legacy_phase_count == 0:
        print("  PHASE PIPELINE: raw JSON has phases, but the legacy DB has 0. Import loss detected.")
    else:
        print(f"  PHASE PIPELINE: raw={raw_phase_count}, legacy={legacy_phase_count}, canonical={canonical_phase_count}")

    raw_mechanics = int(raw.get("mechanic_count", 0))
    canonical_mechanics = int(canonical.get("mechanic_count", 0))
    if raw_mechanics == 0:
        print("  MECHANIC PIPELINE: raw boss JSON contains 0 structured mechanics.")
        print("                     Ability prose exists, but mechanic classification was not materialized there.")
    elif canonical and canonical_mechanics == 0:
        print("  MECHANIC PIPELINE: raw JSON has mechanics, but canonical encounter_mechanic has 0.")

    if canonical:
        print("  CANONICAL LAYER: encounter tables are present and contain data; see counts above.")
    else:
        print("  CANONICAL LAYER: encounter tables are absent from this database.")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only audit of UESP boss JSON, legacy boss imports, and the canonical encounter layer."
    )
    parser.add_argument("--db", default="data/eso.db", help="SQLite database to audit")
    parser.add_argument(
        "--raw-bosses",
        default="data/uesp/bosses",
        help="Directory containing Stage 1 UESP boss JSON",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    raw_dir = Path(args.raw_bosses)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    raw = audit_raw(raw_dir)
    db = sqlite3.connect(db_path)
    try:
        legacy = audit_legacy(db)
        canonical = audit_canonical(db)
    finally:
        db.close()

    print("=" * 64)
    print(" ENCOUNTER DATA COVERAGE AUDIT")
    print("=" * 64)
    print(f"database:   {db_path}")
    print(f"raw bosses: {raw_dir}")
    print(f"meaningful ability threshold: {MEANINGFUL_DESCRIPTION_LENGTH} characters")
    print()

    print_raw(raw, raw_dir)
    print_legacy(legacy)
    print_canonical(canonical)
    print_comparison(raw, legacy, canonical)

    print("=== AUDIT COMPLETE ===")
    print("Read-only: no database rows or JSON files were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
