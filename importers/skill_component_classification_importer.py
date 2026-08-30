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
SOURCE = "ability.coef_description semantic extractor; upstream provenance unresolved"
CONFIDENCE = 1.0


@dataclass(frozen=True)
class ImportSummary:
    scanned: int
    active: int
    qualified: int
    write_eligible: int
    inserted: int
    removed_derived: int
    protected_existing: int
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

    @property
    def key(self) -> tuple[int, int]:
        return (self.skill_rank_id, self.coefficient_number)


def _table_exists(db: sqlite3.Connection) -> bool:
    return (
        db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (TABLE,),
        ).fetchone()
        is not None
    )


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
    """Return whether the row is safe to persist without inventing mechanics."""

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
        write_eligible=len(candidates),
        inserted=0,
        removed_derived=0,
        protected_existing=0,
        skipped_inactive=skipped_inactive,
        skipped_slot_mismatch=skipped_slot_mismatch,
        skipped_missing_fragment=skipped_missing_fragment,
        skipped_incomplete=skipped_incomplete,
    )
    return tuple(candidates), summary


def _existing_classification_state(
    database_path: str | Path,
) -> tuple[dict[tuple[int, int], str | None], int]:
    """Read current classification ownership without mutating the database."""

    path = Path(database_path)
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
        if not _table_exists(db):
            return {}, 0
        rows = db.execute(
            f"SELECT skill_rank_id, coefficient_number, source FROM {TABLE}"
        ).fetchall()

    sources = {
        (int(skill_rank_id), int(coefficient_number)): source
        for skill_rank_id, coefficient_number, source in rows
    }
    derived_count = sum(1 for source in sources.values() if source == SOURCE)
    return sources, derived_count


def _protect_foreign_rows(
    candidates: tuple[ClassificationCandidate, ...],
    existing_sources: dict[tuple[int, int], str | None],
) -> tuple[tuple[ClassificationCandidate, ...], int]:
    """Never overwrite a row owned by another/manual evidence source."""

    eligible: list[ClassificationCandidate] = []
    protected = 0
    for candidate in candidates:
        existing_source = existing_sources.get(candidate.key)
        if candidate.key in existing_sources and existing_source != SOURCE:
            protected += 1
            continue
        eligible.append(candidate)
    return tuple(eligible), protected


def import_skill_component_classifications(
    database_path: str | Path,
    *,
    replace_derived: bool = True,
    limit: int | None = None,
    dry_run: bool = True,
) -> ImportSummary:
    """Populate verified per-coefficient semantics from coefficient-aware text.

    Safety rules:
    - dry-run is the API default;
    - ``can_crit`` remains NULL until a separate verified source exists;
    - rebuilds delete only rows owned by this exact extractor ``SOURCE``;
    - rows owned by manual or other sources are never overwritten;
    - source wording does not claim provenance that ``skills_raw.json`` has not
      formally established.
    """

    path = Path(database_path)
    candidates, summary = _evaluate_candidates(path, limit=limit)
    existing_sources, existing_derived = _existing_classification_state(path)
    eligible, protected = _protect_foreign_rows(candidates, existing_sources)

    if dry_run:
        return ImportSummary(
            scanned=summary.scanned,
            active=summary.active,
            qualified=summary.qualified,
            write_eligible=len(eligible),
            inserted=0,
            removed_derived=existing_derived if replace_derived else 0,
            protected_existing=protected,
            skipped_inactive=summary.skipped_inactive,
            skipped_slot_mismatch=summary.skipped_slot_mismatch,
            skipped_missing_fragment=summary.skipped_missing_fragment,
            skipped_incomplete=summary.skipped_incomplete,
        )

    inserted = 0
    removed_derived = 0
    with sqlite3.connect(path) as db:
        _create_table(db)

        # Re-read ownership inside the write transaction in case the table was
        # created or changed between preflight and mutation.
        current_rows = db.execute(
            f"SELECT skill_rank_id, coefficient_number, source FROM {TABLE}"
        ).fetchall()
        current_sources = {
            (int(skill_rank_id), int(coefficient_number)): source
            for skill_rank_id, coefficient_number, source in current_rows
        }
        eligible, protected = _protect_foreign_rows(candidates, current_sources)

        if replace_derived:
            removed_derived = int(
                db.execute(
                    f"SELECT COUNT(*) FROM {TABLE} WHERE source = ?",
                    (SOURCE,),
                ).fetchone()[0]
            )
            db.execute(f"DELETE FROM {TABLE} WHERE source = ?", (SOURCE,))

        for candidate in eligible:
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
        write_eligible=len(eligible),
        inserted=inserted,
        removed_derived=removed_derived,
        protected_existing=protected,
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
        "--write",
        action="store_true",
        help="Explicitly write qualified derived rows. Default is read-only dry-run.",
    )
    parser.add_argument(
        "--append-derived",
        action="store_true",
        help=(
            "Do not first remove rows owned by this extractor source. Foreign/manual "
            "rows are protected in either mode."
        ),
    )
    args = parser.parse_args()

    dry_run = not args.write
    summary = import_skill_component_classifications(
        args.database,
        replace_derived=not args.append_derived,
        limit=args.limit,
        dry_run=dry_run,
    )

    print("\n========================================")
    print(" PHASE 3 SKILL COMPONENT IMPORT")
    print("========================================")
    print(f"Database:                 {args.database}")
    print(f"Mode:                     {'DRY RUN / READ ONLY' if dry_run else 'WRITE'}")
    print(f"Source:                   {SOURCE}")
    print(f"Coefficient rows scanned: {summary.scanned}")
    print(f"Active coefficients:      {summary.active}")
    print(f"Qualified rows:           {summary.qualified}")
    print(f"Write-eligible rows:      {summary.write_eligible}")
    print(f"Protected existing rows:  {summary.protected_existing}")
    print(f"Derived rows to replace:  {summary.removed_derived}")
    print(f"Rows written:             {summary.inserted}")
    print(f"Inactive slots skipped:   {summary.skipped_inactive}")
    print(f"Slot mismatches skipped:  {summary.skipped_slot_mismatch}")
    print(f"Missing fragments:        {summary.skipped_missing_fragment}")
    print(f"Incomplete semantics:     {summary.skipped_incomplete}")
    print("Crit eligibility:         unresolved / stored NULL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
