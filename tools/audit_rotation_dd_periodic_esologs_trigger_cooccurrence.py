from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_dd_periodic_esologs_trigger_cooccurrence_service import (
    RotationDDPeriodicEsoLogsTriggerCooccurrenceService,
)


def _common(values: list[object], *, limit: int = 12) -> str:
    counts = Counter(values)
    if not counts:
        return "none"
    return ", ".join(f"{value} x{count}" for value, count in counts.most_common(limit))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect periodic rows occurring at a reviewed trigger timestamp."
    )
    parser.add_argument("--trigger-id", required=True, type=int)
    parser.add_argument("--periodic-id", required=True, type=int)
    parser.add_argument("--logs-db", required=True, type=Path)
    parser.add_argument("--tolerance-ms", type=float, default=50.0)
    parser.add_argument("--max-observations", type=int, default=30)
    args = parser.parse_args(argv)

    report = RotationDDPeriodicEsoLogsTriggerCooccurrenceService(args.logs_db).inspect(
        trigger_ability_id=args.trigger_id,
        periodic_ability_id=args.periodic_id,
        tolerance_ms=args.tolerance_ms,
    )

    observations = report.observations
    print("\n====================================================")
    print(" DD PERIODIC ESO LOGS TRIGGER COOCCURRENCE")
    print("====================================================")
    print(f"Trigger ability id:  {report.trigger_ability_id}")
    print(f"Periodic ability id: {report.periodic_ability_id}")
    print(f"Tolerance: ±{report.tolerance_ms:g}ms")
    print(f"Trigger events: {report.trigger_count}")
    print(f"Triggers with coincident periodic rows: {report.coincident_trigger_count}")
    print(f"Coincident periodic rows: {len(observations)}")
    print("Coincident offsets: " + _common([round(o.offset_seconds, 3) for o in observations]))
    print("Coincident tick flags: " + _common([o.periodic_tick for o in observations]))
    print("Same target: " + _common([o.same_target for o in observations]))
    print("Same cast track: " + _common([o.same_cast_track for o in observations]))
    print(
        "Next periodic offsets: "
        + _common(
            [round(o.next_offset_seconds, 3) for o in observations if o.next_offset_seconds is not None]
        )
    )

    for index, observation in enumerate(observations[: max(0, args.max_observations)], start=1):
        print(
            f"\n  [{index}] report={observation.report_code} fight={observation.fight_id} "
            f"source={observation.source_id} trigger_event={observation.trigger_event_index}"
        )
        print(
            "      trigger: "
            f"target={observation.trigger_target_id} hit={observation.trigger_hit_type} "
            f"amount={observation.trigger_amount} track={observation.trigger_cast_track_id}"
        )
        print(
            "      coincident periodic: "
            f"event={observation.periodic_event_index} offset={observation.offset_seconds:.3f}s "
            f"target={observation.periodic_target_id} hit={observation.periodic_hit_type} "
            f"amount={observation.periodic_amount} tick={observation.periodic_tick} "
            f"track={observation.periodic_cast_track_id}"
        )
        if observation.next_periodic_event_index is not None:
            print(
                "      next periodic: "
                f"event={observation.next_periodic_event_index} "
                f"offset={observation.next_offset_seconds:.3f}s "
                f"target={observation.next_periodic_target_id} "
                f"hit={observation.next_periodic_hit_type} "
                f"amount={observation.next_periodic_amount} tick={observation.next_periodic_tick}"
            )

    if report.unresolved:
        print("\nUnresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")
    print(
        "\nResult: OBSERVATIONAL ONLY — coincident rows are reported exactly as imported; "
        "this audit never promotes first-tick semantics automatically."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
