from __future__ import annotations

"""Profile one Extreme max-resource published-record closure run.

The canonical static snapshot is warmed before profiling so the report isolates
candidate-search/scoring cost from the intentional one-time cost of loading immutable
ESO evidence. Ctrl+C still prints the partial profile, and ``--seconds`` can bound a
Windows profiling run automatically without changing the authoritative search path.
"""

import argparse
import cProfile
import io
from pathlib import Path
import pstats
import sys
from threading import Timer
from time import perf_counter
import _thread

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_resource_canonical_static_snapshot_service import (
    ExtremeResourceCanonicalStaticSnapshotService,
)
from services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service import (
    ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
)


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Profile the authoritative Extreme max-resource record search after warming "
            "the canonical static snapshot. Interrupting still prints hot spots."
        )
    )
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=_OBJECTIVES, default="max_magicka")
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        help="Number of rows to print for each profile view (default: 40).",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=None,
        help=(
            "Optional wall-clock bound for the profiled search. When reached, the "
            "tool interrupts the main thread and prints the partial profile."
        ),
    )
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Optional .prof path for later pstats inspection.",
    )
    return parser


def _render(profile: cProfile.Profile, *, limit: int) -> str:
    output = io.StringIO()
    stats = pstats.Stats(profile, stream=output).strip_dirs()
    stats.sort_stats("cumulative")
    output.write("\n=== TOP BY CUMULATIVE TIME ===\n")
    stats.print_stats(limit)
    output.write("\n=== TOP BY SELF TIME ===\n")
    stats.sort_stats("tottime")
    stats.print_stats(limit)
    output.write("\n=== SQLITE-RELATED CALLS ===\n")
    stats.sort_stats("cumulative")
    stats.print_stats("sqlite", limit)
    return output.getvalue()


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    warm_started = perf_counter()
    snapshot = ExtremeResourceCanonicalStaticSnapshotService(database).build()
    warm_elapsed = perf_counter() - warm_started

    print("EXTREME RESOURCE STATIC SNAPSHOT")
    print(f"database={snapshot.database_path}")
    print(f"preload_seconds={warm_elapsed:.3f}")
    print(f"preload_complete={snapshot.preload_complete}")
    print(f"player_skills={len(snapshot.player_skills)}")
    print(f"cp_non_slottable={len(snapshot.champion_points_non_slottable)}")
    print(f"cp_slottable={len(snapshot.champion_points_slottable)}")
    if snapshot.preload_unresolved:
        print("preload_unresolved=")
        for item in snapshot.preload_unresolved:
            print(f"  {item}")

    service = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        database_path=database
    )

    timer: Timer | None = None
    if args.seconds is not None:
        seconds = float(args.seconds)
        if seconds <= 0:
            raise ValueError("--seconds must be greater than zero")
        timer = Timer(seconds, _thread.interrupt_main)
        timer.daemon = True

    profile = cProfile.Profile()
    started = perf_counter()
    completed = False
    record = None
    if timer is not None:
        timer.start()
    profile.enable()
    try:
        record = service.record(args.objective)
        completed = True
    except KeyboardInterrupt:
        print("\nPROFILE INTERRUPTED: reporting work completed so far.", flush=True)
    finally:
        profile.disable()
        if timer is not None:
            timer.cancel()

    elapsed = perf_counter() - started
    print("EXTREME RESOURCE RECORD PROFILE")
    print(f"objective={args.objective}")
    print(f"profiled_elapsed_seconds={elapsed:.3f}")
    print(f"completed={completed}")
    if record is not None:
        print(f"raw_value={record.raw_value}")
        print(f"proof_status={record.proof_status.value}")

    print(_render(profile, limit=max(1, int(args.limit))))

    if args.save is not None:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        profile.dump_stats(str(args.save))
        print(f"profile_saved={args.save}")

    return 0 if completed else 130


if __name__ == "__main__":
    raise SystemExit(main())
