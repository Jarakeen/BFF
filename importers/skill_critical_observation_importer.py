from __future__ import annotations

"""Import positive runtime critical observations without guessing negatives.

The semantic component classifier and runtime critical evidence intentionally own
separate tables. Static tooltip/coefficient evidence says what a component is;
runtime observations can prove that a uniquely mappable component *can* crit.

Absence of an observed critical result never writes ``can_crit = False``.
"""

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_critical_observation import (
    CriticalComponentCandidate,
    CriticalEventFamily,
    RuntimeCriticalObservation,
    resolve_observed_critical_eligibility,
)
from tools.audit_skill_critical_mapping import load_critical_mapping_groups


DEFAULT_DATABASE = ROOT / "data" / "eso.db"
CLASSIFICATION_TABLE = "skill_component_classification"
EVIDENCE_TABLE = "skill_component_critical_evidence"


@dataclass(frozen=True)
class CriticalEvidenceImportSummary:
    observations: int
    observation_events: int
    resolved_components: int
    ambiguous_observations: int
    unmatched_observations: int
    already_classified_observations: int
    write_eligible_rows: int
    rows_written: int


def load_runtime_critical_observations(path: str | Path) -> tuple[RuntimeCriticalObservation, ...]:
    """Load normalized observations from JSON array/object or JSONL.

    Each record must contain:
      - ``ability_id``: positive integer
      - ``event_family``: damage_direct, damage_periodic, heal_direct, heal_periodic
      - ``source``: provenance string identifying the log/report/collector source
      - ``observed_count``: optional positive integer, default 1
    """

    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    text = source_path.read_text(encoding="utf-8").strip()
    if not text:
        return ()

    records: list[object]
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        if isinstance(decoded, list):
            records = list(decoded)
        else:
            records = [decoded]

    observations: list[RuntimeCriticalObservation] = []
    for index, raw in enumerate(records, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"observation {index} must be a JSON object")
        try:
            family = CriticalEventFamily(str(raw["event_family"]).strip())
            observation = RuntimeCriticalObservation(
                ability_id=int(raw["ability_id"]),
                event_family=family,
                source=str(raw["source"]),
                observed_count=int(raw.get("observed_count", 1)),
            )
        except KeyError as exc:
            raise ValueError(f"observation {index} missing required field {exc.args[0]!r}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid observation {index}: {exc}") from exc
        observations.append(observation)

    return tuple(observations)


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    return (
        db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        is not None
    )


def _existing_can_crit(database_path: str | Path) -> dict[tuple[int, int], bool]:
    """Read explicit classification values so runtime evidence never overwrites them."""

    path = Path(database_path)
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
        if not _table_exists(db, CLASSIFICATION_TABLE):
            return {}
        rows = db.execute(
            f"""
            SELECT skill_rank_id, coefficient_number, can_crit
            FROM {CLASSIFICATION_TABLE}
            WHERE can_crit IS NOT NULL
            """
        ).fetchall()

    return {
        (int(skill_rank_id), int(coefficient_number)): bool(int(can_crit))
        for skill_rank_id, coefficient_number, can_crit in rows
    }


def _load_candidates(database_path: str | Path) -> tuple[CriticalComponentCandidate, ...]:
    groups, _summary = load_critical_mapping_groups(database_path)
    explicit = _existing_can_crit(database_path)
    candidates: list[CriticalComponentCandidate] = []

    for group in groups:
        for candidate in group.candidates:
            known = explicit.get(candidate.key)
            candidates.append(replace(candidate, can_crit=known))

    return tuple(candidates)


