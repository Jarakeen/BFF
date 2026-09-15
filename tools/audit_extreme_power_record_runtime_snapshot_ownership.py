from __future__ import annotations

"""Audit canonical ownership of closed Weapon/Spell Damage snapshot prerequisites.

This is an E1 integration audit, not a new record search.  It verifies that every
reviewed prerequisite of the closed power records has one explicit canonical owner
and that the subset assigned to unified runtime history maps only to runtime event
families the current ExtremeRuntimeSnapshot contract is designed to carry.
"""

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_power_record_runtime_requirement_service import (
    ExtremePowerRecordRuntimeRequirementService,
    ExtremePowerRequirementOwner,
)


RUNTIME_KINDS = {"gear_proc", "potion_use", "external_group_buff"}


def _audit(objective: str):
    rows = ExtremePowerRecordRuntimeRequirementService.requirements_for(objective)
    ids = [row.requirement_id for row in rows]
    duplicate_ids = sorted(
        requirement_id
        for requirement_id, count in Counter(ids).items()
        if count > 1
    )
    orphaned = tuple(row for row in rows if not row.owner)
    runtime = tuple(row for row in rows if row.unified_runtime_snapshot_owned)
    unknown_runtime_kinds = tuple(
        row
        for row in runtime
        if row.runtime_history_kind not in RUNTIME_KINDS
    )
    missing_runtime_kind = tuple(
        row
        for row in runtime
        if not row.runtime_history_kind
    )
    misplaced_runtime_kind = tuple(
        row
        for row in rows
        if not row.unified_runtime_snapshot_owned and row.runtime_history_kind is not None
    )
    return (
        rows,
        duplicate_ids,
        orphaned,
        runtime,
        unknown_runtime_kinds,
        missing_runtime_kind,
        misplaced_runtime_kind,
    )


def main() -> int:
    all_ready = True
    print("EXTREME POWER RECORD RUNTIME SNAPSHOT OWNERSHIP")

    for objective in ("weapon_damage", "spell_damage"):
        (
            rows,
            duplicate_ids,
            orphaned,
            runtime,
            unknown_runtime_kinds,
            missing_runtime_kind,
            misplaced_runtime_kind,
        ) = _audit(objective)
        owner_counts = Counter(row.owner.value for row in rows)
        ready = not (
            duplicate_ids
            or orphaned
            or unknown_runtime_kinds
            or missing_runtime_kind
            or misplaced_runtime_kind
        )
        all_ready = all_ready and ready

        print()
        print(f"OBJECTIVE={objective}")
        print(f"requirement_count={len(rows)}")
        print(f"runtime_history_requirement_count={len(runtime)}")
        for owner in ExtremePowerRequirementOwner:
            print(f"owner_{owner.value}={owner_counts.get(owner.value, 0)}")
        print(f"duplicate_requirement_ids={len(duplicate_ids)}")
        print(f"orphaned_requirements={len(orphaned)}")
        print(f"unknown_runtime_kinds={len(unknown_runtime_kinds)}")
        print(f"missing_runtime_kind={len(missing_runtime_kind)}")
        print(f"misplaced_runtime_kind={len(misplaced_runtime_kind)}")
        for row in rows:
            suffix = (
                f" runtime_kind={row.runtime_history_kind!r}"
                if row.runtime_history_kind is not None
                else ""
            )
            print(
                f"  {row.requirement_id}: owner={row.owner.value}"
                f" external={row.external}{suffix}"
            )
        print(f"{objective}_runtime_ownership_closed={ready}")

    print()
    print("PROOF STATUS")
    print(f"unified_runtime_supported_kinds={tuple(sorted(RUNTIME_KINDS))!r}")
    print(f"power_record_runtime_ownership_closed={all_ready}")
    print("final_e1_runtime_record_bridge_closed=False")
    print(
        "NEXT_STEP=if ownership is green, build one constructive ExtremeRuntimeSnapshot witness "
        "for each closed power record and prove potion, external Minor power, and Armor of Truth "
        "runtime state through the shared CombatState projector; keep target health/Off Balance, "
        "same-build resources, class-runtime, and active-bar legality with their canonical owners"
    )
    return 0 if all_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
