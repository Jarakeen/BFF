from __future__ import annotations

"""Audit reviewed Tank rotation-assignment policy against canonical requirement IDs.

This is deliberately read-only. It does not infer encounter strategy from role names,
provider ownership, or generic Tank practice. It answers one narrower question: for
each canonical raid-Tank responsibility requirement in an encounter, does the reviewed
rotation-assignment registry contain an exact policy disposition for that same
requirement identity?

Symbolic encounter-horizon maintenance is reported separately because it remains
non-executable until Generate-time encounter-horizon materialization.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.raid_tank_responsibility_encounter_adapter import (
    RaidTankResponsibilityEncounterAdapter,
)
from services.raid_tank_responsibility_profile import (
    DEFAULT_RAID_TANK_RESPONSIBILITY_PROFILE,
)
from services.rotation_assignment_policy_registry_service import (
    DEFAULT_ROTATION_ASSIGNMENT_POLICY,
    RotationAssignmentPolicyRegistryService,
)


@dataclass(frozen=True)
class TankAssignmentPolicyCoverageRow:
    encounter_id: str
    requirement_id: str
    requirement_type: str
    disposition: str
    source: str = ""

    @property
    def reviewed(self) -> bool:
        return self.disposition != "missing"

    @property
    def executable_before_horizon_materialization(self) -> bool:
        return self.disposition != "taunt_maintenance_horizon" and self.reviewed


def audit_encounter(
    encounter_id: str,
    *,
    registry: RotationAssignmentPolicyRegistryService,
) -> tuple[TankAssignmentPolicyCoverageRow, ...]:
    resolved = str(encounter_id or "").strip()
    if not resolved:
        raise ValueError("Tank assignment policy coverage audit requires encounter_id")

    adapter = RaidTankResponsibilityEncounterAdapter(
        DEFAULT_RAID_TANK_RESPONSIBILITY_PROFILE
    )
    requirements = adapter.requirements(resolved)
    bundle = registry.for_encounter(resolved)

    disposition_by_id: dict[str, tuple[str, object]] = {}
    groups = (
        ("effect", bundle.effect_policies),
        ("taunt", bundle.taunt_policies),
        ("taunt_maintenance", bundle.taunt_maintenance_policies),
        ("taunt_maintenance_horizon", bundle.taunt_maintenance_horizon_policies),
        ("non_effect", bundle.non_effect_policies),
    )
    for disposition, policies in groups:
        for policy in policies:
            key = str(policy.requirement_id).casefold()
            if key in disposition_by_id:
                raise ValueError(
                    "Tank assignment policy audit found multiple dispositions for "
                    f"{policy.requirement_id!r}"
                )
            disposition_by_id[key] = (disposition, policy)

    rows: list[TankAssignmentPolicyCoverageRow] = []
    for requirement in requirements:
        matched = disposition_by_id.get(requirement.requirement_id.casefold())
        if matched is None:
            rows.append(
                TankAssignmentPolicyCoverageRow(
                    encounter_id=resolved,
                    requirement_id=requirement.requirement_id,
                    requirement_type=requirement.requirement_type,
                    disposition="missing",
                )
            )
            continue
        disposition, policy = matched
        rows.append(
            TankAssignmentPolicyCoverageRow(
                encounter_id=resolved,
                requirement_id=requirement.requirement_id,
                requirement_type=requirement.requirement_type,
                disposition=disposition,
                source=str(getattr(policy, "source", "") or "").strip(),
            )
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--encounter",
        action="append",
        required=True,
        help="Canonical encounter id to audit. Repeat for multiple encounters.",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_ROTATION_ASSIGNMENT_POLICY,
        help="Reviewed assignment-policy registry path.",
    )
    args = parser.parse_args()

    registry = RotationAssignmentPolicyRegistryService(args.registry)
    encounters = tuple(dict.fromkeys(str(value).strip() for value in args.encounter if str(value).strip()))
    if not encounters:
        parser.error("at least one non-empty --encounter is required")

    print("=" * 72)
    print(" PHASE 13 TANK ASSIGNMENT POLICY COVERAGE AUDIT")
    print("=" * 72)
    print(f"registry={Path(args.registry)}")
    print()

    missing = 0
    symbolic = 0
    reviewed = 0
    for encounter_id in encounters:
        rows = audit_encounter(encounter_id, registry=registry)
        print(encounter_id)
        for row in rows:
            if row.disposition == "missing":
                status = "MISSING"
                missing += 1
            elif row.disposition == "taunt_maintenance_horizon":
                status = "REVIEWED-SYMBOLIC"
                symbolic += 1
                reviewed += 1
            else:
                status = "REVIEWED"
                reviewed += 1
            print(
                f"  {status} | {row.requirement_id} | "
                f"type={row.requirement_type} | disposition={row.disposition}"
            )
            if row.source:
                print(f"    source={row.source}")
        print()

    print("SUMMARY")
    print("-------")
    print(f"reviewed_requirements={reviewed}")
    print(f"symbolic_horizon_requirements={symbolic}")
    print(f"missing_requirements={missing}")
    if missing:
        print(
            "NEXT_STEP=research each missing exact encounter requirement and add only "
            "source-reviewed executable policy; do not infer policy from provider ownership"
        )
    elif symbolic:
        print(
            "NEXT_STEP=field-test Generate-time encounter-horizon materialization for the "
            "reviewed symbolic maintenance requirements"
        )
    else:
        print(
            "NEXT_STEP=field-test reviewed assignment policy against exact selected-team "
            "provider ownership and generated Tank obligations"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
