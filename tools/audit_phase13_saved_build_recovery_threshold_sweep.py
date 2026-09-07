from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.resource_costs import ResourceType
from tools.audit_phase13_saved_build_recovery_heavy_rotation import (
    _baseline_maximum_magicka,
    _heavy_signature,
    _load_saved_build,
    build_verified_heavy_restore_resolver,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"
DEFAULT_THRESHOLDS = (0.35, 0.50, 0.65, 0.75, 0.80)


def minimum_timeline_point(timeline) -> tuple[float, int]:
    """Return the first point at which the timeline reaches its minimum amount."""

    minimum_amount = int(timeline.starting_amount)
    minimum_time = 0.0
    for event in timeline.events:
        amount = int(event.after)
        if amount < minimum_amount:
            minimum_amount = amount
            minimum_time = float(event.time_seconds)
    return minimum_time, minimum_amount


def _parse_thresholds(raw: str) -> tuple[float, ...]:
    values = tuple(float(item.strip()) for item in str(raw or "").split(",") if item.strip())
    if not values:
        raise ValueError("at least one recovery threshold is required")
    if any(value < 0 or value > 1 for value in values):
        raise ValueError("recovery thresholds must be between 0 and 1")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sweep explicit recovery-heavy trigger fractions for one real saved healer build "
            "without treating any threshold or heavy restore amount as canonical ESO policy."
        )
    )
    parser.add_argument("--character", required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--restore-amount", type=int, required=True)
    parser.add_argument(
        "--restore-bar",
        choices=("front", "back"),
        help="optional diagnostic filter; omit to credit the supplied test restore to any scheduled staff heavy",
    )
    parser.add_argument("--channel-seconds", type=float, default=1.8)
    parser.add_argument(
        "--thresholds",
        default=",".join(f"{value:g}" for value in DEFAULT_THRESHOLDS),
        help="comma-separated fractions, e.g. 0.35,0.5,0.65,0.75,0.8",
    )
    parser.add_argument("--max-iterations", type=int, default=6)
    args = parser.parse_args()

    build = _load_saved_build(
        args.builds,
        character=args.character,
        build_name=args.build,
    )
    maximum_magicka = _baseline_maximum_magicka(
        build=build,
        duration_seconds=float(args.duration),
        database_path=Path(args.database),
    )
    thresholds = _parse_thresholds(args.thresholds)
    resolver = build_verified_heavy_restore_resolver(
        amount=args.restore_amount,
        channel_seconds=args.channel_seconds,
        bar=args.restore_bar,
    )

    print("=" * 86)
    print(" PHASE 13 SAVED-BUILD RECOVERY HEAVY THRESHOLD SWEEP")
    print("=" * 86)
    print(f"Character:       {args.character}")
    print(f"Build:           {args.build}")
    print(f"Duration:        {float(args.duration):g}s")
    print(f"Maximum Magicka: {maximum_magicka} (Phase 4 full-pool baseline)")
    print(f"Heavy restore:   {int(args.restore_amount)} Magicka (caller supplied)")
    print(f"Heavy channel:   {float(args.channel_seconds):g}s")
    print(f"Restore bar:     {args.restore_bar or 'any scheduled heavy'}")
    print("Boundary:        sensitivity audit only; thresholds and restore amount are not canonical policy")
    print()
    print("TRIGGER | MIN MAGICKA | MIN TIME | HEAVIES | END MAGICKA | SHORTFALL | CONVERGED")
    print("--------+-------------+----------+---------+-------------+-----------+----------")

    for trigger in thresholds:
        result = RotationGenerationSupport().generate_with_evidence(
            build=build,
            request=RotationGenerationRequest(
                duration_seconds=float(args.duration),
                required_heavy_channel_seconds=float(args.channel_seconds),
                stabilize_recovery_heavies=True,
                recovery_stabilization_resource=ResourceType.MAGICKA,
                recovery_maximum_amount=maximum_magicka,
                recovery_trigger_fraction=float(trigger),
                recovery_restoration_resolver=resolver,
                recovery_stabilization_max_iterations=int(args.max_iterations),
            ),
        )
        stabilization = result.recovery_stabilization
        if stabilization is None:
            raise RuntimeError("recovery-heavy stabilization evidence was not returned")

        timeline = stabilization.replay.final_projection.run.timeline
        minimum_time, minimum_amount = minimum_timeline_point(timeline)
        heavies = _heavy_signature(stabilization.plan)
        print(
            f"{trigger:7.1%} | {minimum_amount:11d} | {minimum_time:8.1f}s | "
            f"{len(heavies):7d} | {timeline.ending_amount:11d} | "
            f"{timeline.total_shortfall:9d} | {str(stabilization.converged):>9s}"
        )
        if heavies:
            schedule = ", ".join(
                f"{time_seconds:g}s/{bar or 'unbarred'}"
                for time_seconds, bar, _name in heavies
            )
            print(f"          heavy schedule: {schedule}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
