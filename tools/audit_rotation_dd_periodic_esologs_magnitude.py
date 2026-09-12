from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_magnitude_observation_service import (
    RotationDDPeriodicEsoLogsMagnitudeObservationService,
)


def audit(
    *,
    skill: str,
    database: Path,
    logs_db: Path,
    periodic_id: int,
    minimum_occurrences: int,
    max_sequences: int,
) -> int:
    if not database.is_file():
        print(f"Canonical ESO database not found: {database}")
        return 1
    if not logs_db.is_file():
        print(f"ESO Logs database not found or is not a file: {logs_db}")
        return 2

    report = RotationDDPeriodicEsoLogsMagnitudeObservationService(
        canonical_database_path=database,
        logs_database_path=logs_db,
    ).inspect(
        skill,
        periodic_ability_id=periodic_id,
        minimum_occurrences=minimum_occurrences,
    )

    print()
    print("=============================================")
    print(" DD PERIODIC ESO LOGS MAGNITUDE OBSERVATION")
    print("=============================================")
    print(f"Skill: {report.skill_entity_id or skill}")
    print(f"Periodic evidence ID: {report.periodic_ability_id}")
    print(f"Cast anchors: {report.cast_anchor_count}")
    print(f"Same-target/same-hit-type sequences: {len(report.sequences)}")
    print(f"Constant amount sequences: {report.constant_sequence_count}")
    print(f"Varying amount sequences:  {report.varying_sequence_count}")

    ranked = sorted(
        report.sequences,
        key=lambda item: (-len(item.amounts), item.report_code, item.fight_id, item.cast_track_id),
    )
    for index, item in enumerate(ranked[: max(0, int(max_sequences))], start=1):
        pairs = ", ".join(
            f"{offset:.3f}s={amount:g}"
            for offset, amount in zip(item.offsets_seconds, item.amounts)
        )
        print()
        print(
            f"  [{index}] report={item.report_code} fight={item.fight_id} "
            f"source={item.source_id} target={item.target_id} track={item.cast_track_id} "
            f"hit_type={item.hit_type}"
        )
        print(f"      occurrences: {len(item.amounts)}")
        print(f"      distinct amounts: {item.distinct_amount_count}")
        print(f"      amount sequence: {pairs}")

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for item in report.unresolved:
            print(f"  - {item}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — constant or varying tick amounts do not by "
        "themselves prove snapshot_at_cast or dynamic_at_tick. Target, hit type, "
        "buffs, debuffs, and mitigation must still be reviewed."
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect same-cast, same-target, same-hit-type periodic damage amounts "
            "as non-executable ESO Logs magnitude evidence."
        )
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--periodic-id", type=int, required=True)
    parser.add_argument("--minimum-occurrences", type=int, default=3)
    parser.add_argument("--max-sequences", type=int, default=12)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--logs-db", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return audit(
        skill=args.skill,
        database=args.database,
        logs_db=args.logs_db,
        periodic_id=args.periodic_id,
        minimum_occurrences=args.minimum_occurrences,
        max_sequences=args.max_sequences,
    )


if __name__ == "__main__":
    raise SystemExit(main())
