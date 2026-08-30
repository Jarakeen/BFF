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
    qualified: int
    inserted: int
    skipped_inactive: int
    skipped_slot_mismatch: int
    skipped_missing_fragment: int
    skipped_incomplete: int


@dataclass(frozen=True)
class ClassificationCandidate:
    skill_rank_id: int
    coefficient_number: int
    effect_kind: str
    damage_type: str | None
    is_dot: bool | None
    is_aoe: bool | None
    evidence_fragment: str
    evidence: tuple[str, ...]


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
    """Return whether the row is safe to persist without inventing mechanics.

    Damage needs a complete routing identity because those fields can affect
    combat math immediately. Heal semantics need delivery and recipient shape
    to be mechanically complete. A shield may be persisted once its effect kind
    is explicitly proven; damage-only routing fields are not applicable and stay
    NULL rather than being fabricated as False.
    """

    if evidence.effect_kind is None:
        return False
    if evidence.effect_kind == "damage":
        return (
            evidence.damage_type is not None
            and evidence.is_dot is not None
            and evidence.is_aoe is not None
        )
    if evidence.effect_kind == "heal":
        return evidence.is_dot is not None and evidence.is_aoe is not None
    if evidence.effect_kind == "shield":
        return True
    return False


def _evaluate_candidates(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[tuple[ClassificationCandidate, ...], ImportSummary]:
    path = Path(database_path)
    if not path.exists():
        raise FileNotFoundError(path)

    rows = load_slot_audit(path, limit=limit)

    active = 0
    skipped_inactive = 0
    skipped_slot_mismatch = 0
    skipped_missing_fragment = 0
    skipped_incomplete = 0
    candidates: list[ClassificationCandidate] = []

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

        candidates.append(
            ClassificationCandidate(
                skill_rank_id=int(row.skill_rank_id),
                coefficient_number=int(row.coefficient_number),
                effect_kind=str(evidence.effect_kind),
                damage_type=evidence.damage_type,
                is_dot=evidence.is_dot,
                is_aoe=evidence.is_aoe,
                evidence_fragment=evidence.fragment,
                evidence=tuple(evidence.evidence),
            )
        )

    summary = ImportSummary(
        scanned=len(rows),
        active=active,
        qualified=len(candidates),
        inserted=0,
        skipped_inactive=skipped_inactive,
        skipped_slot_mismatch=skipped_slot_mismatch,
        skipped_missing_fragment=skipped_missing_fragment,
        skipped_incomplete=skipped_incomplete,
    )
    return tuple(candidates), summary


def import_skill_component_classifications(
    database_path: str | Path,
    *,
    clear_existing: bool = True,
    limit: int | None = None,
    dry_run: bool = False,
) -> ImportSummary:
    """Populate verified per-coefficient semantics from coefficient-aware text.

    This importer deliberately leaves ``can_crit`` NULL. Tooltip wording does not
    prove critical eligibility, so that field requires a separate verified source.
    Rows are imported only when the active coefficient is aligned to its same-numbered
    raw source slot and the text extractor proves the mechanics required for that
    effect family.

    When ``dry_run`` is true, the exact qualification logic is executed but the
    database is never opened for writing. No table is created, altered, cleared,
    or populated.
    """

    path = Path(database_path)
    candidates, summary = _evaluate_candidates(path, limit=limit)

    if dry_run:
        return summary

    inserted = 0
    with sqlite3.connect(path) as db:
        _create_table(db)
        if clear_existing:
            db.execute(f"DELETE FROM {TABLE}")

        for candidate in candidates:
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
                    candidate.skill_rank_id,
                    candidate.coefficient_number,
                    candidate.effect_kind,
                    candidate.damage_type,
                    None if candidate.is_dot is None else int(candidate.is_dot),
                    None if candidate.is_aoe is None else int(candidate.is_aoe),
                    None,
                    SOURCE,
                    CONFIDENCE,
                    candidate.evidence_fragment,
                    json.dumps(list(candidate.evidence), ensure_ascii=False),
                ),
            )
            inserted += 1

        db.commit()

    return ImportSummary(
        scanned=summary.scanned,
        active=summary.active,
        qualified=summary.qualified,
        inserted=inserted,
        skipped_inactive=summary.skipped_inactive,
        skipped_slot_mismatch=summary.skipped_slot_mismatch,
        skipped_missing_fragment=summary.skipped_missing_fragment,
        skipped_incomplete=summary.skipped_incomplete,
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate exactly what would qualify without writing anything to the database.",
    )
    args = parser.parse_args()

    summary = import_skill_component_classifications(
        args.database,
        clear_existing=not args.append,
        limit=args.limit,
        dry_run=args.dry_run,
    )

    print("\n========================================")
    print(" PHASE 3 SKILL COMPONENT IMPORT")
    print("========================================")
    print(f"Database:                 {args.database}")
    print(f"Mode:                     {'DRY RUN / READ ONLY' if args.dry_run else 'WRITE'}")
    print(f"Coefficient rows scanned: {summary.scanned}")
    print(f"Active coefficients:      {summary.active}")
    print(f"Qualified rows:           {summary.qualified}")
    print(f"Rows written:             {summary.inserted}")
    print(f"Inactive slots skipped:   {summary.skipped_inactive}")
    print(f"Slot mismatches skipped:  {summary.skipped_slot_mismatch}")
    print(f"Missing fragments:        {summary.skipped_missing_fragment}")
    print(f"Incomplete semantics:     {summary.skipped_incomplete}")
    print("Crit eligibility:         unresolved / stored NULL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
