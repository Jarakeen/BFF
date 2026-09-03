from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from services.paths import PROCESSED, RAW_DATA
from tools.import_uesp_alchemy_effects_v3 import EXPECTED_EFFECTS

DEFAULT_PROCESSED = PROCESSED / "alchemy_effects.json"
DEFAULT_RAW = RAW_DATA
LEGACY_PROCESSED = get_data_dir() / "processed" / "alchemy_effects.json"
LEGACY_RAW = get_data_dir() / "raw"

LEGACY_SPELL_POWER_COMPONENTS = (
    "Restore Magicka",
    "Increase Spell Power",
    "Spell Critical",
)
U51_POWER_COMPONENTS = (
    "Restore Magicka",
    "Increase Power",
    "Critical",
)


def _processed_inventory(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = payload.get("effects") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("effect_name") or row.get("name") or "").strip()
        if name:
            result[name.casefold()] = row
    return result


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def _db_effect_status(db: sqlite3.Connection, name: str) -> tuple[int, int, int]:
    if not _table_exists(db, "effect"):
        return (0, 0, 0)
    row = db.execute(
        "SELECT id FROM effect WHERE lower(trim(name)) = lower(trim(?)) ORDER BY id LIMIT 1",
        (name,),
    ).fetchone()
    if row is None:
        return (0, 0, 0)
    effect_id = int(row[0])
    if not _table_exists(db, "effect_variant"):
        return (1, 0, 0)
    variant_rows = db.execute(
        """
        SELECT id
        FROM effect_variant
        WHERE effect_id = ?
          AND lower(trim(COALESCE(type, ''))) = 'potion'
        """,
        (effect_id,),
    ).fetchall()
    variant_ids = [int(item[0]) for item in variant_rows]
    if not variant_ids or not _table_exists(db, "effect_source"):
        return (1, len(variant_ids), 0)
    placeholders = ",".join("?" for _ in variant_ids)
    source_count = int(
        db.execute(
            f"SELECT COUNT(*) FROM effect_source WHERE effect_variant_id IN ({placeholders})",
            variant_ids,
        ).fetchone()[0]
    )
    return (1, len(variant_ids), source_count)


def _likely_raw_files(raw_dir: Path, name: str) -> tuple[str, ...]:
    if not raw_dir.exists():
        return ()
    tokens = tuple(part for part in name.casefold().replace("-", " ").split() if part)
    matches: list[str] = []
    for path in raw_dir.rglob("*"):
        if not path.is_file():
            continue
        filename = path.name.casefold().replace("_", " ").replace("-", " ")
        if all(token in filename for token in tokens):
            matches.append(str(path.relative_to(raw_dir)))
    return tuple(sorted(matches, key=str.casefold))


def _unique_paths(*paths: Path) -> tuple[Path, ...]:
    output: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve()).casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(path)
    return tuple(output)


def audit(*, database_path: Path, processed_path: Path, raw_dir: Path) -> int:
    processed_candidates = _unique_paths(processed_path, DEFAULT_PROCESSED, LEGACY_PROCESSED)
    raw_candidates = _unique_paths(raw_dir, DEFAULT_RAW, LEGACY_RAW)

    print("========================================")
    print(" PHASE 5 POTION SOURCE RECOVERY AUDIT")
    print("========================================")
    print(f"Database: {database_path}")
    print()

    print("Source path candidates (migration-aware):")
    for path in processed_candidates:
        print(f"  processed: {'PRESENT' if path.exists() else 'missing'} | {path}")
    for path in raw_candidates:
        print(f"  raw:       {'PRESENT' if path.exists() else 'missing'} | {path}")
    print()

    print("Saved legacy shorthand: spell power")
    print("Legacy/U50 component evidence expected:")
    for name in LEGACY_SPELL_POWER_COMPONENTS:
        marker = "yes" if name in EXPECTED_EFFECTS else "NO"
        print(f"  - {name} | V3 EXPECTED_EFFECTS={marker}")
    print()
    print("U51 compatibility names to recognize when the active source corpus changes:")
    for name in U51_POWER_COMPONENTS:
        marker = "yes" if name in EXPECTED_EFFECTS else "no"
        print(f"  - {name} | V3 EXPECTED_EFFECTS={marker}")

    print()
    print("Processed source inventories:")
    for candidate in processed_candidates:
        processed = _processed_inventory(candidate)
        print(f"  {candidate}")
        if not candidate.exists():
            print("    processed alchemy JSON: MISSING")
        elif not processed:
            print("    processed alchemy JSON: present but unreadable/empty")
        else:
            print(f"    processed alchemy JSON: present | effects={len(processed)}")
        for name in tuple(dict.fromkeys(LEGACY_SPELL_POWER_COMPONENTS + U51_POWER_COMPONENTS)):
            row = processed.get(name.casefold())
            if row is None:
                print(f"    - {name}: absent")
                continue
            tiers = row.get("potion_tiers") if isinstance(row.get("potion_tiers"), list) else []
            formulas = row.get("formulas") if isinstance(row.get("formulas"), list) else []
            sources = row.get("source_files") if isinstance(row.get("source_files"), list) else []
            print(
                f"    - {name}: present | potion_tiers={len(tiers)} | "
                f"formulas={len(formulas)} | sources={len(sources)}"
            )

    print()
    print("SQLite effect inventory:")
    if not database_path.exists():
        print("  database missing")
    else:
        with sqlite3.connect(database_path) as db:
            for name in tuple(dict.fromkeys(LEGACY_SPELL_POWER_COMPONENTS + U51_POWER_COMPONENTS)):
                effect_count, potion_variants, sources = _db_effect_status(db, name)
                print(
                    f"  - {name}: effect={effect_count} | "
                    f"potion_variants={potion_variants} | sources={sources}"
                )

    print()
    print("Likely raw source files by filename:")
    for candidate in raw_candidates:
        print(f"  {candidate}")
        if not candidate.exists():
            print("    raw directory missing")
            continue
        any_match = False
        for name in LEGACY_SPELL_POWER_COMPONENTS:
            matches = _likely_raw_files(candidate, name)
            if not matches:
                print(f"    - {name}: none")
                continue
            any_match = True
            print(f"    - {name}: {len(matches)}")
            for item in matches[:10]:
                print(f"        {item}")
        if not any_match:
            print("    No legacy component filenames matched. Source pages may use generic UESP filenames.")

    print()
    print("Interpretation boundary:")
    print("  - This audit is read-only.")
    print("  - research/raw and research/processed are the current developer-source paths.")
    print("  - legacy data/raw and data/processed are checked only for migration recovery.")
    print("  - A saved potion selection proves availability, not active uptime.")
    print("  - Potion components must come from the active source corpus/database, not from the saved label alone.")
    print("  - U51 consolidates the power/critical trait names, so the eventual resolver must tolerate versioned source names.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit recoverability of saved spell-power potion evidence.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--processed", type=Path, default=DEFAULT_PROCESSED)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(
        audit(
            database_path=args.database,
            processed_path=args.processed,
            raw_dir=args.raw_dir,
        )
    )
