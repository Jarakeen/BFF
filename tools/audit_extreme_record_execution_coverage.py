from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_record_execution_catalog_service import (
    ExtremeRecordExecutionCatalogService,
    ExtremeRecordExecutionStatus,
)
from services.extreme_specialized_execution_service import (
    ExtremeSpecializedExecutionService,
)


def main() -> int:
    rows = ExtremeRecordExecutionCatalogService.descriptors()
    status_counts = Counter(row.status.value for row in rows)
    family_counts = Counter(row.execution_family for row in rows)
    direct_specialized = tuple(
        row.objective.key
        for row in rows
        if row.status is ExtremeRecordExecutionStatus.SPECIALIZED
        and ExtremeSpecializedExecutionService.can_execute_without_extra_inputs(
            row.objective.key
        )
    )
    direct_specialized_saved_build = tuple(
        key
        for key in direct_specialized
        if ExtremeSpecializedExecutionService.requires_saved_build(key)
    )
    direct_specialized_scratch = tuple(
        key
        for key in direct_specialized
        if not ExtremeSpecializedExecutionService.requires_saved_build(key)
    )

    print("EXTREME RECORD EXECUTION COVERAGE")
    print(f"canonical_record_count={len(rows)}")
    for status in ExtremeRecordExecutionStatus:
        print(f"{status.value}_count={status_counts[status.value]}")
    print(f"direct_specialized_count={len(direct_specialized)}")
    print(f"direct_specialized_records={direct_specialized}")
    print(f"direct_specialized_saved_build_records={direct_specialized_saved_build}")
    print(f"direct_specialized_scratch_records={direct_specialized_scratch}")
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
    specialized_families = tuple(
        sorted(
            {
                row.execution_family
                for row in rows
                if row.status is ExtremeRecordExecutionStatus.SPECIALIZED
            }
        )
    )
    print()
    print(f"pending_execution_family_count={len(pending_families)}")
    print(f"pending_execution_families={pending_families}")
    print(f"specialized_execution_family_count={len(specialized_families)}")
    print(f"specialized_execution_families={specialized_families}")
    if pending_families:
        print(
            "NEXT_STEP=close shared execution families, not individual record clones; "
            "then route the canonical catalog through the Extreme Build Lab UI"
        )
    elif specialized_families:
        print(
            "NEXT_STEP=route specialized execution families through the Extreme Build Lab UI; "
            "preserve family-specific scenario inputs and unresolved source evidence"
        )
    else:
        print("NEXT_STEP=run final Extreme UI and proof closeout gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
