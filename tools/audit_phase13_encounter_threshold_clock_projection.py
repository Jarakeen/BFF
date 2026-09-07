from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from minmax.fight_damage_trajectory import RaidDamageSegment
from services.encounter_boss_guide import EncounterBossGuideService
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjectionService,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Project reviewed encounter health thresholds into wall-clock time using "
            "an explicit caller-supplied raid DPS assumption."
        )
    )
    parser.add_argument("--encounter", required=True)
    parser.add_argument(
        "--difficulty",
        choices=("normal", "veteran", "hardmode"),
        default="hardmode",
    )
    parser.add_argument("--raid-dps", type=float, required=True)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    if float(args.raid_dps) <= 0:
        raise ValueError("--raid-dps must be positive")

    guide = EncounterBossGuideService(Path(args.database)).get(args.encounter)
    projection = EncounterHealthThresholdProjectionService().project(
        guide=guide,
        difficulty=args.difficulty,
        damage_segments=(
            RaidDamageSegment(
                0.0,
                None,
                float(args.raid_dps),
                "caller-supplied constant raid DPS audit assumption",
            ),
        ),
    )

    print("=" * 96)
    print(" PHASE 13 ENCOUNTER HEALTH-THRESHOLD CLOCK PROJECTION")
    print("=" * 96)
    print(f"Encounter:   {guide.name} ({guide.encounter_id})")
    print(f"Content:     {guide.content_name}")
    print(f"Difficulty:  {projection.difficulty}")
    print(f"Boss health: {projection.maximum_health if projection.maximum_health is not None else 'unresolved'}")
    print(f"Raid DPS:    {float(args.raid_dps):,.0f} (caller supplied; not derived from Phase 12 potency)")
    print(
        "Boundary:    clock times are conditional projections under this DPS assumption, not canonical encounter timestamps"
    )
    print()

    if not projection.points:
        print("No reviewed health-threshold facts could be projected.")
    else:
        print("FACT KEY                         | THRESHOLD | PROJECTED TIME | STATUS")
        print("---------------------------------+-----------+----------------+------------------------------")
        for point in projection.points:
            time_text = f"{point.time_seconds:10.2f}s" if point.time_seconds is not None else "    unresolved"
            status = "resolved" if point.resolved else point.reason
            print(
                f"{point.fact_key:32s} | {point.threshold_fraction * 100:8.1f}% | "
                f"{time_text:14s} | {status}"
            )

    if projection.unresolved:
        print()
        print("UNRESOLVED")
        print("----------")
        for message in projection.unresolved:
            print(message)

    print()
    print("Interpretation: changing raid DPS changes projected threshold timing. Health-triggered")
    print("mechanics therefore cannot have one universal seconds-since-pull timestamp independent")
    print("of group damage trajectory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
