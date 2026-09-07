from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_evidence import reconcile_encounter_evidence
from services.encounter_evidence_packet import load_encounter_evidence_packet


def _display_value(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _load_packet(path: Path) -> tuple[dict, list]:
    """Compatibility adapter for callers that still expect ``(payload, evidence)``.

    ``load_encounter_evidence_packet`` is the canonical packet loader.  Older
    audit/preview/test code historically imported this private helper and
    expects a dict-like metadata payload plus a mutable evidence list.  Keep
    that contract here while routing all parsing and validation through the
    canonical loader so the two paths cannot drift apart.
    """
    packet = load_encounter_evidence_packet(path)
    payload = {
        "schema_version": packet.schema_version,
        "content_id": packet.content_id,
        "encounter_id": packet.encounter_id,
        "encounter_name": packet.encounter_name,
    }
    return payload, list(packet.evidence)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Reconcile source-separated encounter evidence without changing the database"
    )
    ap.add_argument("packet", type=Path)
    ap.add_argument(
        "--status",
        choices=("single_source", "corroborated", "conflicting"),
        help="Show only facts with this reconciliation status.",
    )
    args = ap.parse_args()

    packet = load_encounter_evidence_packet(args.packet)
    evidence = list(packet.evidence)
    facts = reconcile_encounter_evidence(evidence)
    if args.status:
        facts = [fact for fact in facts if fact.status == args.status]

    print("=" * 76)
    print(" ENCOUNTER EVIDENCE RECONCILIATION - READ ONLY")
    print("=" * 76)
    print(f"packet:          {args.packet}")
    print(f"content:         {packet.content_id or '(unknown)'}")
    print(f"encounter:       {packet.encounter_name}")
    print(f"evidence rows:   {len(evidence)}")

    all_facts = reconcile_encounter_evidence(evidence)
    for status in ("corroborated", "single_source", "conflicting"):
        count = sum(1 for fact in all_facts if fact.status == status)
        print(f"{status + ':':17} {count}")

    if not facts:
        print("\nNo facts match the requested filter.")
    else:
        for fact in facts:
            print()
            print(
                f"[{fact.status.upper()}] "
                f"{fact.fact_type}:{fact.fact_key} "
                f"sources={fact.distinct_sources} values={fact.distinct_values}"
            )
            if fact.value is not None:
                print(f"  value: {_display_value(fact.value)}")
            else:
                print("  value: unresolved because sources conflict")

            for row in fact.evidence:
                locator = f" | {row.source_locator}" if row.source_locator else ""
                revision = f" | rev {row.source_revision}" if row.source_revision else ""
                family = f" | family {row.source_family}" if row.source_family else ""
                print(
                    f"    - {row.source_type}: {row.source_name}{locator}{revision}{family} "
                    f"[{row.confidence}] -> {_display_value(row.value)}"
                )

    print("\nNo canonical encounter rows or source JSON files were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())