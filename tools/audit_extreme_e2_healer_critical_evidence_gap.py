from __future__ import annotations

"""Audit canonical critical-evidence readiness for real healer witnesses.

Read-only. This tool does not infer critical eligibility. It maps the reviewed
Margrat/DF-Healer coefficient-backed heals to the generic runtime critical
observation key (ability id + direct/periodic heal family), reports whether the
mapping is unique, and shows any positive evidence already stored in eso.db.
"""

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from importers.skill_critical_observation_importer import EVIDENCE_TABLE
from tools.audit_skill_critical_mapping import load_critical_mapping_groups


@dataclass(frozen=True)
class Target:
    entity_id: str
    skill_rank_id: int
    coefficient_number: int = 1


TARGETS = (
    Target("combat_prayer", 6226),
    Target("radiating_regeneration", 5147),
    Target("illustrious_healing", 5110),
    Target("energy_orb", 6328),
    Target("echoing_vigor", 6640),
)


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def _evidence_rows(database_path: Path, target: Target) -> tuple[tuple, ...]:
    with sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True) as db:
        if not _table_exists(db, EVIDENCE_TABLE):
            return ()
        return tuple(
            db.execute(
                f"""
                SELECT ability_id, event_family, source, observed_count
                FROM {EVIDENCE_TABLE}
                WHERE skill_rank_id=? AND coefficient_number=?
                  AND can_crit=1 AND observed_count > 0
                ORDER BY event_family, source
                """,
                (target.skill_rank_id, target.coefficient_number),
            ).fetchall()
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()
    database_path = Path(args.database)

    groups, _summary = load_critical_mapping_groups(database_path)
    unique_ready = 0
    proven = 0

    print("EXTREME E2 HEALER CRITICAL EVIDENCE GAP")
    print(f"database={database_path}")
    print()

    for target in TARGETS:
        matching = []
        for group in groups:
            if any(
                candidate.skill_rank_id == target.skill_rank_id
                and candidate.coefficient_number == target.coefficient_number
                for candidate in group.candidates
            ):
                matching.append(group)

        rows = _evidence_rows(database_path, target)
        mapping_unique = (
            len(matching) == 1
            and matching[0].is_unique
            and len(matching[0].candidates) == 1
        )
        if mapping_unique:
            unique_ready += 1
        if rows:
            proven += 1

        print(
            f"entity={target.entity_id!r} | rank={target.skill_rank_id} | "
            f"coef={target.coefficient_number}"
        )
        print(f"  mapping_group_count={len(matching)}")
        print(f"  mapping_unique={mapping_unique}")
        for group in matching:
            keys = tuple(
                (candidate.skill_rank_id, candidate.coefficient_number)
                for candidate in group.candidates
            )
            print(
                f"  mapping: ability_id={group.ability_id} | "
                f"event_family={group.event_family.value} | candidates={keys}"
            )
        print(f"  positive_evidence_rows={len(rows)}")
        for ability_id, event_family, source, observed_count in rows:
            print(
                f"  evidence: ability_id={ability_id} | family={event_family} | "
                f"observed_count={observed_count} | source={source!r}"
            )

        if mapping_unique and not rows:
            group = matching[0]
            print("  observation_template_if_real_positive_crit_is_observed=")
            print(
                "    {"
                f"\"ability_id\": {group.ability_id}, "
                f"\"event_family\": \"{group.event_family.value}\", "
                "\"source\": \"<real provenance>\", \"observed_count\": <positive integer>}"
            )
        print()

    print("PROOF STATUS")
    print(f"target_count={len(TARGETS)}")
    print(f"unique_runtime_mapping_count={unique_ready}")
    print(f"positive_critical_evidence_target_count={proven}")
    print(f"at_least_one_importable_mapping={unique_ready > 0}")
    print(f"at_least_one_proven_heal_crit={proven > 0}")
    if proven > 0:
        print("NEXT_STEP=rerun the saved-build witness inventory; positive evidence now exists for at least one target")
        return 0
    if unique_ready > 0:
        print("NEXT_STEP=collect a real positive critical heal observation for one uniquely mapped target, dry-run the canonical importer, then write only that proven evidence")
        return 2
    print("NEXT_STEP=resolve runtime critical mapping ambiguity before collecting/importing evidence")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
