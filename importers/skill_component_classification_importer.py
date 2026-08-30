from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_text_evidence import extract_component_text_evidence
from tools.audit_skill_coefficient_slots import load_slot_audit
from tools.audit_skill_component_text_semantics import is_active_coefficient


DEFAULT_DATABASE = ROOT / "data" / "eso.db"
TABLE = "skill_component_classification"
SOURCE = "UESP coefficient-aware tooltip text"
CONFIDENCE = 1.0


@dataclass(frozen=True)
class ImportSummary:
    scanned: int
    active: int
    inserted: int
    skipped_inactive: int
    skipped_slot_mismatch: int
    skipped_missing_fragment: int
    skipped_incomplete: int


def _create_table(db: sqlite3.Connection) -> None:
    db.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL,
            effect_kind TEXT NOT NULL,
            damage_type TEXT,
            is_dot INTEGER,
            is_aoe INTEGER,
            can_crit INTEGER,
            source TEXT,
            confidence REAL,
            evidence_fragment TEXT,
            evidence_json TEXT,
            PRIMARY KEY (skill_rank_id, coefficient_number)
        )
        """
    )

    columns = {str(row[1]) for row in db.execute(f"PRAGMA table_info({TABLE})").fetchall()}
    if "evidence_fragment" not in columns:
        db.execute(f"ALTER TABLE {TABLE} ADD COLUMN evidence_fragment TEXT")
    if "evidence_json" not in columns:
        db.execute(f"ALTER TABLE {TABLE} ADD COLUMN evidence_json TEXT")


def _complete_for_import(evidence) -> bool:
    if evidence.effect_kind is None:
        return False
    if evidence.is_dot is None or evidence.is_aoe is None:
        return False
    if evidence.effect_kind == "damage" and evidence.damage_type is None:
        return False
    return True


def import_skill_component_classifications(
    database_path: str | Path,
    *,
    clear_existing: bool = True,
    limit: int | None = None,
) -> ImportSummary:
    """Populate verified per-coefficient semantics from coefficient-aware text.

    This importer deliberately leaves ``can_crit`` NULL. Tooltip wording does not
    prove critical eligibility, so that field requires a separate verified source.
    Rows are imported only when the active coefficient is aligned to its same-numbered
    raw source slot and the text extractor proves all currently required semantics.
    """

    path = Path(database_path)
    if not path.exists():
        raise FileNotFoundError(path)

    rows = load_slot_audit(path, limit=limit)

    scanned = len(rows)
    active = 0
    inserted = 0
    skipped_inactive = 0
    skipped_slot_mismatch = 0
    skipped_missing_fragment = 0
    skipped_incomplete = 0

    with sqlite3.connect(path) as db:
        _create_table(db)
        if clear_existing:
            db.execute(f"DELETE FROM {TABLE}")

        for row in rows:
            if not is_active_coefficient(row):
                skipped_inactive += 1
                continue
            active += 1

            if row.raw_slot_matches_coefficient is not True:
                skipped_slot_mismatch += 1
                continue

            evidence = extract_component_text_evidence(
                row.coef_description,
                row.coefficient_number,
            )
            if not evidence.fragment:
                skipped_missing_fragment += 1
                continue
            if not _complete_for_import(evidence):
                skipped_incomplete += 1
                continue

            db.execute(
                f"""
                INSERT OR REPLACE INTO {TABLE} (
                    skill_rank_id,
                    coefficient_number,
                    effect_kind,
                    damage_type,
                    is_dot,
                    is_aoe,
                    can_crit,
                    source,
                    confidence,
                    evidence_fragment,
                    evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(row.skill_rank_id),
                    int(row.coefficient_number),
                    str(evidence.effect_kind),
                    evidence.damage_type,
                    int(bool(evidence.is_dot)),
                    int(bool(evidence.is_aoe)),
                    None,
                    SOURCE,
                    CONFIDENCE,
                    evidence.fragment,
                    json.dumps(list(evidence.evidence), ensure_ascii=False),
                ),
            )
            inserted += 1

        db.commit()

    return ImportSummary(
        scanned=scanned,
        active=active,
        inserted=inserted,
        skipped_inactive=skipped_inactive,
        skipped_slot_mismatch=skipped_slot_mismatch,
        skipped_missing_fragment=skipped_missing_fragment,
        skipped_incomplete=skipped_incomplete,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import verified per-coefficient skill component classifications."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--append",
        action="store_true",
        help="Keep existing classification rows instead of rebuilding the table contents.",
    )
    args = parser.parse_args()

    summary = import_skill_component_classifications(
        args.database,
        clear_existing=not args.append,
        limit=args.limit,
    )

    print("\n========================================")
    print(" PHASE 3 SKILL COMPONENT IMPORT")
    print("========================================")
    print(f"Database:                 {args.database}")
    print(f"Coefficient rows scanned: {summary.scanned}")
    print(f"Active coefficients:      {summary.active}")
    print(f"Imported rows:            {summary.inserted}")
    print(f"Inactive slots skipped:   {summary.skipped_inactive}")
    print(f"Slot mismatches skipped:  {summary.skipped_slot_mismatch}")
    print(f"Missing fragments:        {summary.skipped_missing_fragment}")
    print(f"Incomplete semantics:     {summary.skipped_incomplete}")
    print("Crit eligibility:         unresolved / stored NULL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
