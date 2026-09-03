from __future__ import annotations

"""Read-only audit of timeline-capable facts in encounter evidence packets."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_evidence import ReconciledEncounterFact, reconcile_encounter_evidence
from services.encounter_evidence_packet import load_encounter_evidence_packet


DEFAULT_EVIDENCE_ROOT = Path("data/encounter_evidence")
TIMELINE_FACT_TYPES = {"phase", "transition"}
THRESHOLD_KEYS = {"threshold", "thresholds", "health_threshold", "health_thresholds"}
EXACT_TIME_KEYS = {"time", "time_seconds", "timestamp", "exact_time_seconds"}
APPROX_TIME_KEYS = {"approx_time", "approx_time_seconds", "timing_window", "timing_window_seconds"}
REPEAT_KEYS = {"repeat_interval", "repeat_interval_seconds", "interval", "interval_seconds"}
ORDER_KEYS = {"after", "before", "after_event", "before_event", "ordering"}


@dataclass(frozen=True)
class TimelineEvidenceRow:
    packet_name: str
    encounter_id: str
    encounter_name: str
    fact_type: str
    fact_key: str
    reconciliation_status: str
    trigger_kind: str
    distinct_sources: int
    value: Any | None


def _value_keys(value: Any) -> set[str]:
    if not isinstance(value, dict):
        return set()
    return {str(key).strip().casefold() for key in value}


def timeline_trigger_kind(fact: ReconciledEncounterFact) -> str | None:
    fact_type = fact.fact_type.strip().casefold()
    if fact_type not in TIMELINE_FACT_TYPES:
        return None
    if fact.status == "conflicting":
        return "conflicting"
    if fact_type == "phase":
        return "phase"

    keys = _value_keys(fact.value)
    if keys & THRESHOLD_KEYS:
        return "health_threshold"
    if keys & EXACT_TIME_KEYS:
        return "exact_time"
    if keys & APPROX_TIME_KEYS:
        return "approx_time"
    if keys & REPEAT_KEYS:
        return "repeat_interval"
    if keys & ORDER_KEYS:
        return "ordered"
    return "unresolved_trigger"


def audit_timeline_evidence(root: Path) -> list[TimelineEvidenceRow]:
    rows: list[TimelineEvidenceRow] = []
    for path in sorted(Path(root).glob("*.json")):
        packet = load_encounter_evidence_packet(path)
        facts = reconcile_encounter_evidence(packet.evidence)
        for fact in facts:
            trigger_kind = timeline_trigger_kind(fact)
            if trigger_kind is None:
                continue
            rows.append(
                TimelineEvidenceRow(
                    packet_name=path.name,
                    encounter_id=fact.encounter_id,
                    encounter_name=packet.encounter_name,
                    fact_type=fact.fact_type,
                    fact_key=fact.fact_key,
                    reconciliation_status=fact.status,
                    trigger_kind=trigger_kind,
                    distinct_sources=fact.distinct_sources,
                    value=fact.value,
                )
            )
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit phase/transition evidence that could feed encounter timelines"
    )
    parser.add_argument(
        "--evidence-root",
        default=str(DEFAULT_EVIDENCE_ROOT),
        help="Directory containing encounter evidence packet JSON files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Detailed candidate rows to print; 0 means all",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = Path(args.evidence_root)
    if not root.is_dir():
        parser.error(f"encounter evidence directory does not exist: {root}")

    rows = audit_timeline_evidence(root)
    packet_count = len(list(root.glob("*.json")))
    encounter_count = len({row.encounter_id for row in rows})

    print("=" * 76)
    print(" ENCOUNTER TIMELINE EVIDENCE AUDIT - READ ONLY")
    print("=" * 76)
    print(f"evidence root:                   {root}")
    print(f"evidence packets:                {packet_count:6}")
    print(f"encounters with timeline facts:  {encounter_count:6}")
    print(f"phase/transition facts:          {len(rows):6}")
    for kind in (
        "health_threshold",
        "phase",
        "exact_time",
        "approx_time",
        "repeat_interval",
        "ordered",
        "unresolved_trigger",
        "conflicting",
    ):
        count = sum(1 for row in rows if row.trigger_kind == kind)
        print(f"{kind + ':':31} {count:6}")
    print()
    for status in ("corroborated", "single_source", "conflicting"):
        count = sum(1 for row in rows if row.reconciliation_status == status)
        print(f"{status + ':':31} {count:6}")

    print("\n=== TIMELINE CANDIDATES ===")
    limit = None if args.limit == 0 else max(args.limit, 0)
    shown = rows if limit is None else rows[:limit]
    for row in shown:
        print(
            f"  {row.encounter_name} [{row.encounter_id}] | "
            f"{row.fact_type}:{row.fact_key} | {row.trigger_kind} | "
            f"{row.reconciliation_status} | sources={row.distinct_sources}"
        )
    if limit is not None and len(rows) > len(shown):
        print(f"  ... {len(rows) - len(shown)} more")

    print("\nInterpretation:")
    print("  - threshold/phase rows can become reviewed timeline events after canonical promotion")
    print("  - conflicting rows must remain unresolved until reviewed; no source wins automatically")
    print("  - unresolved_trigger means the fact is timeline-related but its trigger semantics are not explicit")
    print("  - observed log timing should remain distinct from guide/source threshold semantics")
    print("\nNo database rows or evidence packets were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
