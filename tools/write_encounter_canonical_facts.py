from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_canonical_mapping import build_encounter_canonical_mapping_preview
from services.encounter_evidence import EncounterEvidence, reconcile_encounter_evidence
from services.encounter_persistence_plan import build_persistence_plan
from services.encounter_persistence_writer import (
    persist_encounter_plans,
    validate_persistence_target,
)
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


def _build_plans(rows: list[EncounterEvidence]):
    facts = reconcile_encounter_evidence(rows)
    candidates = build_encounter_promotion_preview(facts)
    # Force canonical mapping construction as an additional validation step.
    build_encounter_canonical_mapping_preview(candidates)
    return build_persistence_plan(candidates)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate or apply reviewed schema-v3 encounter canonical facts"
    )
    ap.add_argument("packet", type=Path)
    ap.add_argument("--database", type=Path, default=Path("data/eso.db"))
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually write canonical fact/evidence rows. Without this flag the command is validation-only.",
    )
    args = ap.parse_args()

    payload, evidence = _load_packet(args.packet)
    plans = _build_plans(evidence)

    print("=" * 76)
    print(" ENCOUNTER CANONICAL FACT WRITER")
    print("=" * 76)
    print(f"mode:             {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"database:         {args.database}")
    print(f"packet:           {args.packet}")
    print(f"content:          {payload.get('content_id', '(unknown)')}")
    print(f"encounter:        {payload.get('encounter_name', payload.get('encounter_id', '(unknown)'))}")
    print(f"planned facts:    {len(plans)}")
    print(f"planned evidence: {sum(len(plan.evidence) for plan in plans)}")

    if not args.database.exists():
        print("\nBLOCKED: database file does not exist.")
        return 2

    con = sqlite3.connect(args.database)
    con.execute("PRAGMA foreign_keys = ON")
    try:
        try:
            validate_persistence_target(con, plans)
        except RuntimeError as exc:
            print(f"\nBLOCKED: {exc}")
            print("No SQLite rows were changed.")
            return 2

        print("\nTarget validation: PASS")

        if not args.apply:
            print("DRY RUN complete. No SQLite rows were changed.")
            return 0

        try:
            con.execute("BEGIN IMMEDIATE")
            result = persist_encounter_plans(con, plans)
            con.commit()
        except Exception:
            con.rollback()
            raise

        print("\nAPPLY complete.")
        print(f"canonical facts inserted: {result.facts_inserted}")
        print(f"canonical facts existing: {result.facts_existing}")
        print(f"evidence rows inserted:   {result.evidence_inserted}")
        print(f"evidence rows existing:   {result.evidence_existing}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
