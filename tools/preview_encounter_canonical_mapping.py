from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_canonical_mapping import build_encounter_canonical_mapping_preview
from services.encounter_promotion import build_encounter_promotion_preview
from tools.reconcile_encounter_evidence import _load_packet
from services.encounter_evidence import reconcile_encounter_evidence


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Preview reviewed encounter facts in canonical shapes without writing the database"
    )
    ap.add_argument("packet", type=Path)
    ap.add_argument(
        "--kind",
        choices=("mechanic_presence", "phase", "phase_transition", "encounter_state", "unmapped"),
        help="Show only one canonical mapping kind.",
    )
    args = ap.parse_args()

    payload, evidence = _load_packet(args.packet)
    reconciled = reconcile_encounter_evidence(evidence)
    promotion = build_encounter_promotion_preview(reconciled)
    mappings = build_encounter_canonical_mapping_preview(promotion)

    if args.kind:
        mappings = [mapping for mapping in mappings if mapping.canonical_kind == args.kind]

    print("=" * 76)
    print(" ENCOUNTER CANONICAL MAPPING PREVIEW - READ ONLY")
    print("=" * 76)
    print(f"packet:          {args.packet}")
    print(f"content:         {payload.get('content_id', '(unknown)')}")
    print(f"encounter:       {payload.get('encounter_name', payload.get('encounter_id', '(unknown)'))}")

    all_mappings = build_encounter_canonical_mapping_preview(promotion)
    print(f"eligible mappings: {len(all_mappings)}")
    print(f"lossless now:      {sum(1 for item in all_mappings if item.lossless_in_current_schema)}")
    print(f"schema extension:  {sum(1 for item in all_mappings if not item.lossless_in_current_schema)}")

    if not mappings:
        print("\nNo mappings match the requested filter.")
    else:
        for mapping in mappings:
            print()
            print(
                f"[{mapping.canonical_kind.upper()}] "
                f"{mapping.fact_type}:{mapping.fact_key} sources={mapping.source_count}"
            )
            print(f"  payload: {json.dumps(mapping.payload, ensure_ascii=False, sort_keys=True)}")
            print(f"  lossless in schema v2: {'yes' if mapping.lossless_in_current_schema else 'no'}")
            print(f"  schema note: {mapping.schema_note}")

    print("\nPreview only. No canonical encounter rows, source JSON, or database schema were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
