from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    discover_healer_heavy_attack_build_incentives,
)
from minmax.healer_recovery_heavy_pressure import evaluate_healer_recovery_heavy_pressure
from minmax.healer_recovery_heavy_runtime_candidates import build_recovery_heavy_attack_candidate
from minmax.heavy_attack_opportunity import evaluate_heavy_attack_opportunity
from minmax.heavy_attack_wait_window import derive_heavy_attack_decision_window
from minmax.resource_costs import ResourceType
from services.rotation_sustain_service import RotationSustainService
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"


@dataclass(frozen=True)
class DecisionTrace:
    context: object
    pressure: object


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Trace real saved-build recovery-heavy decision gates at every consulted slot."
    )
    parser.add_argument("--character", required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--trigger-fraction", type=float, default=0.80)
    parser.add_argument("--channel-seconds", type=float, default=1.8)
    args = parser.parse_args()

    build = _load_saved_build(
        args.builds,
        character=args.character,
        build_name=args.build,
    )
    support = RotationGenerationSupport()
    baseline = support.generate(
        build=build,
        request=RotationGenerationRequest(duration_seconds=float(args.duration)),
    )
    sustain = RotationSustainService(database_path=Path(args.database)).evaluate(
        build=build,
        plan=baseline,
        resource=ResourceType.MAGICKA,
    )
    timeline = sustain.run.timeline
    maximum = int(timeline.starting_amount)
    trigger = float(args.trigger_fraction)
    channel = float(args.channel_seconds)

    traces: list[DecisionTrace] = []

    def pressure_resolver(context):
        pressure = evaluate_healer_recovery_heavy_pressure(
            timeline=timeline,
            time_seconds=float(context.time_seconds),
            maximum_amount=maximum,
            trigger_fraction=trigger,
        )
        traces.append(DecisionTrace(context=context, pressure=pressure))
        return pressure

    generated = support.generate(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=float(args.duration),
            required_heavy_channel_seconds=channel,
            recovery_pressure_resolver=pressure_resolver,
        ),
    )

    recovery_incentives = tuple(
        item
        for item in discover_healer_heavy_attack_build_incentives(build)
        if item.kind is HeavyAttackBuildIncentiveKind.RECOVERY_VALUE
    )

    print("=" * 118)
    print(" PHASE 13 RECOVERY HEAVY DECISION TRACE")
    print("=" * 118)
    print(f"Character: {args.character} | Build: {args.build} | Trigger: {trigger:.1%} | Channel: {channel:g}s")
    print(f"Baseline Magicka: start={timeline.starting_amount} end={timeline.ending_amount}")
    print("Recovery incentives: " + (", ".join(f"{item.name}/{item.bar}/{item.weapon.value}" for item in recovery_incentives) or "none"))
    print()
    print(" TIME | BAR   | MAGICKA | FRACTION | PRESSURE | WINDOW | COLLISION | CANDIDATE | OUTCOME")
    print("------+-------+---------+----------+----------+--------+-----------+-----------+------------------------------")

    for trace in traces:
        context = trace.context
        pressure = trace.pressure
        window = derive_heavy_attack_decision_window(
            context=context,
            required_window_seconds=channel,
        )
        candidate = None
        outcome = "no matching recovery incentive"
        for incentive in recovery_incentives:
            built = build_recovery_heavy_attack_candidate(
                incentive=incentive,
                pressure=pressure,
                window=window,
            )
            if built is None:
                continue
            candidate = built
            evaluated = evaluate_heavy_attack_opportunity(built.evidence)
            outcome = evaluated.reason
            break

        fraction = pressure.resource_fraction
        print(
            f"{float(context.time_seconds):5.1f}s | {str(context.bar or ''):5s} | "
            f"{pressure.current_amount:7d} | {fraction:8.1%} | "
            f"{str(pressure.recommended):8s} | {window.available_window_seconds:6.1f}s | "
            f"{str(window.refresh_due_before_completion):9s} | {str(candidate is not None):9s} | {outcome}"
        )

    scheduled = [
        action
        for action in generated.actions
        if action.kind.value == "heavy_attack"
    ]
    print()
    print(f"Consulted decisions: {len(traces)}")
    print(f"Scheduled heavies:   {len(scheduled)}")
    for action in scheduled:
        print(f"  {action.time_seconds:g}s | {action.bar or 'unbarred'} | {action.name or 'Heavy Attack'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
