from __future__ import annotations

"""Read-only recovery queue for encounter data already collected by FoundryDock.

The broad UESP crawl contains many creature/location pages that are not part of
our imported group-content catalog. This audit deliberately anchors itself to
`eso.db` content rows, then asks what useful encounter records are missing or
thin for those imported trials, dungeons, and arenas.

Nothing is written to the database or source JSON.
"""

import argparse
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable


TRANSITION_CUE_RE = re.compile(
    r"(?i)\b(?:"
    r"disappears?|vanishes?|teleports?|"
    r"becomes?\s+(?:untargetable|invulnerable|immune)|"
    r"returns?\s+to\s+the\s+fight|reappears?|"
    r"transforms?|changes?\s+form|"
    r"enters?\s+(?:a|the|its)?\s*(?:new|next|final)?\s*phase|"
    r"begins?\s+(?:a|the)?\s*(?:new|next|final)?\s*phase|"
    r"starts?\s+(?:a|the)?\s*(?:new|next|final)?\s*phase"
    r")\b"
)
EXPLICIT_PHASE_RE = re.compile(
    r"(?i)\b(?:phase\s+(?:\d+|[ivx]+)|final\s+phase|intermission)\b"
)
ACTIONABLE_RE = re.compile(
    r"(?i)\b(?:"
    r"block(?:ed|ing)?|dodge(?:d|roll)?|interrupt(?:ed|ible|ing)?|"
    r"cleanse(?:d|s)?|purge(?:d|s)?|spread|stack|"
    r"knock(?:s|ed|ing)?\s*back|knockdown|knocks?\s+down|stun(?:s|ned|ning)?|"
    r"snare(?:s|d)?|fear(?:s|ed)?|"
    r"safe\s+(?:area|zone|circle|spot)|"
    r"move\s+(?:out|away|through)|run\s+(?:out|away|through)|avoid|"
    r"portal|summons?|spawns?|adds?|"
    r"invulnerable|untargetable|immune|"
    r"one[- ]shot|fatal|kills?\s+(?:a|the|all)?\s*players?"
    r")\b"
)

# Handles both "75%, 50%, 25%" and shorthand "80, 60, 40 and 20%".
PERCENT_LIST_RE = re.compile(
    r"(?i)(?<![\d,])"
    r"(\d{1,3}(?:\s*%?\s*(?:,|/|\band\b|&)\s*\d{1,3})+)\s*%"
)
SINGLE_PERCENT_RE = re.compile(r"(?i)(?<![\d,])(\d{1,3})\s*%")
DECIMAL_PERCENT_RE = re.compile(r"\b\d+\s*,\s*\d+\s*%")


def clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def ability_rows(record: dict[str, Any]) -> Iterable[tuple[str, str]]:
    rows = record.get("abilities")
    if not isinstance(rows, list):
        return
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        name = clean(row.get("name")) or f"Ability {index}"
        description = clean(row.get("description"))
        if description:
            yield name, description


def extract_thresholds(text: str) -> list[int]:
    """Extract health-like percentage lists without treating 0,2% as 2%."""
    scrubbed = DECIMAL_PERCENT_RE.sub("", text)
    found: list[int] = []
    consumed: list[tuple[int, int]] = []

    for match in PERCENT_LIST_RE.finditer(scrubbed):
        values = [int(v) for v in re.findall(r"\d{1,3}", match.group(1))]
        for value in values:
            if 0 < value <= 100 and value not in found:
                found.append(value)
        consumed.append(match.span())

    def inside_consumed(start: int, end: int) -> bool:
        return any(start >= a and end <= b for a, b in consumed)

    for match in SINGLE_PERCENT_RE.finditer(scrubbed):
        if inside_consumed(*match.span()):
            continue
        value = int(match.group(1))
        if 0 < value <= 100 and value not in found:
            found.append(value)

    return found


def transition_rows(record: dict[str, Any]) -> list[tuple[str, list[int], str]]:
    result: list[tuple[str, list[int], str]] = []
    for name, text in ability_rows(record):
        thresholds = extract_thresholds(text)
        if not thresholds:
            continue
        if not (TRANSITION_CUE_RE.search(text) or EXPLICIT_PHASE_RE.search(text)):
            continue
        result.append((name, thresholds, text))
    return result


def has_actionable_ability(record: dict[str, Any]) -> bool:
    return any(ACTIONABLE_RE.search(text) for _, text in ability_rows(record))


