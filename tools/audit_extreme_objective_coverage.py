from __future__ import annotations

"""Print the source-readiness matrix for current Extreme Build objectives."""

from collections import Counter
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.extreme_objective_coverage_service import ExtremeObjectiveCoverageService


def main() -> int:
    matrix = ExtremeObjectiveCoverageService.reviewed_matrix()

    print("EXTREME OBJECTIVE SOURCE COVERAGE AUDIT")
    print("Mode:       READ ONLY")
    print("Boundary:   coverage/readiness only; no ESO values are inferred here")
    print()

    for coverage in matrix:
        print(f"{coverage.objective_key}")
        print(f"  claim:              {coverage.claim.value}")
        print(f"  global max ready:   {'yes' if coverage.global_maximum_ready else 'no'}")
        print(
            f"  source universe:    {'reviewed' if coverage.source_universe_reviewed else 'not fully reviewed'}"
        )
        for source in coverage.sources:
            print(f"  - {source.source_family}: {source.status.value}")
        blockers = ", ".join(source.source_family for source in coverage.blocking_sources)
        print(f"  blockers:           {blockers or 'none'}")
        print()

    claims = Counter(row.claim.value for row in matrix)
    print("SUMMARY")
    print(f"Objectives audited:                   {len(matrix)}")
    print(
        "Global-maximum-ready objectives:     "
        f"{sum(row.global_maximum_ready for row in matrix)}"
    )
    for claim, count in sorted(claims.items()):
        print(f"{claim}: {count}")
    print()
    print("BOUNDARY")
    print(
        "A largest generated candidate is not a global maximum while known source "
        "families remain partial, context-only, unreviewed, or unmodeled."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
