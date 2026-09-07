from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.encounter_boss_guide import EncounterBossGuideService


def _number(payload: dict, key: str):
    raw = payload.get(key)
    if isinstance(raw, bool) or raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def timing_shape(payload: dict) -> tuple[str, str]:
    start = _number(payload, "start_seconds")
    end = _number(payload, "end_seconds")
    if start is not None and end is not None and end > start:
        return "CLOCK WINDOW", f"{start:g}s to {end:g}s"

    point = _number(payload, "time_seconds")
    if point is None:
        point = _number(payload, "at_seconds")
    if point is not None:
        return "CLOCK POINT", f"{point:g}s"

    threshold_keys = (
        "threshold",
        "thresholds",
        "starts_at",
        "health_threshold",
        "health_thresholds",
    )
    threshold_values = [payload.get(key) for key in threshold_keys if payload.get(key) not in (None, "", [])]
    if threshold_values:
        rendered = ", ".join(str(value) for value in threshold_values)
        return "THRESHOLD", rendered

    return "UNTIMED", "no explicit seconds or threshold"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit reviewed canonical encounter timeline facts for direct Phase 13 "
            "rotation-demand timing readiness."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--encounter", default="xalvakka")
    args = parser.parse_args()

    guide = EncounterBossGuideService(Path(args.database)).get(args.encounter)

    print("=" * 104)
    print(" PHASE 13 ENCOUNTER ROTATION-DEMAND TIMING READINESS")
    print("=" * 104)
    print(f"Encounter: {guide.name} ({guide.encounter_id})")
    print(f"Content:   {guide.content_name}")
    print(
        "Boundary: clock-timed reviewed facts can feed seconds-based rotation demands; "
        "health thresholds cannot be converted without a fight/DPS projection"
    )
    print()

    if not guide.timeline_facts:
        print("No reviewed canonical timeline facts are persisted for this encounter.")
        return 0

    print("FACT KEY                         | STATUS                  | EVIDENCE | TIMING SHAPE  | VALUE")
    print("---------------------------------+-------------------------+----------+---------------+------------------------------")

    counts = {"CLOCK WINDOW": 0, "CLOCK POINT": 0, "THRESHOLD": 0, "UNTIMED": 0}
    for fact in guide.timeline_facts:
        shape, detail = timing_shape(fact.payload)
        counts[shape] += 1
        print(
            f"{fact.fact_key[:32]:33s}| "
            f"{fact.review_status[:24]:25s}| "
            f"{fact.evidence_count:8d} | "
            f"{shape:13s} | {detail}"
        )

    print()
    print("SUMMARY")
    print("-------")
    print(f"Direct clock windows: {counts['CLOCK WINDOW']}")
    print(f"Direct clock points:  {counts['CLOCK POINT']}")
    print(f"Health/phase timing:  {counts['THRESHOLD']}")
    print(f"Untimed facts:        {counts['UNTIMED']}")
    print()
    direct = counts["CLOCK WINDOW"] + counts["CLOCK POINT"]
    if direct:
        print(
            "Rotation-demand bridge: READY for explicit role-policy mapping on the clock-timed facts above."
        )
    elif counts["THRESHOLD"]:
        print(
            "Rotation-demand bridge: BLOCKED on seconds placement. Canonical encounter timing exists, "
            "but only in health/phase space; a fight-duration/DPS projection is required first."
        )
    else:
        print(
            "Rotation-demand bridge: BLOCKED on timing evidence. No explicit clock timing is currently persisted."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
