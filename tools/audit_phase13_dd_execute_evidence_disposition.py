from __future__ import annotations

"""Audit execute evidence support disposition for one saved DD build."""

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_execute_evidence_disposition_service import (
    RotationExecuteEvidenceDispositionService,
)
from tools.audit_phase13_dd_execute_candidate_evidence import _ordinary_slots
from tools.audit_phase13_dd_priority_schedule import _character_name
from tools.audit_phase13_saved_build_rotation_timing import _load_build


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character")
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    args = parser.parse_args()

    build = _load_build(Path(args.builds), args.build, args.character)
    role = str(getattr(build, "Role", "") or "").strip().casefold()
    if role not in _DD_ROLE_KEYS:
        raise ValueError(
            "DD execute disposition audit requires a saved damage-dealer build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

    service = RotationExecuteEvidenceDispositionService()
    counts: Counter[str] = Counter()

    print("=" * 72)
    print(" PHASE 13 DD EXECUTE EVIDENCE DISPOSITION AUDIT")
    print("=" * 72)
    print(f"Character: {_character_name(build) or 'unnamed'}")
    print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
    print()

    for bar, slot, skill_name in _ordinary_slots(build):
        result = service.resolve(skill_name)
        counts[result.disposition.value] += 1
        print(
            f"{bar}:{slot} | {skill_name} | canonical={result.evidence.resolved_skill_name or 'unresolved'} "
            f"| disposition={result.disposition.value}"
        )
        for component in result.evidence.components:
            bonus = (
                ""
                if component.maximum_bonus_fraction is None
                else f" | max_bonus={component.maximum_bonus_fraction * 100:g}%"
            )
            print(
                f"  coef#{component.coefficient_number} | target<{component.threshold * 100:g}% "
                f"| {component.consequence_type.value}{bonus}"
            )
        for item in result.unresolved:
            print(f"  unresolved: {item}")

    print()
    print("SUMMARY")
    print("-------")
    for key in (
        "threshold_activation_supported",
        "continuous_amplification_unresolved",
        "no_threshold_evidence",
        "identity_or_source_unresolved",
    ):
        print(f"{key}={counts.get(key, 0)}")
    print()
    if counts.get("continuous_amplification_unresolved", 0):
        print(
            "NEXT_STEP=positive continuous execute evidence exists, but interpolation semantics remain source-unverified; do not award maximum bonus"
        )
    elif counts.get("threshold_activation_supported", 0):
        print(
            "NEXT_STEP=threshold execute evidence is scheduler-supported; validate it through an explicit target-Health timeline on this build"
        )
    else:
        print(
            "NEXT_STEP=this build is not a positive execute control; use another saved DD with reviewed execute evidence before declaring execute evidence coverage complete"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
