from __future__ import annotations

"""Dry-run persistence planner for explicitly reviewed encounter evidence.

This tool never writes SQLite. It joins a source evidence packet to a separate
human-review manifest, reconciles the evidence, and prints the exact canonical
fact/evidence rows that would be eligible for the existing schema-v3 writer.
"""

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_evidence import reconcile_encounter_evidence
from services.reviewed_encounter_fact_persistence import (
    ReviewedEncounterFactDecision,
    build_reviewed_single_source_fact_plans,
)
from tools.reconcile_encounter_evidence import _load_packet


DEFAULT_EVIDENCE = REPO_ROOT / "data" / "encounter_evidence" / "sunspire_lokkestiiz.json"
DEFAULT_REVIEW = REPO_ROOT / "data" / "encounter_reviews" / "sunspire_lokkestiiz.json"


def _load_review(path: Path) -> tuple[dict[str, object], list[ReviewedEncounterFactDecision]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("review manifest root must be an object")
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported review manifest schema_version")
    encounter_id = str(payload.get("encounter_id", "")).strip()
    if not encounter_id:
        raise ValueError("review manifest encounter_id is required")
    rows = payload.get("decisions")
    if not isinstance(rows, list):
        raise ValueError("review manifest decisions must be a list")

    decisions: list[ReviewedEncounterFactDecision] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"review decision #{index + 1} must be an object")
        decisions.append(
            ReviewedEncounterFactDecision(
                encounter_id=encounter_id,
                fact_type=str(row.get("fact_type", "")),
                fact_key=str(row.get("fact_key", "")),
                status=str(row.get("status", "")),
                rationale=str(row.get("rationale", "")),
            )
        )
    return payload, decisions


def _validate_pair(evidence_payload: dict[str, object], review_payload: dict[str, object]) -> None:
    for field in ("content_id", "encounter_id"):
        evidence_value = str(evidence_payload.get(field, "")).strip()
        review_value = str(review_payload.get(field, "")).strip()
        if evidence_value != review_value:
            raise ValueError(
                f"evidence/review {field} mismatch: {evidence_value!r} != {review_value!r}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print reviewed single-source encounter persistence plans without writing SQLite."
    )
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    args = parser.parse_args()

    evidence_path = args.evidence.resolve()
    review_path = args.review.resolve()
    if not evidence_path.exists():
        parser.error(f"evidence packet does not exist: {evidence_path}")
    if not review_path.exists():
        parser.error(f"review manifest does not exist: {review_path}")

    evidence_payload, evidence_rows = _load_packet(evidence_path)
    review_payload, decisions = _load_review(review_path)
    _validate_pair(evidence_payload, review_payload)

    facts = reconcile_encounter_evidence(evidence_rows)
    plans = build_reviewed_single_source_fact_plans(facts, decisions)

    print("REVIEWED ENCOUNTER FACT PERSISTENCE PLAN")
    print(f"Evidence:   {evidence_path}")
    print(f"Review:     {review_path}")
    print("Mode:       DRY RUN / NO DATABASE WRITES")
    print(f"Encounter:  {evidence_payload.get('encounter_name')} [{evidence_payload.get('encounter_id')}]")
    print(f"Facts:      {len(facts)} reconciled")
    print(f"Decisions:  {len(decisions)}")
    print(f"Plans:      {len(plans)}")
    print()

    for plan in plans:
        fact = plan.fact
        print(f"[PLAN] {fact.logical_ref}")
        print(f"  canonical_kind: {fact.canonical_kind}")
        print(f"  review_status:  {fact.review_status}")
        print(f"  evidence_rows:  {len(plan.evidence)}")
        print(f"  payload:        {fact.payload_json}")
        for evidence in plan.evidence:
            print(
                "  source:         "
                f"{evidence.source_type}:{evidence.source_name} "
                f"revision={evidence.source_revision or '<none>'}"
            )
        print()

    print("BOUNDARY")
    print("Review decisions authorize planning only. This command does not write data/eso.db.")
    print("Human review does not count as a second evidence source or create corroboration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
