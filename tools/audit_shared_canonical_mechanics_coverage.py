from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.canonical_mechanics_coverage_audit import (
    CanonicalMechanicsCoverageAuditService,
    CanonicalMechanicsCoverageStatus,
)
from services.canonical_mechanics_coverage_inventory import (
    shared_canonical_mechanics_inventory,
)


def _heading(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> int:
    report = CanonicalMechanicsCoverageAuditService().audit(
        shared_canonical_mechanics_inventory()
    )

    print("SHARED CANONICAL MECHANICS COVERAGE AUDIT")
    print("Comp Maker + Rotation Maker + Optimizer")

    for status in CanonicalMechanicsCoverageStatus:
        rows = report.by_status(status)
        if not rows:
            continue
        _heading(f"{status.value.replace('_', ' ').upper()} ({len(rows)})")
        for row in rows:
            print(f"[{row.domain.value}] {row.key}")
            print(f"  Knows:   {row.capability}")
            print(f"  Source:  {row.evidence_source}")
            print(f"  Helps:   {', '.join(row.consumers)}")
            if row.missing_evidence:
                print(f"  Missing: {row.missing_evidence}")
            if row.research_context:
                print(f"  Context: {row.research_context}")
            print()

    _heading(f"RESEARCH QUEUE ({len(report.knowledge_gaps)})")
    for index, gap in enumerate(report.knowledge_gaps, start=1):
        print(f"{index:02d}. [{gap.domain.value}] {gap.key}")
        print(f"    Why:       {gap.summary}")
        print(f"    Bring back:{' ' if gap.needed_evidence else ''}{gap.needed_evidence}")
        print(f"    Helps:     {', '.join(gap.consumers)}")
        print(f"    Context:   {gap.source_context}")
        print()

    for consumer in ("comp_maker", "rotation_maker", "optimizer"):
        gaps = report.gaps_for(consumer)
        _heading(f"{consumer.upper()} RESEARCH ({len(gaps)})")
        for gap in gaps:
            print(f"- {gap.key}: {gap.needed_evidence}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
