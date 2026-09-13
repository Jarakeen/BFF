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

    supported_builds = 0
    threshold_builds = 0
    continuous_supported_builds = 0
    continuous_unresolved_builds = 0
    counts: Counter[str] = Counter()
    for control in controls:
        threshold = control.threshold_supported
        continuous_supported = control.continuous_supported
        continuous_unresolved = control.continuous_unresolved
        if (
            not args.show_all
            and not threshold
            and not continuous_supported
            and not continuous_unresolved
        ):
            continue
        if control.is_positive_execute_control:
            supported_builds += 1
        if threshold:
            threshold_builds += 1
        if continuous_supported:
            continuous_supported_builds += 1
        if continuous_unresolved:
            continuous_unresolved_builds += 1
        print(
            f"{control.character_name or 'unnamed'} | {control.build_name or 'unnamed'} "
            f"| role={control.role or 'unresolved'}"
        )
        if threshold:
            for row in threshold:
                thresholds = sorted(
                    {
                        component.threshold
                        for component in row.result.evidence.components
                        if component.consequence_type.value == "activates_component"
                    }
                )
                threshold_text = ",".join(f"{value * 100:g}%" for value in thresholds) or "reviewed"
                print(
                    f"  THRESHOLD-SUPPORTED {row.bar}:{row.slot} | {row.skill_name} "
                    f"| threshold={threshold_text}"
                )
                counts["threshold_activation_supported"] += 1
        if continuous_supported:
            for row in continuous_supported:
                print(
                    f"  CONTINUOUS-SUPPORTED {row.bar}:{row.slot} | {row.skill_name}"
                )
                counts["continuous_amplification_supported"] += 1
        if continuous_unresolved:
            for row in continuous_unresolved:
                print(
                    f"  CONTINUOUS-UNRESOLVED {row.bar}:{row.slot} | {row.skill_name}"
                )
                counts["continuous_amplification_unresolved"] += 1
        if not threshold and not continuous_supported and not continuous_unresolved:
            print("  execute_control_evidence=none")
        print()

    print("SUMMARY")
    print("-------")
    print(f"positive_execute_builds={supported_builds}")
    print(f"positive_threshold_builds={threshold_builds}")
    print(f"continuous_supported_builds={continuous_supported_builds}")
    print(f"continuous_unresolved_builds={continuous_unresolved_builds}")
    print(f"threshold_activation_supported_skills={counts['threshold_activation_supported']}")
    print(
        f"continuous_amplification_supported_skills={counts['continuous_amplification_supported']}"
    )
    print(
        f"continuous_amplification_unresolved_skills={counts['continuous_amplification_unresolved']}"
    )
    if supported_builds:
        print(
            "NEXT_STEP=use one listed supported saved DD as a production Generate execute control with an explicit target-Health timeline"
        )
    else:
        print(
            "NEXT_STEP=no saved DD supported execute control exists; retain synthetic production-boundary fixtures rather than altering a real saved build"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
