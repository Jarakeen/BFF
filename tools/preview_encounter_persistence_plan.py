from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_evidence import EncounterEvidence, reconcile_encounter_evidence
from services.encounter_persistence_plan import build_persistence_plan
from services.encounter_promotion import build_encounter_promotion_preview


def _load_packet(path: Path) -> tuple[dict, list[EncounterEvidence]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    encounter_id = str(payload.get("encounter_id", "")).strip()
    rows: list[EncounterEvidence] = []

    for raw in payload.get("evidence", []):
        rows.append(
            EncounterEvidence(
                encounter_id=str(raw.get("encounter_id") or encounter_id),
                fact_type=str(raw["fact_type"]),
                fact_key=str(raw["fact_key"]),
                value=raw.get("value"),
                source_type=str(raw["source_type"]),
                source_name=str(raw["source_name"]),
                source_locator=str(raw.get("source_locator", "")),
                source_revision=str(raw.get("source_revision", "")),
                game_update=str(raw.get("game_update", "")),
                patch_version=str(raw.get("patch_version", "")),
                confidence=str(raw.get("confidence", "medium")),
                notes=str(raw.get("notes", "")),
            )
        )

    return payload, rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Preview exact schema-v3 canonical fact/evidence rows without writing SQLite"
    )
    ap.add_argument("packet", type=Path)
    ap.add_argument("--fact", help="Show only one fact key, for example bridge_thresholds")
    args = ap.parse_args()

    payload, evidence = _load_packet(args.packet)
    reconciled = reconcile_encounter_evidence(evidence)
    candidates = build_encounter_promotion_preview(reconciled)
    plans = build_persistence_plan(candidates)

    if args.fact:
        plans = [plan for plan in plans if plan.fact.fact_key == args.fact]

    total_evidence = sum(len(plan.evidence) for plan in plans)

    print("=" * 76)
    print(" ENCOUNTER SCHEMA V3 PERSISTENCE PLAN - READ ONLY")
    print("=" * 76)
    print(f"packet:             {args.packet}")
    print(f"content:            {payload.get('content_id', '(unknown)')}")
    print(f"encounter:          {payload.get('encounter_name', payload.get('encounter_id', '(unknown)'))}")
    print(f"canonical fact rows:{len(plans):6}")
    print(f"evidence link rows: {total_evidence:6}")

    if not plans:
        print("\nNo promotion-eligible, lossless schema-v3 rows match the request.")
    else:
        for plan in plans:
            fact = plan.fact
            print()
            print(f"[FACT] {fact.logical_ref}")
            print(f"  encounter_id:      {fact.encounter_id}")
            print(f"  canonical_kind:    {fact.canonical_kind}")
            print(f"  payload_json:      {fact.payload_json}")
            print(f"  review_status:     {fact.review_status}")
            print(f"  valid_from_update: {fact.valid_from_update or '(unresolved)'}")
            print(f"  valid_from_patch:  {fact.valid_from_patch or '(unresolved)'}")
            print(f"  evidence rows:     {len(plan.evidence)}")

            for row in plan.evidence:
                locator = f" | {row.source_locator}" if row.source_locator else ""
                revision = f" | rev {row.source_revision}" if row.source_revision else ""
                update = f" | {row.game_update}" if row.game_update else ""
                patch = f" | {row.patch_version}" if row.patch_version else ""
                print(
                    f"    - {row.source_type}: {row.source_name}{locator}{revision}{update}{patch} "
                    f"[{row.confidence}] value={row.source_value_json}"
                )

    print("\nPlan only. No SQLite rows, source JSON files, or schema objects were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
