from __future__ import annotations

"""Audit exhaustive H1 package admission for special gear families."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from services.extreme_actual_heal_package_admission_denominator_service import (
    ExtremeActualHealPackageAdmissionDenominatorService,
)


def main() -> int:
    database = get_data_dir() / "eso.db"
    report = ExtremeActualHealPackageAdmissionDenominatorService(database).build()

    print("EXTREME E2 H1 SPECIAL PACKAGE ADMISSION DENOMINATOR")
    print(f"database={database}")
    print(f"family_count={len(report.families)}")
    print(f"missing_count={len(report.missing)}")
    print(f"unexpected_count={len(report.unexpected)}")
    print(f"package_admission_denominator_proven={report.denominator_proven}")

    for row in report.families:
        print()
        print(f"[{row.family.upper()}]")
        print(f"expected_count={len(row.expected)}")
        print(f"admitted_count={len(row.admitted)}")
        print(f"missing_count={len(row.missing)}")
        print(f"unexpected_count={len(row.unexpected)}")
        for name in row.missing:
            print(f"MISSING {name}")
        for name in row.unexpected:
            print(f"UNEXPECTED {name}")

    print()
    print(
        "NOTE=Purely conditional special-set rows remain owned by explicit "
        "runtime/proc scenario evidence and are not required in standing package admission."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
