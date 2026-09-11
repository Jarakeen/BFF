from __future__ import annotations

"""Inspect read-only ESO Logs candidate evidence for Minor Lifesteal runtime rules."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_healer_minor_lifesteal_esologs_evidence_service import (
    RotationHealerMinorLifestealEsoLogsEvidenceService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Discover candidate Minor Lifesteal heal aliases, ownership, preceding "
            "damage, and observed cadence without promoting runtime mechanics."
        )
    )
    parser.add_argument("--database", type=Path, default=Path("data/eso.db"))
    parser.add_argument("--report-code")
    parser.add_argument("--fight-id", type=int)
    parser.add_argument(
        "--timestamp-unit",
        choices=("milliseconds", "seconds"),
        default="milliseconds",
    )
    parser.add_argument(
        "--heal-ability-id",
        action="append",
        type=int,
        default=[],
        help="Observational ESO Logs heal alias; repeat for multiple ids.",
    )
    parser.add_argument(
        "--max-observations",
        type=int,
        default=50,
        help="Maximum detailed heal rows printed in text mode; collection remains complete.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_observations < 0:
        raise SystemExit("--max-observations must be non-negative")

    report = RotationHealerMinorLifestealEsoLogsEvidenceService().inspect(
        args.database,
        report_code=args.report_code,
        fight_id=args.fight_id,
        timestamp_unit=args.timestamp_unit,
        observed_heal_ability_ids=tuple(args.heal_ability_id),
    )

    if args.as_json:
        print(json.dumps(report.to_candidate_fixture_payload(), indent=2))
        return 0

    print("=" * 104)
    print("PHASE 13 MINOR LIFESTEAL ESO LOGS RUNTIME EVIDENCE DISCOVERY")
    print("=" * 104)
    print(f"Database: {report.source_path}")
    print(f"Evidence status: {report.evidence_status.upper()} — human review required")
    print(f"Timestamp unit: {report.timestamp_unit}")
    print(f"Observed heal events: {len(report.observations)}")
    aliases = ", ".join(str(value) for value in report.observed_heal_ability_aliases)
    print(f"Observed heal ability aliases: {aliases or '(none)'}")

    print("\nCADENCE STREAMS")
    print("-" * 104)
    if not report.cadence_streams:
        print("(none)")
    for stream in report.cadence_streams:
        intervals = ", ".join(
            f"{value:g}s" for value in stream.observed_intervals_seconds
        )
        print(
            f"{stream.report_code} fight {stream.fight_id} | "
            f"source={stream.source_id} target={stream.target_id} "
            f"relation={stream.source_target_relation} | "
            f"heals={stream.heal_event_count} | "
            f"intervals={intervals or '(single observation)'}"
        )

    print("\nHEAL OBSERVATIONS")
    print("-" * 104)
    if not report.observations:
        print("(none)")
    displayed = report.observations[: args.max_observations]
    for item in displayed:
        delta = (
            f"{item.previous_same_source_damage_delta_seconds:g}s"
            if item.previous_same_source_damage_delta_seconds is not None
            else "(none)"
        )
        print(
            f"{item.report_code} fight {item.fight_id} event {item.event_index} | "
            f"t={item.timestamp_seconds:g}s ability={item.ability_game_id} "
            f"source={item.source_id} target={item.target_id} "
            f"relation={item.source_target_relation} amount={item.amount} "
            f"overheal={item.overheal} | prior same-source damage "
            f"event={item.previous_same_source_damage_event_index} "
            f"target={item.previous_same_source_damage_target_id} delta={delta}"
        )
    omitted = len(report.observations) - len(displayed)
    if omitted:
        print(
            f"... {omitted} additional observations collected but omitted from text output; "
            "use --json or report/fight filters for complete detail"
        )

    print("\nUNRESOLVED")
    print("-" * 104)
    if report.unresolved:
        for message in report.unresolved:
            print(f"- {message}")
    else:
        print("(none in extraction; candidate evidence is still not canonical mechanics)")

    print("\nBOUNDARY")
    print("-" * 104)
    print("- Numeric ability ids remain observational aliases, not semantic identity.")
    print("- Observed intervals are evidence samples, not an inferred cooldown.")
    print("- A preceding damage event is correlation evidence, not automatic trigger proof.")
    print("- This command opens the database read-only and performs no imports or writes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
