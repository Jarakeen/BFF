from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_reviewed_coverage_service import (
    RotationDDPeriodicEsoLogsReviewedCoverageService,
)


def audit(*, database_path: Path, logs_database_path: Path) -> int:
    if not database_path.is_file():
        print(f"Canonical database file not found: {database_path}")
        return 1
    if not logs_database_path.is_file():
        print(f"ESO Logs SQLite file not found: {logs_database_path}")
        return 2

    report = RotationDDPeriodicEsoLogsReviewedCoverageService(
        canonical_database_path=database_path,
        logs_database_path=logs_database_path,
    ).inspect()

    print()
    print("===============================================")
    print(" DD PERIODIC ESO LOGS REVIEWED CORPUS COVERAGE")
    print("===============================================")
    print(f"Reviewed skills: {len(report.rows)}")
    print(f"Observed reviewed skills: {len(report.observed_rows)}")

    for row in report.rows:
        state = "OBSERVED" if row.observed else "ABSENT"
        print()
        print(f"[{state}] {row.skill_entity_id}")
        print(f"  reviewed components: {row.component_count}")
        print(f"  cast observations: {row.cast_count}")
        print(f"  secondary candidates: {row.candidate_count}")
        print(f"  executable reviewed components: {row.executable_component_count}")
        print(
            "  unresolved executable fields: "
            + (", ".join(row.unresolved_executable_fields) or "none")
        )
        for message in row.evidence_unresolved:
            print(f"  evidence note: {message}")

    print()
    if report.observed_rows:
        print("Result: use observed reviewed skills as the next evidence-review candidates.")
    else:
        print("Result: this corpus contains no matching casts for the reviewed DD periodic skills.")
    print("No executable runtime semantics are promoted by this audit.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report which reviewed DD periodic skills have matching cast observations "
            "in an imported ESO Logs SQLite corpus."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(DEFAULT_DATABASE),
        help="Canonical ESO SQLite database for skill identity/crosswalks",
    )
    parser.add_argument(
        "--logs-db",
        type=Path,
        required=True,
        help="SQLite database containing imported ESO Logs log_event rows",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return audit(database_path=args.database, logs_database_path=args.logs_db)


if __name__ == "__main__":
    raise SystemExit(main())
