from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_npc_candidate_audit import audit_encounter_npc_candidates


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit exact canonical entity/NPC candidates for encounters without writing SQLite"
    )
    parser.add_argument("content_id")
    parser.add_argument("--database", type=Path, default=Path("data/eso.db"))
    args = parser.parse_args()

    connection = sqlite3.connect(args.database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        rows = audit_encounter_npc_candidates(connection, args.content_id)

        print("=" * 76)
        print(" ENCOUNTER NPC CANDIDATE AUDIT - READ ONLY")
        print("=" * 76)
        print(f"content_id:       {args.content_id}")
        print(f"database:         {args.database}")
        print(f"encounters:       {len(rows)}")
        print()

        if not rows:
            print("No canonical encounters found for this content_id.")
            print("No SQLite rows were changed.")
            return 0

        total_candidates = 0
        encounters_without_candidates = 0
        encounters_without_links = 0

        for row in rows:
            print(f"=== {row.encounter_name} [{row.encounter_id}] ===")
            print("search names:")
            for name in row.search_names:
                print(f"  - {name}")

            if row.existing_npc_ids:
                print("existing encounter_npc links:")
                for entity_id in row.existing_npc_ids:
                    print(f"  - {entity_id}")
            else:
                encounters_without_links += 1
                print("existing encounter_npc links: none")

            if not row.candidates:
                encounters_without_candidates += 1
                print("exact canonical candidates: none")
                print()
                continue

            print("exact canonical candidates:")
            total_candidates += len(row.candidates)
            for candidate in row.candidates:
                source_bits = []
                if candidate.source:
                    source_bits.append(candidate.source)
                if candidate.source_entity_type:
                    source_bits.append(candidate.source_entity_type)
                if candidate.source_id:
                    source_bits.append(f"id={candidate.source_id}")
                if candidate.source_name:
                    source_bits.append(f"name={candidate.source_name}")
                source_text = " | ".join(source_bits) if source_bits else "no entity_source row"
                print(
                    f"  - search={candidate.search_name!r} | entity={candidate.entity_id!r} "
                    f"| type={candidate.entity_type!r} | name={candidate.entity_name!r} "
                    f"| slug={candidate.entity_slug!r}"
                )
                print(f"      source: {source_text}")
            print()

        print("=== SUMMARY ===")
        print(f"  candidate rows:                  {total_candidates}")
        print(f"  encounters without candidates:  {encounters_without_candidates}")
        print(f"  encounters without NPC links:   {encounters_without_links}")
        print()
        print("Interpretation:")
        print("  - exact-name candidates are identity leads, not automatic associations")
        print("  - multiple rows or reused names require source/provenance review")
        print("  - Reef Guardian is a known name-collision risk; never attach by name alone")
        print()
        print("No SQLite rows were changed.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