def _create_evidence_table(db: sqlite3.Connection) -> None:
    db.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {EVIDENCE_TABLE} (
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL,
            ability_id INTEGER NOT NULL,
            event_family TEXT NOT NULL,
            can_crit INTEGER NOT NULL CHECK (can_crit = 1),
            source TEXT NOT NULL,
            observed_count INTEGER NOT NULL CHECK (observed_count > 0),
            evidence_json TEXT,
            PRIMARY KEY (
                skill_rank_id,
                coefficient_number,
                event_family,
                source
            )
        )
        """
    )


def import_runtime_critical_evidence(
    database_path: str | Path,
    observations: tuple[RuntimeCriticalObservation, ...],
    *,
    dry_run: bool = True,
) -> CriticalEvidenceImportSummary:
    """Resolve and optionally persist positive runtime critical evidence.

    Writes are source-keyed UPSERTs. Re-importing the same source replaces its
    observed count rather than accumulating duplicates. Ambiguous and unmatched
    observations are never written.
    """

    path = Path(database_path)
    if not path.exists():
        raise FileNotFoundError(path)

    candidates = _load_candidates(path)
    resolved, resolution = resolve_observed_critical_eligibility(candidates, observations)

    if dry_run:
        return CriticalEvidenceImportSummary(
            observations=resolution.observations,
            observation_events=resolution.observation_events,
            resolved_components=resolution.resolved_components,
            ambiguous_observations=resolution.ambiguous_observations,
            unmatched_observations=resolution.unmatched_observations,
            already_classified_observations=resolution.already_classified_observations,
            write_eligible_rows=len(resolved),
            rows_written=0,
        )

    written = 0
    with sqlite3.connect(path) as db:
        _create_evidence_table(db)
        for item in resolved:
            db.execute(
                f"""
                INSERT INTO {EVIDENCE_TABLE} (
                    skill_rank_id,
                    coefficient_number,
                    ability_id,
                    event_family,
                    can_crit,
                    source,
                    observed_count,
                    evidence_json
                ) VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT (
                    skill_rank_id,
                    coefficient_number,
                    event_family,
                    source
                ) DO UPDATE SET
                    ability_id = excluded.ability_id,
                    can_crit = 1,
                    observed_count = excluded.observed_count,
                    evidence_json = excluded.evidence_json
                """,
                (
                    item.skill_rank_id,
                    item.coefficient_number,
                    item.ability_id,
                    item.event_family.value,
                    item.source,
                    item.observed_count,
                    json.dumps(
                        {
                            "proof": "positive runtime critical observation",
                            "ability_id": item.ability_id,
                            "event_family": item.event_family.value,
                            "observed_count": item.observed_count,
                            "source": item.source,
                            "negative_inference": False,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                ),
            )
            written += 1
        db.commit()

    return CriticalEvidenceImportSummary(
        observations=resolution.observations,
        observation_events=resolution.observation_events,
        resolved_components=resolution.resolved_components,
        ambiguous_observations=resolution.ambiguous_observations,
        unmatched_observations=resolution.unmatched_observations,
        already_classified_observations=resolution.already_classified_observations,
        write_eligible_rows=len(resolved),
        rows_written=written,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import positive runtime skill critical observations. Default is "
            "read-only; ambiguous mappings and negative inference are rejected."
        )
    )
    parser.add_argument("observations", help="Normalized JSON/JSONL observation file")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Persist resolved positive evidence")
    mode.add_argument("--dry-run", action="store_true", help="Explicit read-only mode (default)")
    args = parser.parse_args()

    observations = load_runtime_critical_observations(args.observations)
    summary = import_runtime_critical_evidence(
        args.database,
        observations,
        dry_run=not args.write,
    )

    print("\n========================================")
    print(" PHASE 3 RUNTIME CRITICAL EVIDENCE")
    print("========================================")
    print(f"Database:                        {args.database}")
    print(f"Observation file:                {args.observations}")
    print(f"Mode:                            {'DRY RUN / READ ONLY' if not args.write else 'WRITE'}")
    print(f"Observation groups:              {summary.observations}")
    print(f"Observed critical events:        {summary.observation_events}")
    print(f"Resolved components:             {summary.resolved_components}")
    print(f"Ambiguous observations skipped:  {summary.ambiguous_observations}")
    print(f"Unmatched observations skipped:  {summary.unmatched_observations}")
    print(f"Already classified skipped:      {summary.already_classified_observations}")
    print(f"Write-eligible evidence rows:    {summary.write_eligible_rows}")
    print(f"Rows written:                    {summary.rows_written}")
    print("Negative inference:              disabled; absence never writes False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
