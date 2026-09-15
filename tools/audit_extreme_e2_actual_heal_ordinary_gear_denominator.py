from __future__ import annotations

"""Audit the ordinary five-piece gear-set denominator for Extreme H1 Actual Heal.

Read-only. The production H1 ordinary-set candidate service intentionally uses a
bounded per-objective pool. That is a useful search heuristic, but it is not a
proof that every canonically relevant ordinary five-piece set was considered.

This audit enumerates the complete canonical GearSetRepository universe against
the exact H1 objective families used by the candidate service. It distinguishes:

* sets incapable of reaching a useful five-piece threshold;
* sets with at least one reviewed positive H1 contribution;
* sets whose potentially relevant mechanics remain unresolved;
* sets selected by the current bounded production discovery policy; and
* reviewed-positive sets omitted only because of that production bound.

It does not score whole builds and does not claim that the gear-family denominator
is globally complete across monster sets, mythics, arena weapons, or runtime procs.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from minmax.gear_set_repository import GearSetRepository
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


@dataclass(frozen=True)
class OrdinaryGearDenominatorRow:
    set_id: int
    set_name: str
    category: str
    useful_piece_count: int
    reviewed_positive_objectives: tuple[str, ...]
    unresolved_objectives: tuple[str, ...]
    selected_by_bounded_search: bool

    @property
    def reviewed_positive(self) -> bool:
        return bool(self.reviewed_positive_objectives)

    @property
    def mechanic_complete_for_h1_screen(self) -> bool:
        return not self.unresolved_objectives


def build_ordinary_gear_denominator(
    repository: GearSetRepository,
    *,
    per_objective: int = 12,
) -> tuple[OrdinaryGearDenominatorRow, ...]:
    selected = {
        name.casefold()
        for name in ExtremeActualHealGearSetCandidateService(
            repository.database_path
        ).candidate_set_names(per_objective=per_objective)
    }

    rows: list[OrdinaryGearDenominatorRow] = []
    for gear_set in repository.list_sets():
        useful = ExtremeGearSetObjectiveService._maximum_useful_piece_count(
            repository,
            gear_set,
        )
        positive: list[str] = []
        unresolved: list[str] = []
        if useful >= 5:
            for objective in ExtremeActualHealGearSetCandidateService.OBJECTIVES:
                candidate = ExtremeGearSetObjectiveService.candidate_for_set(
                    repository,
                    gear_set.name,
                    objective,
                    equipped_piece_count=useful,
                )
                if candidate.reviewed_delta > 0:
                    positive.append(objective)
                if candidate.unresolved:
                    unresolved.append(objective)

        rows.append(
            OrdinaryGearDenominatorRow(
                set_id=int(gear_set.id),
                set_name=str(gear_set.name),
                category=str(gear_set.category or ""),
                useful_piece_count=int(useful),
                reviewed_positive_objectives=tuple(positive),
                unresolved_objectives=tuple(unresolved),
                selected_by_bounded_search=gear_set.name.casefold() in selected,
            )
        )

    return tuple(sorted(rows, key=lambda row: (row.set_name.casefold(), row.set_id)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--per-objective", type=int, default=12)
    args = parser.parse_args()

    repository = GearSetRepository(Path(args.database))
    rows = build_ordinary_gear_denominator(
        repository,
        per_objective=max(1, int(args.per_objective)),
    )

    five_piece = tuple(row for row in rows if row.useful_piece_count >= 5)
    reviewed_positive = tuple(row for row in five_piece if row.reviewed_positive)
    unresolved = tuple(row for row in five_piece if row.unresolved_objectives)
    selected = tuple(row for row in five_piece if row.selected_by_bounded_search)
    omitted_positive = tuple(
        row
        for row in reviewed_positive
        if not row.selected_by_bounded_search
    )
    complete_positive = tuple(
        row
        for row in reviewed_positive
        if row.mechanic_complete_for_h1_screen
    )
    omitted_complete_positive = tuple(
        row
        for row in complete_positive
        if not row.selected_by_bounded_search
    )

    print("EXTREME E2 ACTUAL HEAL ORDINARY GEAR DENOMINATOR")
    print(f"database={Path(args.database)}")
    print(f"per_objective_candidate_cap={max(1, int(args.per_objective))}")
    print(f"canonical_set_count={len(rows)}")
    print(f"five_piece_capable_set_count={len(five_piece)}")
    print(f"reviewed_positive_h1_set_count={len(reviewed_positive)}")
    print(f"mechanic_complete_reviewed_positive_set_count={len(complete_positive)}")
    print(f"h1_screen_unresolved_set_count={len(unresolved)}")
    print(f"bounded_search_selected_set_count={len(selected)}")
    print(f"bounded_search_omitted_reviewed_positive_count={len(omitted_positive)}")
    print(
        "bounded_search_omitted_mechanic_complete_reviewed_positive_count="
        f"{len(omitted_complete_positive)}"
    )

    if omitted_complete_positive:
        print("OMITTED MECHANIC-COMPLETE REVIEWED-POSITIVE SETS")
        for row in omitted_complete_positive:
            objectives = ",".join(row.reviewed_positive_objectives)
            print(f"  {row.set_name}: objectives={objectives}")

    if unresolved:
        print("UNRESOLVED H1 SCREEN SETS")
        for row in unresolved[:50]:
            print(
                f"  {row.set_name}: objectives={','.join(row.unresolved_objectives)}"
            )
        if len(unresolved) > 50:
            print(f"  ... {len(unresolved) - 50} additional unresolved sets")

    bounded_search_is_denominator = not omitted_complete_positive and not unresolved
    print(f"ordinary_gear_bounded_search_is_complete_denominator={bounded_search_is_denominator}")
    print("global_gear_family_denominator_complete=False")
    print(
        "GLOBAL_GEAR_FAMILY_REASON=ordinary five-piece proof is only one family; "
        "monster sets, mythics, arena weapons, and runtime proc families require their own denominators"
    )
    print(
        "NEXT_STEP="
        + (
            "prove unresolved ordinary-set mechanics, then replace or justify the bounded per-objective candidate cap"
            if unresolved
            else (
                "remove or prove-safe-prune the bounded per-objective cap before closing the ordinary five-piece denominator"
                if omitted_complete_positive
                else "ordinary five-piece denominator is ready for family-level closure; continue with monster/mythic/arena/proc denominators"
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
