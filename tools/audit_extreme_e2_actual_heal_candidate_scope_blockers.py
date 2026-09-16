from __future__ import annotations

from engine.config import DEFAULT_DATABASE
from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


SETS = ("Light Speaker", "Innate Axiom")
OBJECTIVES = ("spell_damage", "weapon_damage")


def main() -> int:
    repository = GearSetRepository(DEFAULT_DATABASE)
    print("EXTREME E2 H1 CANDIDATE-SCOPE BLOCKER DRILLDOWN")
    print(f"database={DEFAULT_DATABASE}")

    found = 0
    for objective in OBJECTIVES:
        rows = ExtremeGearSetObjectiveService.candidates_for_objective(repository, objective)
        for row in rows:
            if str(row.set_name or "") not in SETS:
                continue
            found += 1
            print(f"SET={row.set_name!r} objective={row.objective_key!r} reviewed_delta={row.reviewed_delta!r}")
            if row.unresolved:
                for index, blocker in enumerate(row.unresolved, start=1):
                    print(f"  blocker[{index}]={blocker!r}")
            else:
                print("  blockers=NONE")

    print(f"rows_found={found}")
    if found == 0:
        print("RESULT=FAIL: expected Light Speaker / Innate Axiom objective rows were not found")
        return 1
    print("NEXT_STEP=align exact reviewed admission patterns to these live blocker strings; do not broaden candidate-scope semantics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
