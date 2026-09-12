from __future__ import annotations

"""Time one authoritative Extreme max-resource record closure without cProfile.

The profiling harness is useful for locating hot functions, but its per-call tracing
can materially distort a recursive search with hundreds of millions of Python calls.
This tool measures the actual wall-clock path instead. It warms the canonical static
snapshot first, resets special-subset reuse diagnostics, and optionally interrupts
after a caller-supplied time bound while still reporting progress counters.
"""

import argparse
import _thread
from pathlib import Path
import sys
from threading import Timer
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_max_resource_named_gear_candidate_search_service import (
    ExtremeMaxResourceNamedGearCandidateSearchService,
)
from services.extreme_resource_canonical_static_snapshot_service import (
    ExtremeResourceCanonicalStaticSnapshotService,
)
from services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service import (
    ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
)


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=_OBJECTIVES, default="max_magicka")
    parser.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="Optional wall-clock bound. The real record search is interrupted when reached.",
    )
    return parser


def _print_reuse() -> None:
    print("\nSPECIAL SUBSET REUSE")
    diagnostics = ExtremeMaxResourceNamedGearCandidateSearchService.reuse_diagnostics()
    for key in (
        "fitting_subsets_seen",
        "structural_keys_built",
        "structural_classes_seen",
        "representative_exact_searches",
        "reuse_attempts",
        "reuse_successes",
        "rematerialization_failures",
        "fallback_exact_searches",
    ):
        print(f"{key}={diagnostics.get(key, 0)}")


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

    ExtremeMaxResourceNamedGearCandidateSearchService._reset_reuse_diagnostics()
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
        timer.start()

    started = perf_counter()
    completed = False
    record = None
    try:
        record = service.record(args.objective)
        completed = True
    except KeyboardInterrupt:
        print("\nTIMING INTERRUPTED: reporting work completed so far.", flush=True)
    finally:
        if timer is not None:
            timer.cancel()

    elapsed = perf_counter() - started
    print("\nEXTREME RESOURCE RECORD TIMING")
    print(f"objective={args.objective}")
    print(f"elapsed_seconds={elapsed:.3f}")
    print(f"completed={completed}")
    _print_reuse()

    if record is not None:
        print("\nRESULT")
        print(f"raw_value={record.raw_value}")
        print(f"proof_status={record.proof_status.value}")
        print(f"coverage_complete={record.search_coverage.complete}")
        print(f"globally_proven={record.globally_proven}")
        print(f"omitted={', '.join(record.search_coverage.omitted)}")
        print(f"unresolved={', '.join(record.unresolved)}")

    return 0 if completed else 130


if __name__ == "__main__":
    raise SystemExit(main())
