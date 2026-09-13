from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.rotation_meteor_esologs_candidate_drilldown_service import (
    RotationMeteorEsoLogsCandidateDrilldownService,
)
from tools.discover_esologs_runtime_db import discover


_DEFAULT_IDS = (121090, 119169, 26879)


def _resolve_logs_database(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    candidates = discover(
        roots=(
            Path(get_data_dir()),
            ROOT / "data",
            ROOT / "user_data",
            ROOT / "research",
        )
    )
    if not candidates:
        print("No ESO Logs runtime database discovered. Use --logs-db to specify one.")
        return None
    preferred = [path for path in candidates if path.name == "eso_gear_customization_test.db"]
    if len(preferred) == 1:
        return preferred[0]
    if len(candidates) > 1:
        print("Multiple ESO Logs runtime databases discovered:")
        for path in candidates:
            print(f"- {path}")
        print("Use --logs-db to choose one explicitly.")
        return None
    return candidates[0]


def audit(logs_database_path: Path, *, ability_ids: tuple[int, ...]) -> int:
    report = RotationMeteorEsoLogsCandidateDrilldownService(logs_database_path).inspect(
        ability_ids=ability_ids,
    )

    print("=" * 76)
    print(" METEOR-LIKE ESO LOGS CANDIDATE TOPOLOGY DRILLDOWN")
    print("=" * 76)
    print(f"Database: {logs_database_path}")
    print("Candidate ids: " + ", ".join(str(value) for value in ability_ids))
    print()

    if not report.candidates:
        print("Candidates: none")
    for candidate in report.candidates:
        names = ", ".join(candidate.ability_names) or "(unnamed)"
        print(f"Candidate {candidate.ability_game_id} | {names}")
        print(f"- damage events: {candidate.damage_event_count}")
        print(f"- segmented runs: {candidate.run_count}")
        print(f"- source actors: {candidate.source_actor_count}")
        print(
            "- median run interval: "
            + (f"{candidate.median_run_interval_seconds:.4f}s" if candidate.median_run_interval_seconds is not None else "n/a")
        )
        print(
            "- median run span: "
            + (f"{candidate.median_run_span_seconds:.4f}s" if candidate.median_run_span_seconds is not None else "n/a")
        )
        print(f"- runs with prior cast in 6s: {candidate.runs_with_prior_cast}/{candidate.run_count}")
        print(f"- runs with same-track prior cast: {candidate.runs_with_same_track_prior_cast}/{candidate.run_count}")
        print("- nearest prior cast ids:")
        if candidate.nearest_prior_cast_id_counts:
            for ability_id, count in candidate.nearest_prior_cast_id_counts:
                print(f"  - {ability_id if ability_id is not None else 'none'}: {count}")
        else:
            print("  - none")
        print("- nearest prior cast names:")
        if candidate.nearest_prior_cast_name_counts:
            for name, count in candidate.nearest_prior_cast_name_counts:
                print(f"  - {name}: {count}")
        else:
            print("  - none")
        print("- runs:")
        for index, run in enumerate(candidate.runs, start=1):
            span = (run.end_timestamp - run.start_timestamp) / 1000.0
            interval = f"{run.median_interval_seconds:.4f}s" if run.median_interval_seconds is not None else "n/a"
            tracks = ",".join(str(value) for value in run.cast_track_ids) or "none"
            print(
                f"  {index}. report={run.report_code} fight={run.fight_id} source={run.source_id} "
                f"events={run.damage_event_count} targets={run.distinct_target_count} "
                f"span={span:.4f}s interval={interval} damage_tracks={tracks}"
            )
            for cast in run.nearby_casts:
                print(
                    f"     prior {cast.offset_seconds:.3f}s | id={cast.ability_game_id if cast.ability_game_id is not None else 'none'} "
                    f"| {cast.ability_name or '(unnamed)'} | type={cast.event_type or '(blank)'} "
                    f"| track={cast.cast_track_id if cast.cast_track_id is not None else 'none'} "
                    f"| same-track={'yes' if cast.shares_damage_cast_track else 'no'}"
                )
        print()

    if report.unresolved:
        print("Unresolved:")
        for message in report.unresolved:
            print(f"- {message}")
        print()

    print("Interpretation guardrails:")
    print("- run segmentation is observational and uses a >2.25s gap boundary")
    print("- a nearby or same-track cast is identity evidence, not automatic proof")
    print("- candidate ids are ESO Logs handles and are never promoted by this audit")
    print("- occurrence counts from the anonymous scanner were timestamps, not cast counts")
    return 0 if report.candidates else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Drill into anonymous Meteor-like ESO Logs timing candidates."
    )
    parser.add_argument("--logs-db", type=Path)
    parser.add_argument(
        "--ability-id",
        type=int,
        action="append",
        dest="ability_ids",
        help="Candidate ability id. Repeatable. Defaults to 121090, 119169, and 26879.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logs_db = _resolve_logs_database(args.logs_db)
    if logs_db is None:
        return 2
    ability_ids = tuple(args.ability_ids) if args.ability_ids else _DEFAULT_IDS
    return audit(logs_db, ability_ids=ability_ids)


if __name__ == "__main__":
    raise SystemExit(main())
