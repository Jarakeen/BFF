from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


SET_NAME = "Netch Oil"
OBJECTIVES = ("healing_done", "critical_healing")


def main() -> int:
    database = get_data_dir() / "eso.db"
    repository = GearSetRepository(database)
    repository.preload_all_static()

    gear_set = repository.get_set(SET_NAME)
    if gear_set is None:
        print(f"NETCH OIL H1 EVIDENCE AUDIT\ndatabase={database}\nset_found=False")
        return 1

    print("NETCH OIL H1 EVIDENCE AUDIT")
    print(f"database={database}")
    print(f"set_id={gear_set.id}")
    print(f"category={gear_set.category!r}")
    print(f"max_equip_count={gear_set.max_equip_count!r}")
    print("BONUSES")
    for bonus in repository.get_bonuses(gear_set.id):
        print(f"  {bonus.piece_count}pc: {bonus.description}")

    print("H1 OBJECTIVE ROWS")
    for objective in OBJECTIVES:
        row = ExtremeGearSetObjectiveService.candidate_for_set(
            repository,
            SET_NAME,
            objective,
        )
        print(
            f"  objective={objective} reviewed_delta={row.reviewed_delta:.6f} "
            f"mechanic_complete={row.mechanic_complete} unresolved={len(row.unresolved)}"
        )
        for message in row.unresolved:
            print(f"    unresolved: {message}")
        for effect in row.source_effects:
            print(
                "    effect: "
                f"stat={getattr(effect.stat, 'value', effect.stat)} "
                f"operation={effect.operation.value} value={effect.value} "
                f"condition={effect.condition!r} source={effect.source!r}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
