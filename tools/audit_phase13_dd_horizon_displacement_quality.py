from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.rotation_ability_priority import AbilityPriorityList
from services.rotation_horizon_displacement_quality_service import (
    RotationHorizonDisplacementQualityService,
)
from tools.audit_phase13_dd_priority_schedule import _character_name, _priority_entries
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify saved-DD fixed-horizon displacement spillover as protected-obligation "
            "saturation, ordinary cadence debt, late-window truncation, or unknown provenance."
        )
    )
    parser.add_argument("--character")
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument(
        "--priority",
        action="append",
        default=[],
        metavar="BAR:SLOT:PRIORITY",
        help="Rank every occupied ordinary saved-bar slot; lower number is higher priority.",
    )
    args = parser.parse_args()

    duration = float(args.duration)
    if duration <= 0:
        raise ValueError("duration must be positive")

    build = _load_build(Path(args.builds), args.build, args.character)
    role = str(getattr(build, "Role", "") or "").strip().casefold()
    if role not in _DD_ROLE_KEYS:
        raise ValueError(
            "DD horizon quality audit requires a saved damage-dealer build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

    priorities = _priority_entries(tuple(args.priority or ()), build=build)
    priority_list = AbilityPriorityList(
        character_name=_character_name(build),
        build_name=str(getattr(build, "BuildName", "") or "").strip(),
        role=str(getattr(build, "Role", "") or "Unspecified").strip(),
        entries=priorities,
    )
    generated = RotationGenerationSupport().generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=duration,
            weave_light_attacks=True,
            ability_priorities=priorities,
        ),
    )
    report = RotationHorizonDisplacementQualityService().classify(
        generated.plan,
        priorities=priority_list,
    )

    counts = Counter(row.quality.value for row in report.rows)
    print("=" * 72)
    print(" PHASE 13 DD HORIZON DISPLACEMENT QUALITY AUDIT")
    print("=" * 72)
    print(f"Character: {_character_name(build) or 'unnamed'}")
    print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Duration:  {duration:g}s")
    print(f"Spillover rows: {len(report.rows)}")
    print(f"Proven cadence debt: {len(report.cadence_debt)}")
    print(f"Clean of proven cadence debt: {report.clean_of_proven_cadence_debt}")
    print()

    print("CLASSIFICATION COUNTS")
    print("---------------------")
    for key in (
        "protected_obligation_saturation",
        "ordinary_cadence_debt",
        "late_window_truncation",
        "unknown_provenance",
    ):
        print(f"{key}={counts.get(key, 0)}")
    print()

    print("SPILLOVER DETAIL")
    print("----------------")
    if not report.rows:
        print("none")
    for row in report.rows:
        displaced_from = (
            f"{row.displaced_from_time_seconds:g}s"
            if row.displaced_from_time_seconds is not None
            else "unknown"
        )
        ordinary = (
            ",".join(f"{value:g}" for value in row.later_ordinary_skill_times)
            if row.later_ordinary_skill_times
            else "none"
        )
        print(
            f"{row.bar} | priority={row.priority} | {row.skill_name} | "
            f"displaced_from={displaced_from} | quality={row.quality.value} | "
            f"later_ordinary={ordinary}"
        )
        print(f"  reason: {row.reason}")
    print()

    if report.cadence_debt:
        print(
            "NEXT_STEP=proven ordinary cadence debt remains; inspect those exact post-displacement ordinary slots before changing refresh policy"
        )
    else:
        print(
            "NEXT_STEP=no proven ordinary cadence debt; remaining spillover is protected/terminal/unknown and should not trigger a scheduler rewrite without stronger evidence"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
