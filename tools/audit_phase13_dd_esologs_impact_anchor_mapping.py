from __future__ import annotations

"""Map reviewed ESO Logs cast/impact observations onto one saved DD audit plan.

This tool does not discover, estimate, or infer impact timing. It accepts only a
versioned observation file containing exact cast-track-linked timestamps and uses the
same base saved-build generation path as the whole-plan DD damage coverage audit.
Successful output can be copied directly as ``--impact-anchor`` arguments into that
audit.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_phase13_saved_build_rotation_timing import _load_build
from tools.dd_audit_esologs_anchor_evidence_support import (
    DDAuditEsoLogsAnchorEvidenceSupport,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or ""
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character")
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument(
        "--no-weave",
        action="store_true",
        help="Disable normal light-attack weaving for the audit replay plan.",
    )
    args = parser.parse_args()

    duration = float(args.duration)
    if duration <= 0.0:
        raise ValueError("duration must be positive")

    build = _load_build(Path(args.builds), args.build, args.character)
    role = str(getattr(build, "Role", "") or "").strip().casefold()
    if role not in _DD_ROLE_KEYS:
        raise ValueError(
            "DD ESO Logs anchor audit requires a saved damage-dealer build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

    generated = RotationGenerationSupport().generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=duration,
            weave_light_attacks=not bool(args.no_weave),
        ),
    )
    result = DDAuditEsoLogsAnchorEvidenceSupport().map_file(
        Path(args.evidence),
        plan=generated.plan,
    )

    print("=" * 72)
    print(" PHASE 13 DD ESO LOGS IMPACT-ANCHOR MAPPING AUDIT")
    print("=" * 72)
    print(f"Character: {_character_name(build) or 'unnamed'}")
    print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Duration:  {duration:g}s")
    print(f"Evidence:  {Path(args.evidence)}")
    print()

    print("MAPPED EXACT IMPACT ANCHORS")
    print("---------------------------")
    if result.evidence:
        for row in result.evidence:
            print(
                f"--impact-anchor \"{row.skill_entity_id}:"
                f"{row.action_time_seconds:g}:{row.action_sequence}:"
                f"{row.anchor_time_seconds:g}\""
            )
            print(f"  source: {row.source}")
    else:
        print("none")
    print()

    print("UNRESOLVED")
    print("----------")
    if result.unresolved:
        for item in result.unresolved:
            print(item)
    else:
        print("none")
    print()

    if result.unresolved:
        print("RESULT=FAIL: reviewed observation file does not provide complete exact anchor coverage")
        return 1
    if not result.evidence:
        print("RESULT=FAIL: reviewed observation file mapped no executable exact anchors")
        return 1

    print(
        "RESULT=PASS: exact cast-track-linked ESO Logs observations map completely "
        "onto the saved DD audit plan"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
