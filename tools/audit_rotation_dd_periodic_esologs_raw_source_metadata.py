from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_dd_periodic_esologs_raw_source_metadata_service import (
    RotationDDPeriodicEsoLogsRawSourceMetadataService,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory source/owner/pet-like keys preserved in raw ESO Logs event JSON "
            "for one observed ability id."
        )
    )
    parser.add_argument("--ability-id", type=int, required=True)
    parser.add_argument("--logs-db", type=Path, required=True)
    parser.add_argument("--max-values", type=int, default=12)
    args = parser.parse_args(argv)

    report = RotationDDPeriodicEsoLogsRawSourceMetadataService(args.logs_db).inspect(
        args.ability_id,
        max_values_per_field=args.max_values,
    )

    print()
    print("====================================================")
    print(" DD PERIODIC ESO LOGS RAW SOURCE METADATA")
    print("====================================================")
    print(f"Ability id: {report.ability_id}")
    print(f"Events: {report.event_count}")
    print(f"Distinct report/fight/source actors: {report.source_actor_count}")
    print(f"Source-like raw fields: {len(report.fields)}")

    for index, field in enumerate(report.fields, start=1):
        print()
        print(f"  [{index}] {field.path}")
        print(f"      occurrences: {field.occurrence_count}")
        for value in field.rendered_values:
            print(f"      value: {value}")

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — raw event metadata is inventoried exactly as imported; "
        "field names or numeric values do not establish pet ownership by themselves."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