def clip(text: str, width: int = 160) -> str:
    text = clean(text)
    return text if len(text) <= width else text[: width - 3].rstrip() + "..."


def table_exists(db: sqlite3.Connection, name: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a DB-anchored, read-only recovery queue for encounter enrichment"
    )
    parser.add_argument("--db", default="data/eso.db")
    parser.add_argument("--boss-dir", default="data/uesp/bosses")
    parser.add_argument("--uesp-root", default="data/uesp")
    parser.add_argument("--limit", type=int, default=60, help="Rows per detail section; 0 means all")
    args = parser.parse_args()

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    try:
        required = {"content", "bosses", "content_bosses"}
        missing_tables = sorted(name for name in required if not table_exists(db, name))
        if missing_tables:
            raise SystemExit(f"Missing required legacy encounter tables: {', '.join(missing_tables)}")

        content_rows = db.execute(
            "SELECT id, name, content_type FROM content ORDER BY content_type, name"
        ).fetchall()
        imported_content = {str(r["id"]): dict(r) for r in content_rows}

        db_boss_rows = db.execute(
            "SELECT id, name, content_id FROM bosses ORDER BY name"
        ).fetchall()
        db_bosses = {str(r["id"]): dict(r) for r in db_boss_rows}

        links = db.execute(
            "SELECT content_id, boss_id FROM content_bosses ORDER BY content_id, position"
        ).fetchall()
        links_by_content: dict[str, list[str]] = {}
        for row in links:
            links_by_content.setdefault(str(row["content_id"]), []).append(str(row["boss_id"]))

        raw_records: dict[str, dict[str, Any]] = {}
        raw_paths: dict[str, Path] = {}
        for path in sorted(Path(args.boss_dir).glob("*.json")):
            record = load_json(path)
            if not record:
                continue
            boss_id = clean(record.get("id")) or path.stem
            raw_records[boss_id] = record
            raw_paths[boss_id] = path

        relevant_raw: list[tuple[str, dict[str, Any]]] = []
        for boss_id, record in raw_records.items():
            content_id = clean(record.get("content_id"))
            if content_id in imported_content:
                relevant_raw.append((boss_id, record))

        missing_from_db: list[tuple[str, str, str, str]] = []
        no_abilities: list[tuple[str, str, str, str]] = []
        no_actionable: list[tuple[str, str, str, str, int]] = []
        transition_candidates: list[tuple[str, str, str, list[tuple[str, list[int], str]]]] = []

        for boss_id, record in sorted(relevant_raw, key=lambda item: clean(item[1].get("name")).casefold()):
            name = clean(record.get("name")) or boss_id
            content_id = clean(record.get("content_id"))
            content_name = imported_content[content_id]["name"]
            abilities = list(ability_rows(record))

            if boss_id not in db_bosses:
                missing_from_db.append((content_name, name, boss_id, content_id))
            if not abilities:
                no_abilities.append((content_name, name, boss_id, content_id))
            elif not has_actionable_ability(record):
                no_actionable.append((content_name, name, boss_id, content_id, len(abilities)))

            transitions = transition_rows(record)
            if transitions:
                transition_candidates.append((content_name, name, boss_id, transitions))

        # Raw content relationship status for the same 79 imported content ids only.
        raw_content_by_id: dict[str, dict[str, Any]] = {}
        root = Path(args.uesp_root)
        for folder in ("trials", "dungeons", "arenas"):
            for path in (root / folder).glob("*.json"):
                record = load_json(path)
                if not record:
                    continue
                content_id = clean(record.get("id")) or path.stem
                if content_id in imported_content:
                    raw_content_by_id[content_id] = record

        imported_empty_raw_boss_ids: list[tuple[str, str, int]] = []
        imported_missing_raw_content: list[tuple[str, str]] = []
        for content_id, row in imported_content.items():
            record = raw_content_by_id.get(content_id)
            if record is None:
                imported_missing_raw_content.append((row["name"], content_id))
                continue
            raw_boss_ids = record.get("boss_ids")
            if not isinstance(raw_boss_ids, list) or not raw_boss_ids:
                imported_empty_raw_boss_ids.append(
                    (row["name"], content_id, len(links_by_content.get(content_id, [])))
                )

        db_linked_boss_missing_raw: list[tuple[str, str, str]] = []
        for content_id, boss_ids in links_by_content.items():
            content_name = imported_content.get(content_id, {}).get("name", content_id)
            for boss_id in boss_ids:
                if boss_id not in raw_records:
                    db_name = db_bosses.get(boss_id, {}).get("name", boss_id)
                    db_linked_boss_missing_raw.append((content_name, str(db_name), boss_id))

        print("=" * 76)
        print(" ENCOUNTER RECOVERY QUEUE - DB ANCHORED / READ ONLY")
        print("=" * 76)
        print(f"imported content records:                    {len(imported_content):6}")
        by_type: dict[str, int] = {}
        for row in imported_content.values():
            by_type[str(row['content_type'])] = by_type.get(str(row['content_type']), 0) + 1
        for kind in sorted(by_type):
            print(f"  {kind:12} {by_type[kind]:6}")
        print(f"legacy DB bosses:                            {len(db_bosses):6}")
        print(f"raw boss JSON records:                       {len(raw_records):6}")
        print(f"raw bosses tied to imported content:         {len(relevant_raw):6}")
        print(f"relevant raw bosses missing from DB:         {len(missing_from_db):6}")
        print(f"relevant raw bosses with no abilities:       {len(no_abilities):6}")
        print(f"relevant bosses with abilities/no cues:      {len(no_actionable):6}")
        print(f"relevant bosses with transition evidence:    {len(transition_candidates):6}")
        print(f"DB-linked bosses missing raw boss JSON:      {len(db_linked_boss_missing_raw):6}")
        print(f"imported content with empty raw boss_ids:     {len(imported_empty_raw_boss_ids):6}")
        print(f"imported content lacking matching raw JSON:   {len(imported_missing_raw_content):6}")
        print()

        limit = None if args.limit == 0 else max(args.limit, 0)

        def limited(rows):
            return rows if limit is None else rows[:limit]

        print("=== PRIORITY A: RELEVANT RAW BOSSES MISSING FROM LEGACY DB ===")
        for content_name, name, boss_id, _ in limited(missing_from_db):
            print(f"  {content_name} | {name} [{boss_id}]")
        if limit is not None and len(missing_from_db) > limit:
            print(f"  ... {len(missing_from_db) - limit} more")
        print()

        print("=== PRIORITY B: RELEVANT BOSSES WITH NO ABILITY DATA ===")
        for content_name, name, boss_id, _ in limited(no_abilities):
            in_db = "DB" if boss_id in db_bosses else "RAW-ONLY"
            print(f"  {content_name} | {name} [{boss_id}] | {in_db}")
        if limit is not None and len(no_abilities) > limit:
            print(f"  ... {len(no_abilities) - limit} more")
        print()

        print("=== RECOVERABLE LOCALLY: THRESHOLD / TRANSITION EVIDENCE ===")
        for content_name, name, boss_id, rows in limited(transition_candidates):
            print(f"  {content_name} | {name} [{boss_id}]")
            for ability, thresholds, evidence in rows:
                values = ", ".join(f"{v}%" for v in thresholds)
                print(f"    {ability}: {values}")
                print(f"      {clip(evidence)}")
        if limit is not None and len(transition_candidates) > limit:
            print(f"  ... {len(transition_candidates) - limit} more bosses")
        print()

        print("=== DB-LINKED BOSSES WITH NO CURRENT RAW BOSS JSON ===")
        for content_name, name, boss_id in limited(db_linked_boss_missing_raw):
            print(f"  {content_name} | {name} [{boss_id}]")
        if limit is not None and len(db_linked_boss_missing_raw) > limit:
            print(f"  ... {len(db_linked_boss_missing_raw) - limit} more")
        print()

        print("=== IMPORTED CONTENT WHOSE RAW boss_ids ARE EMPTY ===")
        for name, content_id, linked_count in limited(imported_empty_raw_boss_ids):
            print(f"  {name} [{content_id}] | DB content_boss links={linked_count}")
        if limit is not None and len(imported_empty_raw_boss_ids) > limit:
            print(f"  ... {len(imported_empty_raw_boss_ids) - limit} more")
        print()

        print("Interpretation:")
        print("  A = likely import/reconciliation work before recrawling")
        print("  B = strongest targeted source-recovery/recrawl candidates")
        print("  transition evidence = enrich locally first; do not promote automatically")
        print("  empty raw boss_ids with DB links = Stage-1 relationship discovery gap, not necessarily missing bosses")
        print()
        print("No database rows or source JSON files were changed.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
