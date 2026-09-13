from __future__ import annotations

"""Audit canonical target-health execute evidence for one saved DD build.

This diagnostic is read-only.  It does not schedule execute behavior and does not
interpret missing threshold evidence as proof that a skill is not an execute.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_execute_candidate_evidence_service import (
    RotationExecuteCandidateEvidenceService,
)
from tools.audit_phase13_dd_priority_schedule import _character_name
from tools.audit_phase13_saved_build_rotation_timing import _load_build


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


def _ordinary_slots(build):
    for bar_name, attribute in (("front", "FrontBarSkills"), ("back", "BackBarSkills")):
        values = list(getattr(build, attribute, []) or [])[:5]
        for slot, raw in enumerate(values, start=1):
            name = str(raw or "").strip()
            if name:
                yield bar_name, slot, name


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
            "DD execute evidence audit requires a saved damage-dealer build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

    service = RotationExecuteCandidateEvidenceService()

    print("=" * 72)
    print(" PHASE 13 DD EXECUTE CANDIDATE EVIDENCE AUDIT")
    print("=" * 72)
    print(f"Character: {_character_name(build) or 'unnamed'}")
    print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
    print()

    threshold_evidence_count = 0
    unresolved_count = 0
    for bar, slot, skill_name in _ordinary_slots(build):
        result = service.resolve(skill_name)
        print(f"{bar}:{slot} | {skill_name}")
        print(
            "  canonical="
            + (
                f"{result.resolved_skill_name} [{result.entity_id}]"
                if result.resolved_skill_name
                else "unresolved"
            )
        )
        if result.components:
            for component in result.components:
                threshold_evidence_count += 1
                bonus = (
                    ""
                    if component.maximum_bonus_fraction is None
                    else f" | max_bonus={component.maximum_bonus_fraction * 100:g}%"
                )
                print(
                    f"  EXECUTE-EVIDENCE coef#{component.coefficient_number} | "
                    f"target<{component.threshold * 100:g}% | "
                    f"{component.consequence_type.value}{bonus}"
                )
                print(f"    condition:   {component.condition_evidence}")
                print(f"    consequence: {component.consequence_evidence}")
        else:
            print("  threshold_execute_evidence=none")
        if result.unresolved:
            unresolved_count += len(result.unresolved)
            for item in result.unresolved:
                print(f"  unresolved: {item}")
        print()

    print("SUMMARY")
    print("-------")
    print(f"threshold_execute_components={threshold_evidence_count}")
    print(f"unresolved_identity_or_source_items={unresolved_count}")
    print()
    print(
        "Interpretation: explicit target-health threshold damage evidence is a positive "
        "execute signal only. 'none' is not a negative execute classification; other "
        "missing-health or unsupported semantics may still require a separate reviewed "
        "runtime model before scheduler policy can be applied."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
