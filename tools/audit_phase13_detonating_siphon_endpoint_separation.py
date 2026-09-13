from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.rotation_detonating_siphon_esologs_endpoint_separation_service import (
    RotationDetonatingSiphonEndpointSeparationService,
)
from tools.audit_phase13_detonating_siphon_esologs_spatial_topology import (
    CANDIDATE_ABILITY_ID,
    _cast_ability_ids,
    _logs_database,
)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Detonating Siphon endpoint-separation audit. Stratifies ESO Logs "
            "hits by caster/cast-target candidate separation so overlapping endpoint "
            "circles do not hide discriminating observations."
        )
    )
    parser.add_argument("--logs-db", help="Optional explicit imported ESO Logs SQLite corpus")
    parser.add_argument(
        "--canonical-db",
        default=str(get_data_dir() / "eso.db"),
        help="Canonical BFF ESO database used only to resolve Siphon cast aliases.",
    )
    parser.add_argument("--candidate-ability-id", type=int, default=CANDIDATE_ABILITY_ID)
    parser.add_argument("--endpoint-radius", type=float, default=5.0)
    parser.add_argument(
        "--minimum-separation",
        dest="minimum_separations",
        action="append",
        type=float,
        help="Minimum normalized caster/cast-target separation. Repeat for custom thresholds.",
    )
    args = parser.parse_args()

    thresholds = tuple(args.minimum_separations or (5.0, 10.0, 15.0, 20.0))
    try:
        logs_db = _logs_database(args.logs_db)
        canonical_db = Path(args.canonical_db)
        cast_ids = _cast_ability_ids(canonical_db)
        report = RotationDetonatingSiphonEndpointSeparationService(logs_db).inspect(
            cast_ability_ids=cast_ids,
            candidate_ability_id=args.candidate_ability_id,
            endpoint_radius=args.endpoint_radius,
            minimum_separations=thresholds,
        )
    except (RuntimeError, FileNotFoundError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print("=" * 72)
    print(" DETONATING SIPHON ESO LOGS ENDPOINT SEPARATION")
    print("=" * 72)
    print(f"Logs database: {logs_db}")
    print(f"Canonical database: {canonical_db}")
    print(f"Cast ability ids: {', '.join(map(str, cast_ids))}")
    print(f"Candidate ability id: {report.candidate_ability_id}")
    print(f"Endpoint comparison radius: {args.endpoint_radius:g} normalized coordinate units")
    print()
    print(f"Casts with endpoint positions: {report.cast_count_with_positions}")
    print(f"Linked candidate events: {report.linked_event_count}")
    print(f"Median caster <-> cast-target separation: {_fmt(report.median_endpoint_separation)}")
    print(f"P90 caster <-> cast-target separation: {_fmt(report.separation_p90)}")
    print(f"Maximum caster <-> cast-target separation: {_fmt(report.maximum_endpoint_separation)}")

    for item in report.thresholds:
        print()
        print(f"At separation >= {item.minimum_separation:g}:")
        print(f"- casts: {item.cast_count}")
        print(f"- linked events: {item.linked_event_count}")
        print(f"- events with positions: {item.events_with_positions}")
        print(f"- caster-only hits: {item.caster_only_count}")
        print(f"- cast-target-only hits: {item.cast_target_only_count}")
        print(f"- inside both endpoint circles: {item.within_both_count}")
        print(f"- beyond both endpoint circles: {item.beyond_both_count}")
        print(
            "- beyond-both median distance to segment: "
            + _fmt(item.median_target_to_segment_distance_for_beyond_both)
        )
        print(
            "- beyond-both maximum distance to segment: "
            + _fmt(item.maximum_target_to_segment_distance_for_beyond_both)
        )

    if report.unresolved:
        print("\nUnresolved:")
        for message in report.unresolved:
            print(f"- {message}")

    print("\nInterpretation guardrails:")
    print("- x/y are ESO Logs actor positions normalized from documented 100x storage.")
    print("- normalized coordinate units are not assumed to be meters.")
    print("- the cast target remains a corpse-anchor candidate, not proven corpse identity.")
    print("- separated casts can discriminate endpoint hypotheses; hit observations still do not prove a boundary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
