from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.generated_roster_plan_service import GeneratedRosterPlanService
from services.phase12_5_legacy_plan_repair import Phase125LegacyPlanRepairService
from services.roster_service import RosterService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect or safely repair one pre-Phase-12.5 generated team plan."
    )
    parser.add_argument(
        "--team",
        default="",
        help="Generated team name. Defaults to the most recent generated plan.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply only the repairs proven safe by the dry-run inspection.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    data_dir = get_data_dir()
    db = EsoDatabase(data_dir / "eso.db")
    plans = GeneratedRosterPlanService(db)
    roster = RosterService(db)
    builds = BuildService(data_dir / "builds.json")
    service = Phase125LegacyPlanRepairService(plans=plans, roster=roster)

    requested = str(args.team or "").strip()
    plan = plans.load_plan(requested) if requested else plans.latest_plan()
    if plan is None:
        print("PHASE 12.5 LEGACY PLAN REPAIR")
        print("RESULT: NO PLAN")
        return 1

    roster_members = tuple(roster.list_members())
    build_roster = builds.load()
    result = service.inspect(
        plan=plan,
        builds=build_roster,
        roster_members=roster_members,
    )

    print("========================================")
    print(" PHASE 12.5 LEGACY PLAN REPAIR")
    print("========================================")
    print(f"Team:                    {result.team_name}")
    print(f"Missing team identity:   {'yes' if result.team_identity_missing else 'no'}")
    print(f"Provable saved chairs:   {len(result.promotable_slots)}")
    print(f"Ambiguous legacy chairs: {len(result.ambiguous_slots)}")
    print(f"Blocked source chairs:   {len(result.blocked_source_slots)}")

    if result.promotable_slots:
        print("\nPROVABLE SAVED-CHAIR REPAIRS")
        for slot in result.promotable_slots:
            print(f"- {slot}")
    if result.ambiguous_slots:
        print("\nAMBIGUOUS - LEFT UNCHANGED")
        for slot in result.ambiguous_slots:
            print(f"- {slot}")
    if result.blocked_source_slots:
        print("\nNON-ROSTER SOURCE - LEFT AS RECRUIT EVIDENCE")
        for slot in result.blocked_source_slots:
            print(f"- {slot}")

    if not args.apply:
        print("\nMODE: DRY RUN")
        print("No data was changed.")
        if result.has_repairs:
            print("Run again with --apply to perform only the provable repairs above.")
        else:
            print("No safe legacy repair is available from current evidence.")
        return 0

    if not result.has_repairs:
        print("\nMODE: APPLY")
        print("No provable repairs were available; no data was changed.")
        return 0

    repaired = service.apply(
        plan=plan,
        builds=build_roster,
        roster_members=roster_members,
    )
    after = service.inspect(
        plan=repaired,
        builds=build_roster,
        roster_members=tuple(roster.list_members()),
    )
    print("\nMODE: APPLY")
    print(f"Team identity now present: {'yes' if not after.team_identity_missing else 'NO'}")
    print(f"Remaining promotable chairs: {len(after.promotable_slots)}")
    print(f"Remaining ambiguous chairs:  {len(after.ambiguous_slots)}")
    print(f"Remaining blocked chairs:    {len(after.blocked_source_slots)}")
    print("RESULT: APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
