from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.trial_encounter_source_inventory import build_trial_encounter_source_inventory


ROCKGROVE_BOSSES = (
    "Oaxiltso",
    "Flame-Herald Bahsei",
    "Xalvakka",
)
CURATED_STRATEGY_BOSSES = (
    "Oaxiltso",
    "Flame-Herald Bahsei",
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit local Rockgrove encounter source coverage without changing data")
    ap.add_argument("--database", type=Path, default=Path("data/eso.db"))
    ap.add_argument("--uesp-boss-dir", type=Path, default=Path("data/uesp/bosses"))
    ap.add_argument("--packet-dir", type=Path, default=Path("data/encounter_evidence"))
    args = ap.parse_args()

    connection = sqlite3.connect(args.database)
    try:
        rows = build_trial_encounter_source_inventory(
            connection,
            content_id="rockgrove",
            expected_names=ROCKGROVE_BOSSES,
            raw_boss_dir=args.uesp_boss_dir,
            packet_dir=args.packet_dir,
            curated_strategy_names=CURATED_STRATEGY_BOSSES,
        )
    finally:
        connection.close()

    print("=" * 76)
    print(" ROCKGROVE ENCOUNTER SOURCE INVENTORY - READ ONLY")
    print("=" * 76)
    print(f"database:      {args.database}")
    print(f"UESP bosses:   {args.uesp_boss_dir}")
    print(f"packets:       {args.packet_dir}")
    print()

    for row in rows:
        print(f"=== {row.expected_name} ===")
        print(f"  raw UESP boss JSON:   {', '.join(row.raw_boss_files) if row.raw_boss_files else 'none'}")
        print(f"  legacy boss rows:     {', '.join(row.legacy_boss_ids) if row.legacy_boss_ids else 'none'}")
        print(f"  canonical encounters: {', '.join(row.canonical_encounter_ids) if row.canonical_encounter_ids else 'none'}")
        print(f"  evidence packets:     {', '.join(row.evidence_packets) if row.evidence_packets else 'none'}")
        print(f"  curated strategy:     {'yes' if row.has_curated_strategy else 'no'}")
        print()

    missing_raw = sum(not row.raw_boss_files for row in rows)
    missing_legacy = sum(not row.legacy_boss_ids for row in rows)
    missing_packets = sum(not row.evidence_packets for row in rows)
    missing_canonical = sum(not row.canonical_encounter_ids for row in rows)

    print("=== SUMMARY ===")
    print(f"  bosses without raw UESP record: {missing_raw}")
    print(f"  bosses without legacy DB row:   {missing_legacy}")
    print(f"  bosses without evidence packet: {missing_packets}")
    print(f"  bosses without canonical row:   {missing_canonical}")
    print()
    print("No imports, crawls, database writes, or source-file changes were performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
