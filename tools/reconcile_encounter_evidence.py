from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_evidence import EncounterEvidence, reconcile_encounter_evidence


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
                source_family=str(raw.get("source_family", "")),
                game_update=str(raw.get("game_update", "")),
                patch_version=str(raw.get("patch_version", "")),
                confidence=str(raw.get("confidence", "medium")),
                notes=str(raw.get("notes", "")),
            )
        )

    return payload, rows


def _display_value(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


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

    payload, evidence = _load_packet(args.packet)
    facts = reconcile_encounter_evidence(evidence)
    if args.status:
        facts = [fact for fact in facts if fact.status == args.status]

    print("=" * 76)
    print(" ENCOUNTER EVIDENCE RECONCILIATION - READ ONLY")
    print("=" * 76)
    print(f"packet:          {args.packet}")
    print(f"content:         {payload.get('content_id', '(unknown)')}")
    print(f"encounter:       {payload.get('encounter_name', payload.get('encounter_id', '(unknown)'))}")
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
