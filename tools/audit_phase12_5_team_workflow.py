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
from services.phase12_5_team_workflow_audit import (
    Phase125TeamWorkflowAuditService,
    recruit_prescriptions_from_rows,
)
from services.roster_service import RosterService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit one real persisted Comp Maker -> Roster -> Optimization team workflow."
    )
    parser.add_argument(
        "--team",
        default="",
        help="Named Roster/generated team. Defaults to the most recent generated plan.",
    )
    return parser


def _prescription_rows(db: EsoDatabase, plan_id: int):
    table = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='generated_roster_recruit_prescription'"
    ).fetchone()
    if table is None:
        return ()
    return db.execute(
        """
        SELECT slot_name, prescription_json
        FROM generated_roster_recruit_prescription
        WHERE plan_id = ?
        ORDER BY slot_name COLLATE NOCASE
        """,
        (plan_id,),
    ).fetchall()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    data_dir = get_data_dir()
    db = EsoDatabase(data_dir / "eso.db")
    plans = GeneratedRosterPlanService(db)
    roster = RosterService(db)
    builds = BuildService(data_dir / "builds.json")

    requested = str(args.team or "").strip()
    plan = plans.load_plan(requested) if requested else plans.latest_plan()
    if plan is None:
        print("PHASE 12.5 TEAM WORKFLOW AUDIT")
        print("RESULT: FAIL")
        print("No generated team plan exists. Send a real Comp Maker team to Roster first.")
        return 1

    team_name = requested or plan.name
    prescriptions = recruit_prescriptions_from_rows(_prescription_rows(db, plan.plan_id))
    result = Phase125TeamWorkflowAuditService.audit(
        team_name=team_name,
        registered_team_names=tuple(roster.list_team_names()),
        plan=plan,
        builds=builds.load(),
        roster_members=tuple(roster.list_members()),
        recruit_prescriptions=prescriptions,
    )

    print("========================================")
    print(" PHASE 12.5 TEAM WORKFLOW AUDIT")
    print("========================================")
    print(f"Team:                    {result.team_name}")
    print(f"Roster identity:         {'yes' if result.team_registered else 'NO'}")
    print(f"Generated plan:          {'yes' if result.generated_plan_found else 'NO'}")
    print(f"Plan slots:              {result.slot_count}")
    print(f"Saved assignments:       {result.saved_slot_count}")
    print(f"Exact saved resolutions: {result.exact_saved_assignment_count}")
    print(f"Recruit/open chairs:     {result.recruit_slot_count}")
    print(f"Adopted prescriptions:   {result.adopted_prescription_count}")
    print(f"Explicit unresolved:     {result.unresolved_count}")

    print("\nPROBLEMS")
    if result.problems:
        for problem in result.problems:
            print(f"- {problem}")
    else:
        print("- none")

    print("\nBOUNDARIES")
    for boundary in result.boundaries:
        print(f"- {boundary}")

    print(f"\nRESULT: {'PASS' if result.passed else 'FAIL'}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
