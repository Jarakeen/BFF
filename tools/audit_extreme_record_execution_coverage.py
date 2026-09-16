from __future__ import annotations

from collections import Counter

from services.extreme_record_execution_catalog_service import (
    ExtremeRecordExecutionCatalogService,
    ExtremeRecordExecutionStatus,
)


def main() -> int:
    rows = ExtremeRecordExecutionCatalogService.descriptors()
    status_counts = Counter(row.status.value for row in rows)
    family_counts = Counter(row.execution_family for row in rows)

    print("EXTREME RECORD EXECUTION COVERAGE")
    print(f"canonical_record_count={len(rows)}")
    for status in ExtremeRecordExecutionStatus:
        print(f"{status.value}_count={status_counts[status.value]}")
    print()
    print("EXECUTION FAMILIES")
    for family, count in sorted(family_counts.items()):
        print(f"  {family}: {count}")
    print()
    for row in rows:
        print(
            f"[{row.status.value.upper():11}] {row.objective.label} "
            f"key={row.objective.key} family={row.execution_family}"
        )
        print(f"  {row.evidence}")

    pending_families = tuple(
        sorted(
            {
                row.execution_family
                for row in rows
                if row.status is ExtremeRecordExecutionStatus.PENDING
            }
        )
    )
    print()
    print(f"pending_execution_family_count={len(pending_families)}")
    print(f"pending_execution_families={pending_families}")
    print(
        "NEXT_STEP=close shared execution families, not individual record clones; "
        "then route the canonical catalog through the Extreme Build Lab UI"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
