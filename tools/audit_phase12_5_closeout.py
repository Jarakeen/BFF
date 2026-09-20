from __future__ import annotations

"""Read-only Phase 12.5 closeout audit for the current Raid Plan workflow.

The audit consumes real saved Raid Plans, Builds, and Roster members but never writes
those stores.  Raid Plan persistence is round-tripped only through a temporary file.
Optimizer Adviser is invoked read-only and the plan snapshot is compared before/after.

Examples:
    python tools/audit_phase12_5_closeout.py --plan "Performance Mode"
    python tools/audit_phase12_5_closeout.py --plan-id performance-mode-cloudrest
"""

import argparse
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from engine.config import DEFAULT_DATABASE, get_data_dir
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.phase12_5_raid_plan_workflow_audit import (
    Phase125RaidPlanWorkflowAuditService,
)
from services.raid_plan_optimizer_adviser_service import RaidPlanOptimizerAdviserService
from services.raid_plan_repository import RaidPlanRepository
from services.roster_service import RosterService
from services.saved_build_capability_service import SavedBuildCapabilityService


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _choose_plan(plans, *, plan_id: str = "", plan_name: str = ""):
    if not plans:
        raise ValueError("no saved Raid Plans were found")

    wanted_id = _clean(plan_id).casefold()
    if wanted_id:
        matches = tuple(plan for plan in plans if plan.plan_id.casefold() == wanted_id)
        if len(matches) != 1:
            raise ValueError(
                f"plan id {plan_id!r} did not resolve to exactly one saved Raid Plan"
            )
        return matches[0]

    wanted_name = _clean(plan_name).casefold()
    if wanted_name:
        exact = tuple(plan for plan in plans if plan.name.casefold() == wanted_name)
        if len(exact) == 1:
            return exact[0]
        contains = tuple(plan for plan in plans if wanted_name in plan.name.casefold())
        if len(contains) == 1:
            return contains[0]
        raise ValueError(
            f"plan name {plan_name!r} did not resolve to exactly one saved Raid Plan"
        )

    if len(plans) == 1:
        return plans[0]

    names = ", ".join(f"{plan.plan_id} ({plan.name})" for plan in plans)
    raise ValueError(
        "multiple saved Raid Plans exist; choose one with --plan-id or --plan. "
        f"Available: {names}"
    )


def _yn(value: bool) -> str:
    return "PASS" if value else "FAIL"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-id", default="", help="Exact persisted RaidPlan.plan_id")
    parser.add_argument(
        "--plan",
        default="",
        help="Exact or unique partial persisted Raid Plan name",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=get_data_dir(),
        help="Foundry data directory containing raid_plans.json and builds.json",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Canonical ESO database containing Roster state",
    )
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir)
    plan_repository = RaidPlanRepository(data_dir / "raid_plans.json")
    plans = plan_repository.list_plans()
    try:
        plan = _choose_plan(plans, plan_id=args.plan_id, plan_name=args.plan)
    except ValueError as exc:
        print("PHASE 12.5 CANONICAL WORKFLOW CLOSEOUT")
        print(f"RESULT: FAIL - {exc}")
        return 2

    build_service = BuildService(data_dir / "builds.json")
    build_roster = build_service.load()
    saved_builds = tuple(getattr(build_roster, "Members", ()) or ())

    db = EsoDatabase(Path(args.database))
    roster_service = RosterService(db)
    roster_members = tuple(roster_service.list_members())

    result = Phase125RaidPlanWorkflowAuditService().audit(
        raid_plan=plan,
        saved_builds=saved_builds,
        roster_members=roster_members,
    )

    with TemporaryDirectory(prefix="bff-phase12-5-closeout-") as temp_dir:
        temp_repo = RaidPlanRepository(Path(temp_dir) / "raid_plans.json")
        temp_repo.save(plan)
        persistence_roundtrip_preserved = temp_repo.get(plan.plan_id) == plan

    capability = SavedBuildCapabilityService(build_service, Path(args.database))
    before = plan
    adviser = RaidPlanOptimizerAdviserService(capability).review(
        raid_plan=plan,
        saved_builds=saved_builds,
    )
    optimization_read_only_preserved = plan == before

    print("=" * 72)
    print(" PHASE 12.5 CANONICAL WORKFLOW CLOSEOUT")
    print("=" * 72)
    print(f"Plan:                         {plan.name} ({plan.plan_id})")
    print(f"Team:                         {plan.team_name or 'ad hoc / none'}")
    print(f"Trial:                        {plan.trial_id}")
    print(f"Chairs:                       {result.chair_count}")
    print(f"Assigned players:             {result.assigned_player_count}")
    print(f"Recruit/open chairs:          {result.recruit_count}")
    print(f"Selected builds:              {result.selected_build_count}")
    print(f"Resolved builds:              {result.resolved_build_count}")
    print(f"Explicit unresolved chairs:   {result.unresolved_chair_count}")
    print()
    print("INVARIANTS")
    print(f"  team_identity_preserved        {_yn(result.team_identity_preserved)}")
    print(f"  chair_identity_preserved       {_yn(result.chair_identity_preserved)}")
    print(f"  player_identity_preserved      {_yn(result.player_identity_preserved)}")
    print(f"  recruit_state_preserved        {_yn(result.recruit_state_preserved)}")
    print(f"  character_identity_preserved   {_yn(result.character_identity_preserved)}")
    print(f"  build_identity_preserved       {_yn(result.build_identity_preserved)}")
    print(f"  class_constraints_preserved    {_yn(result.class_constraints_preserved)}")
    print(f"  role_constraints_preserved     {_yn(result.role_constraints_preserved)}")
    print(f"  gear_constraints_preserved     {_yn(result.gear_constraints_preserved)}")
    print(f"  provider_assignment_preserved  {_yn(result.provider_assignment_preserved)}")
    print(f"  unresolved_state_preserved     {_yn(result.unresolved_state_preserved)}")
    print(f"  persistence_roundtrip          {_yn(persistence_roundtrip_preserved)}")
    print(f"  optimizer_read_only            {_yn(optimization_read_only_preserved)}")
    print()
    print("OPTIMIZER ADVISER")
    print(f"  blockers={adviser.blocker_count}")
    print(f"  actionable={adviser.actionable_count}")
    print("  Adviser findings are plan-readiness evidence, not Phase 12.5 pipeline failures.")

    print("\nPROBLEMS")
    if result.problems:
        for problem in result.problems:
            print(f"  - {problem}")
    else:
        print("  - none")

    print("\nBOUNDARIES")
    for boundary in result.boundaries:
        print(f"  - {boundary}")

    passed = (
        result.passed
        and persistence_roundtrip_preserved
        and optimization_read_only_preserved
    )
    print(f"\nRESULT: {'PASS' if passed else 'FAIL'}")
    if passed:
        print(
            "The current Raid Plan workflow preserved exact identity, recruit state, "
            "constraints, provenance, persistence, and read-only Optimization boundaries."
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
