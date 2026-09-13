from __future__ import annotations

"""Scan all saved DD builds for scheduler-supported execute positive controls."""

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.build_model import PlayerBuild
from services.build_gear_enchantment_compatibility_service import (
    BuildGearEnchantmentCompatibilityService,
)
from services.rotation_execute_saved_build_control_discovery_service import (
    RotationExecuteSavedBuildControlDiscoveryService,
)


def _load_all_builds(path: Path) -> tuple[PlayerBuild, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    builds: list[PlayerBuild] = []
    for member in payload.get("Members", []):
        loaded = PlayerBuild.from_dict(member)
        builds.append(BuildGearEnchantmentCompatibilityService.normalize_build(loaded))
    return tuple(builds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Also print DD builds with no positive or unresolved execute evidence.",
    )
    args = parser.parse_args()

    controls = RotationExecuteSavedBuildControlDiscoveryService().discover(
        _load_all_builds(Path(args.builds))
    )

    print("=" * 72)
    print(" PHASE 13 DD EXECUTE POSITIVE-CONTROL DISCOVERY")
    print("=" * 72)
    print(f"Saved DD builds reviewed: {len(controls)}")
    print()

    positive_builds = 0
    continuous_builds = 0
    counts: Counter[str] = Counter()
    for control in controls:
        positives = control.threshold_supported
        continuous = control.continuous_unresolved
        if not args.show_all and not positives and not continuous:
            continue
        if positives:
            positive_builds += 1
        if continuous:
            continuous_builds += 1
        print(
            f"{control.character_name or 'unnamed'} | {control.build_name or 'unnamed'} "
            f"| role={control.role or 'unresolved'}"
        )
        if positives:
            for row in positives:
                thresholds = sorted(
                    {
                        component.threshold
                        for component in row.result.evidence.components
                        if component.consequence_type.value == "activates_component"
                    }
                )
                threshold_text = ",".join(f"{value * 100:g}%" for value in thresholds) or "reviewed"
                print(
                    f"  POSITIVE {row.bar}:{row.slot} | {row.skill_name} "
                    f"| threshold={threshold_text}"
                )
                counts["threshold_activation_supported"] += 1
        if continuous:
            for row in continuous:
                print(
                    f"  CONTINUOUS-UNRESOLVED {row.bar}:{row.slot} | {row.skill_name}"
                )
                counts["continuous_amplification_unresolved"] += 1
        if not positives and not continuous:
            print("  execute_control_evidence=none")
        print()

    print("SUMMARY")
    print("-------")
    print(f"positive_threshold_builds={positive_builds}")
    print(f"continuous_unresolved_builds={continuous_builds}")
    print(f"threshold_activation_supported_skills={counts['threshold_activation_supported']}")
    print(
        f"continuous_amplification_unresolved_skills={counts['continuous_amplification_unresolved']}"
    )
    if positive_builds:
        print(
            "NEXT_STEP=use one listed positive saved DD as the production Generate execute control with an explicit target-Health timeline"
        )
    else:
        print(
            "NEXT_STEP=no saved DD positive threshold control exists; add a synthetic production-boundary fixture rather than altering a real saved build"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
