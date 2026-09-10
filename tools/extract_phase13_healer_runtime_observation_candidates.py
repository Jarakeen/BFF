from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.rotation_healer_esologs_observation_extractor import (
    RotationHealerEsoLogsObservationExtractor,
    RotationHealerEsoLogsTimestampUnit,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract candidate healer HoT activation/tick observations from a raw "
            "ESO Logs JSON fight. Output remains candidate evidence until reviewed."
        )
    )
    parser.add_argument("--raw", required=True, help="raw ESO Logs JSON export")
    parser.add_argument("--fight-id", required=True, type=int, help="fight id inside the raw export")
    parser.add_argument("--caster-id", required=True, type=int, help="ESO Logs sourceID for the healer")
    parser.add_argument("--out", required=True, help="candidate observation JSON output path")
    parser.add_argument("--db", default="data/eso.db", help="canonical ESO database path")
    parser.add_argument(
        "--timestamp-unit",
        choices=[item.value for item in RotationHealerEsoLogsTimestampUnit],
        default=RotationHealerEsoLogsTimestampUnit.MILLISECONDS.value,
        help="raw event timestamp unit (default: milliseconds)",
    )
    parser.add_argument("--game-version", default="U50", help="game-version label stored in candidate evidence")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = RotationHealerEsoLogsObservationExtractor(Path(args.db)).extract(
        Path(args.raw),
        fight_id=args.fight_id,
        caster_id=args.caster_id,
        timestamp_unit=args.timestamp_unit,
        game_version=args.game_version,
    )
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            report.to_candidate_fixture_payload(game_version=args.game_version),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("================================================================")
    print(" PHASE 13 HEALER ESO LOGS OBSERVATION CANDIDATE EXTRACTION")
    print("================================================================")
    print(f"Raw export:      {report.source_path}")
    print(f"Report / fight:  {report.report_code} / {report.fight_id}")
    print(f"Caster sourceID: {report.caster_id}")
    print(f"Timestamp unit:  {report.timestamp_unit.value}")
    print(f"Candidates:      {len(report.candidates)}")
    print(f"Output:          {output_path}")
    print("Review status:   candidate")
    print()
    for candidate in report.candidates:
        sample = candidate.sample
        print(
            f"- {sample.source_name} coefficient {sample.coefficient_number}: "
            f"activation={sample.activation_time_seconds:g}s "
            f"unique_ticks={len(sample.observed_tick_times_seconds)} "
            f"raw_heal_events={candidate.raw_periodic_heal_event_count}"
        )
    if report.unresolved:
        print()
        print("UNRESOLVED / SKIPPED")
        print("--------------------")
        for item in report.unresolved:
            print(f"- {item}")
    print()
    print(
        "Boundary: this output is candidate evidence only. Inspect the event pairing, "
        "then promote only explicitly approved samples with "
        "tools/review_phase13_healer_runtime_observations.py. Do not edit review_status "
        "in the candidate fixture by hand."
    )
    return 0 if report.candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
