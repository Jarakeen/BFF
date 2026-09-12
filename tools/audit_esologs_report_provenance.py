from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.esologs_report_provenance_service import EsoLogsReportProvenanceService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect stored and raw-source ESO Logs report provenance without modifying the database."
    )
    parser.add_argument("--db", required=True, type=Path, help="ESO Logs runtime SQLite database")
    args = parser.parse_args()

    reports = EsoLogsReportProvenanceService(args.db).inspect()
    print("====================================")
    print(" ESO LOGS REPORT PROVENANCE AUDIT")
    print("====================================")
    print(f"Reports: {len(reports)}")

    for report in reports:
        print()
        print(f"[{report.report_code}]")
        print(f"  fetched_at: {report.fetched_at or 'unavailable'}")
        print(f"  source_url: {report.source_url or 'unavailable'}")
        print(f"  source_file: {report.source_file or 'unavailable'}")
        print(f"  source_file_exists: {'yes' if report.source_file_exists else 'no'}")
        print(
            "  stored report keys: "
            + (", ".join(report.stored_report_keys) if report.stored_report_keys else "none")
        )
        print(
            "  source report keys: "
            + (", ".join(report.source_report_keys) if report.source_report_keys else "none")
        )
        if report.provenance_values:
            print("  provenance values:")
            for key, value in report.provenance_values:
                print(f"    {key}: {value}")
        else:
            print("  provenance values: none")
        for message in report.unresolved:
            print(f"  unresolved: {message}")

    print()
    print(
        "Result: PROVENANCE ONLY — fetch time, filenames, fight-relative timestamps, and ability behavior "
        "are never converted into an ESO update/version unless the source explicitly records it."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
