from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.rotation_ability_priority import AbilityPriorityList
from services.rotation_priority_displacement_audit_service import (
    RotationPriorityDisplacementAuditService,
)
from tools.audit_phase13_dd_priority_schedule import (
    _character_name,
    _priority_entries,
)
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate one saved DD plan with explicit priorities and report whether "
            "fixed-horizon displacement contradicts those priorities."
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
            "DD displacement audit requires a saved damage-dealer build; "
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
    audit = RotationPriorityDisplacementAuditService().audit(
        generated.plan,
        priorities=priority_list,
    )

    print("=" * 72)
    print(" PHASE 13 DD PRIORITY DISPLACEMENT AUDIT")
    print("=" * 72)
    print(f"Character: {_character_name(build) or 'unnamed'}")
    print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Duration:  {duration:g}s")
    print(f"Horizon-displaced skills: {len(audit.displaced_beyond_horizon)}")
    print(f"Priority inversions:      {len(audit.inversions)}")
    print(f"Priority consistent:      {audit.priority_consistent}")
    print()

    print("HORIZON-DISPLACED SKILLS")
    print("------------------------")
    if audit.displaced_beyond_horizon:
        for bar, skill_name, priority in audit.displaced_beyond_horizon:
            print(f"{bar} | priority={priority} | {skill_name}")
    else:
        print("none")
    print()

    print("PRIORITY INVERSIONS")
    print("-------------------")
    if audit.inversions:
        for row in audit.inversions:
            print(
                f"{row.bar} | displaced '{row.displaced_skill_name}' priority={row.displaced_priority} "
                f"while lower-priority '{row.lower_priority_skill_name}' priority={row.lower_priority} "
                f"still cast through {row.lower_priority_last_time_seconds:g}s"
            )
    else:
        print("none")
    print()

    if audit.priority_consistent:
        print(
            "NEXT_STEP=horizon spillover is not proven to violate explicit priority; "
            "do not rewrite displacement ordering from this evidence alone"
        )
    else:
        print(
            "NEXT_STEP=priority-aware displacement ordering is justified; preserve due refreshes "
            "but choose among displaced/current same-bar actions by explicit priority"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
