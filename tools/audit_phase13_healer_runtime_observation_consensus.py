from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.rotation_healer_periodic_observation_consensus_service import (
    RotationHealerPeriodicObservationConsensusService,
)
from services.rotation_healer_periodic_observation_fixture_service import (
    RotationHealerPeriodicObservationFixtureService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit conservative consensus across explicitly reviewed healer periodic-runtime "
            "observation samples. This command is read-only and does not promote evidence."
        )
    )
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=Path("data/eso.db"))
    parser.add_argument(
        "--first-tick-spread-tolerance",
        type=float,
        default=0.1,
        help="maximum reviewed first-tick offset spread allowed within one consensus group",
    )
    return parser


def consensus_report(
    observation_path: str | Path,
    *,
    database_path: str | Path,
    first_tick_spread_tolerance_seconds: float = 0.1,
):
    fixture = RotationHealerPeriodicObservationFixtureService(database_path).load(
        observation_path
    )
    grouped = defaultdict(list)
    for entry in fixture.entries:
        key = (
            entry.sample.source_name.casefold(),
            int(entry.sample.coefficient_number),
            entry.sample.game_version,
        )
        grouped[key].append(entry)

    service = RotationHealerPeriodicObservationConsensusService()
    resolutions = tuple(
        service.resolve(
            tuple(entries),
            first_tick_spread_tolerance_seconds=first_tick_spread_tolerance_seconds,
        )
        for _, entries in sorted(grouped.items(), key=lambda item: item[0])
    )
    return fixture, resolutions


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fixture, resolutions = consensus_report(
        args.observations,
        database_path=args.db,
        first_tick_spread_tolerance_seconds=args.first_tick_spread_tolerance,
    )

    print("=" * 76)
    print(" PHASE 13 HEALER RUNTIME OBSERVATION CONSENSUS AUDIT")
    print("=" * 76)
    print(f"Reviewed fixture: {args.observations}")
    print(f"Database:         {args.db}")
    print(f"Groups:           {len(resolutions)}")
    print(
        "First-tick spread tolerance: "
        f"{float(args.first_tick_spread_tolerance):g}s"
    )
    print("Boundary: read-only consensus audit; refresh/recast semantics are not inferred")
    print()

    for result in resolutions:
        version = result.game_version or "(unspecified)"
        print(
            f"{result.source_name} coefficient {result.coefficient_number} "
            f"[{version}] | samples={result.sample_count}"
        )
        if result.observation is not None:
            observed_range = result.first_tick_offset_range_seconds
            assert observed_range is not None
            print(
                "  first tick: "
                f"median=+{result.observation.first_tick_offset_seconds:g}s "
                f"range=+{observed_range[0]:g}s..+{observed_range[1]:g}s"
            )
            print(
                "  expiry boundary tick: "
                + ("yes" if result.observation.tick_on_expiry_boundary else "no")
            )
            print("  refresh/recast: unresolved")
            print("  consensus: READY")
        else:
            print("  consensus: UNRESOLVED")
        for message in result.unresolved:
            print(f"  - {message}")
        print()

    if fixture.unresolved:
        print("FIXTURE UNRESOLVED")
        print("-" * 20)
        for message in fixture.unresolved:
            print(f"- {message}")
        print()

    ready = bool(resolutions) and all(result.ready for result in resolutions)
    return 0 if ready and not fixture.unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
