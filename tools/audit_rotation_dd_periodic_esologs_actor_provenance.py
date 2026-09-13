from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_dd_periodic_esologs_actor_provenance_service import (
    RotationDDPeriodicEsoLogsActorProvenanceService,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize imported ESO Logs actor provenance for one observed ability ID "
            "without inferring pet/summon ownership."
        )
    )
    parser.add_argument("--ability-id", type=int, required=True)
    parser.add_argument("--logs-db", type=Path, required=True)
    parser.add_argument("--max-actors", type=int, default=20)
    args = parser.parse_args(argv)

    report = RotationDDPeriodicEsoLogsActorProvenanceService(args.logs_db).inspect(
        args.ability_id
    )

    print()
    print("===============================================")
    print(" DD PERIODIC ESO LOGS ACTOR PROVENANCE")
    print("===============================================")
    print(f"Ability id: {report.ability_id}")
    print(f"Events: {report.event_count}")
    print(f"Distinct source actor ids: {report.source_actor_count}")
    print(f"Source actors matched to log_actor metadata: {report.matched_actor_count}")

    for index, row in enumerate(report.rows[: max(0, int(args.max_actors))], start=1):
        print()
        print(
            f"  [{index}] actor_id={row.actor_id} events={row.event_count} "
            f"report/fight groups={row.report_fight_groups}"
        )
        print(
            "      metadata: "
            f"name={row.name or '(none)'} | display={row.display_name or '(none)'} | "
            f"type={row.actor_type or '(none)'} | role={row.role or '(none)'}"
        )
        if row.owner_hints:
            print("      owner-like raw metadata:")
            for hint in row.owner_hints:
                print(f"        - {hint}")

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — actor metadata is reported exactly as imported; "
        "no pet/summon ownership is inferred when the source data does not expose it."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
