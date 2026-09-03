from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.boss_encounter_projection import project_boss_file, write_projection_packet
from services.boss_encounter_projection_audit import audit_boss_encounter_projection


def _default_source_dir() -> Path:
    candidates = (
        ROOT / "research" / "eso_info" / "bosses",
        ROOT / "data" / "eso_info" / "bosses",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def _default_output_dir() -> Path:
    research = ROOT / "research" / "encounter_evidence" / "generated"
    if (ROOT / "research").exists():
        return research
    return ROOT / "data" / "encounter_evidence" / "generated"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit all boss source JSONs against the encounter evidence/review pipeline."
    )
    parser.add_argument("--source-dir", type=Path, default=_default_source_dir())
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--write-packets", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=_default_output_dir())
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()

    connection = sqlite3.connect(args.database) if args.database.exists() else None
    try:
        result = audit_boss_encounter_projection(args.source_dir, connection=connection)
    finally:
        if connection is not None:
            connection.close()

    print("\n========================================")
    print(" BOSS ENCOUNTER PROJECTION AUDIT")
    print("========================================")
    print(f"Source directory:              {result.source_dir}")
    print(f"Boss source files:             {result.source_files}")
    print(f"Bosses projected:              {result.projected_bosses}")
    print(f"Bosses with mechanics:         {result.bosses_with_mechanics}")
    print(f"Mechanics declared:            {result.mechanics}")
    print(f"Abilities declared:            {result.abilities}")
    print(f"Phases declared:               {result.phases}")
    print(f"Inferred mechanics:            {result.inferred_mechanics}")
    print(f"Incomplete mechanics:          {result.incomplete_mechanics}")
    print(f"Evidence rows projected:       {result.evidence_rows}")
    print(f"Reconciled facts:              {result.reconciled_facts}")
    print(f"Promotion eligible:            {result.promotion_eligible}")
    print(f"Human review required:         {result.review_required}")
    print(f"Blocked/conflicting:           {result.blocked}")
    print(f"Canonical encounters matched:  {result.database_encounters_matched}")
    print(f"Projected bosses missing DB:   {len(result.database_encounters_missing)}")
    print(f"Projection failures:           {len(result.failures)}")

    if result.database_encounters_missing:
        print("\nMISSING CANONICAL ENCOUNTERS")
        for encounter_id in result.database_encounters_missing[: max(0, args.samples)]:
            print(f"  - {encounter_id}")

    if result.failures:
        print("\nPROJECTION FAILURES")
        for failure in result.failures[: max(0, args.samples)]:
            print(f"  - {failure.path}: {failure.reason}")

    if args.write_packets:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        written = 0
        for path in sorted(args.source_dir.glob("*.json")):
            try:
                projection = project_boss_file(path)
            except (OSError, ValueError, TypeError):
                continue
            target = args.output_dir / f"{projection.encounter_id}.json"
            write_projection_packet(projection, target)
            written += 1
        print(f"\nGenerated review packets:      {written}")
        print(f"Packet directory:              {args.output_dir}")

    print("\nRESULT: " + ("PASS" if not result.failures else "REVIEW"))
    print(
        "Source data was projected into the existing encounter-evidence contract; "
        "no canonical facts were auto-promoted and eso.db was not modified."
    )
    return 0 if not result.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
