from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_content_gap_audit import audit_content_encounters


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit one canonical content record against encounter evidence packets"
    )
    parser.add_argument("content_id")
    parser.add_argument("--database", type=Path, default=Path("data/eso.db"))
    parser.add_argument(
        "--packet-dir",
        type=Path,
        default=Path("data/encounter_evidence"),
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("data/uesp"),
        help="Root containing tracked UESP content records with boss_ids",
    )
    args = parser.parse_args()

    if not args.database.exists():
        print(f"BLOCKED: database file does not exist: {args.database}")
        return 2

    connection = sqlite3.connect(args.database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        try:
            audit = audit_content_encounters(
                connection,
                content_id=args.content_id,
                packet_dir=args.packet_dir,
                source_root=args.source_root,
            )
        except ValueError as exc:
            print(f"BLOCKED: {exc}")
            return 2
    finally:
        connection.close()

    print("=" * 76)
    print(" ENCOUNTER CONTENT GAP AUDIT - READ ONLY")
    print("=" * 76)
    print(f"content:          {audit.content_name} [{audit.content_id}]")
    print(f"database:         {args.database}")
    print(f"packet directory: {args.packet_dir}")
    print(f"source root:      {args.source_root}")
    print(f"encounters in DB: {len(audit.database_encounters)}")
    print(f"evidence packets: {len(audit.packet_gaps)}")
    print(f"source boss_ids:  {len(audit.source_declared_encounters)}")
    print()

    if audit.source_declared_encounters:
        print("=== SOURCE-DECLARED ENCOUNTERS ===")
        for encounter_id in audit.source_declared_encounters:
            markers: list[str] = []
            if encounter_id in audit.source_declared_missing_db:
                markers.append("missing DB")
            if encounter_id in audit.source_declared_missing_packets:
                markers.append("missing packet")
            suffix = f" | {', '.join(markers)}" if markers else ""
            print(f"  - {encounter_id}{suffix}")
        print()

    print("=== CANONICAL ENCOUNTERS ===")
    for row in audit.database_encounters:
        print(f"  {row.name} [{row.encounter_id}]")
        print(
            "    "
            f"NPCs={row.npc_count} health={row.health_count} abilities={row.ability_count} "
            f"mechanics={row.mechanic_count} phases={row.phase_count} dialogue={row.dialogue_count}"
        )
        print(
            "    "
            f"canonical_facts={row.canonical_fact_count} "
            f"canonical_evidence={row.canonical_evidence_count}"
        )
        if row.npc_count == 0:
            print("    GAP: no encounter_npc associations")
    if not audit.database_encounters:
        print("  (none)")
    print()

    print("=== EVIDENCE / PROMOTION BACKLOG ===")
    for gap in audit.packet_gaps:
        print(f"  {gap.encounter_name} [{gap.encounter_id}] | {gap.packet_path.name}")
        print(
            "    "
            f"reconciled={gap.reconciled_facts} eligible={len(gap.eligible)} "
            f"review_required={len(gap.review_required)} blocked={len(gap.blocked)}"
        )
        print(
            "    "
            f"persisted_refs={len(gap.persisted)} missing_eligible={len(gap.missing_eligible)}"
        )
        for ref in gap.missing_eligible:
            print(f"    MISSING ELIGIBLE: {ref}")
        for ref in gap.blocked:
            print(f"    BLOCKED: {ref}")
        if gap.review_required:
            print("    review backlog:")
            for ref in gap.review_required:
                print(f"      - {ref}")
    if not audit.packet_gaps:
        print("  (none)")
    print()

    if audit.encounters_without_packets:
        print("=== DATABASE ENCOUNTERS WITHOUT EVIDENCE PACKETS ===")
        for encounter_id in audit.encounters_without_packets:
            print(f"  - {encounter_id}")
        print()

    if audit.packets_without_encounters:
        print("=== EVIDENCE PACKETS WITHOUT CANONICAL ENCOUNTERS ===")
        for encounter_id in audit.packets_without_encounters:
            print(f"  - {encounter_id}")
        print()

    missing_eligible = sum(len(gap.missing_eligible) for gap in audit.packet_gaps)
    blocked = sum(len(gap.blocked) for gap in audit.packet_gaps)
    review = sum(len(gap.review_required) for gap in audit.packet_gaps)
    no_npcs = sum(1 for row in audit.database_encounters if row.npc_count == 0)

    print("=== GAP SUMMARY ===")
    print(f"  missing eligible canonical facts: {missing_eligible}")
    print(f"  blocked conflicting facts:        {blocked}")
    print(f"  single-source review backlog:     {review}")
    print(f"  encounters without NPC links:     {no_npcs}")
    print(f"  source bosses missing DB rows:    {len(audit.source_declared_missing_db)}")
    print(f"  source bosses missing packets:    {len(audit.source_declared_missing_packets)}")
    print(f"  DB encounters without packets:    {len(audit.encounters_without_packets)}")
    print(f"  packets without DB encounters:    {len(audit.packets_without_encounters)}")
    print()
    print("No database rows or evidence packets were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
