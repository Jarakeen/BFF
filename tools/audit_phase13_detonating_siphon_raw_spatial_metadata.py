from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.rotation_dd_periodic_esologs_raw_spatial_metadata_service import (
    RotationDDPeriodicEsoLogsRawSpatialMetadataService,
)
from tools.discover_esologs_runtime_db import discover


DETONATING_SIPHON_PERIODIC_EVIDENCE_ID = 118766


def _resolve_logs_database(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)

    roots = (
        get_data_dir(),
        ROOT / "data",
        ROOT / "user_data",
        ROOT / "research",
    )
    matches = discover(roots=roots)
    if not matches:
        raise ValueError(
            "no ESO Logs runtime database found under configured data, data/, user_data/, "
            "or research/; pass --logs-db explicitly"
        )
    if len(matches) > 1:
        rendered = "; ".join(str(path) for path in matches)
        raise ValueError(
            "multiple ESO Logs runtime databases found; pass --logs-db explicitly: "
            + rendered
        )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit of spatial/range-like metadata preserved in raw ESO Logs "
            "events for Detonating Siphon's reviewed periodic evidence id."
        )
    )
    parser.add_argument(
        "--logs-db",
        help=(
            "Optional imported ESO Logs SQLite corpus containing log_event.raw_json. "
            "When omitted, the existing runtime DB discovery helper scans the normal "
            "project data locations."
        ),
    )
    parser.add_argument(
        "--ability-id",
        type=int,
        default=DETONATING_SIPHON_PERIODIC_EVIDENCE_ID,
        help=(
            "Observed ESO Logs ability id to inspect. Defaults to 118766, the reviewed "
            "Detonating Siphon periodic candidate."
        ),
    )
    parser.add_argument("--max-values", type=int, default=12)
    args = parser.parse_args()

    try:
        logs_database = _resolve_logs_database(args.logs_db)
    except ValueError as exc:
        print(f"ESO Logs database resolution error: {exc}")
        return 2

    report = RotationDDPeriodicEsoLogsRawSpatialMetadataService(
        logs_database
    ).inspect(
        args.ability_id,
        max_values_per_field=max(1, int(args.max_values)),
    )

    print("=" * 64)
    print(" DETONATING SIPHON RAW SPATIAL METADATA AUDIT")
    print("=" * 64)
    print(f"Database: {logs_database}")
    print(f"Ability id: {report.ability_id}")
    print(f"Events: {report.event_count}")
    print(f"Distinct report/fight/target actors: {report.target_actor_count}")

    if report.fields:
        print("\nPotential spatial fields:")
        for field in report.fields:
            print(f"- {field.path} ({field.occurrence_count} occurrences)")
            for value in field.rendered_values:
                print(f"    {value}")
    else:
        print("\nPotential spatial fields: none")

    if report.unresolved:
        print("\nUnresolved:")
        for message in report.unresolved:
            print(f"- {message}")

    print("\nInterpretation rule:")
    print(
        "Matching field names are discovery evidence only. Do not promote them to "
        "coordinates, distances, or hitbox geometry until their semantics are reviewed."
    )
    return 0 if not report.unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
