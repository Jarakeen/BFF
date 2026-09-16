from __future__ import annotations

"""Audit the ordinary five-piece gear-set denominator for Extreme H1 Actual Heal.

Read-only. Authoritative H1 ordinary-set discovery is exhaustive across the
mechanic-complete reviewed five-piece universe. H1 positivity may be supplied by
either the shared numeric objective parser or an H1 specialist rule whose value is
owned by conditioned/runtime scoring (for example a witnessed named Courage buff).

An optional bounded comparison is retained only to measure what the retired
shortlist policy would have omitted. This audit does not claim global completeness
across monster sets, mythics, arena weapons, or runtime proc families.
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
    selected_by_authoritative_search: bool
    selected_by_bounded_comparison: bool
    shared_numeric_positive_objectives: tuple[str, ...] = ()

    @property
    def reviewed_positive(self) -> bool:
        return bool(self.reviewed_positive_objectives)

    @property
    def mechanic_complete_for_h1_screen(self) -> bool:
        return not self.unresolved_objectives

    @property
    def specialist_only_positive(self) -> bool:
        return self.reviewed_positive and not self.shared_numeric_positive_objectives


def build_ordinary_gear_denominator(
    repository: GearSetRepository,
    *,
    comparison_per_objective: int = 12,
) -> tuple[OrdinaryGearDenominatorRow, ...]:
    repository.preload_all_static()

    service = ExtremeActualHealGearSetCandidateService.__new__(
        ExtremeActualHealGearSetCandidateService
    )
    service.repository = repository
    authoritative = {
        name.casefold()
        for name in service.candidate_set_names(per_objective=None)
    }
    bounded = {
        name.casefold()
        for name in service.candidate_set_names(
            per_objective=max(1, int(comparison_per_objective))
        )
    }

    rows: list[OrdinaryGearDenominatorRow] = []
    for gear_set in repository.list_sets():
        useful = ExtremeGearSetObjectiveService._maximum_useful_piece_count(
            repository,
            gear_set,
        )
        positive: list[str] = []
        shared_numeric_positive: list[str] = []
        unresolved: list[str] = []
        if useful >= 5:
            for objective in ExtremeActualHealGearSetCandidateService.OBJECTIVES:
                candidate = ExtremeGearSetObjectiveService.candidate_for_set(
                    repository,
                    gear_set.name,
                    objective,
                    equipped_piece_count=useful,
                )
                review = service._h1_review(candidate)
                if candidate.reviewed_delta > 0:
                    shared_numeric_positive.append(objective)
                if candidate.reviewed_delta > 0 or review.h1_positive_modifier_proven:
                    positive.append(objective)
                if not review.h1_mechanic_complete:
                    unresolved.append(objective)

        key = gear_set.name.casefold()
        rows.append(
            OrdinaryGearDenominatorRow(
                set_id=int(gear_set.id),
                set_name=str(gear_set.name),
                category=str(gear_set.category or ""),
                useful_piece_count=int(useful),
                reviewed_positive_objectives=tuple(positive),
                unresolved_objectives=tuple(unresolved),
                selected_by_authoritative_search=key in authoritative,
                selected_by_bounded_comparison=key in bounded,
                shared_numeric_positive_objectives=tuple(shared_numeric_positive),
            )
        )

    return tuple(sorted(rows, key=lambda row: (row.set_name.casefold(), row.set_id)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--comparison-per-objective", type=int, default=12)
    args = parser.parse_args()

    comparison_cap = max(1, int(args.comparison_per_objective))
    repository = GearSetRepository(Path(args.database))
    rows = build_ordinary_gear_denominator(
        repository,
        comparison_per_objective=comparison_cap,
    )

    five_piece = tuple(row for row in rows if row.useful_piece_count >= 5)
    reviewed_positive = tuple(row for row in five_piece if row.reviewed_positive)
    shared_numeric_positive = tuple(
        row for row in five_piece if row.shared_numeric_positive_objectives
    )
    specialist_only_positive = tuple(
        row for row in five_piece if row.specialist_only_positive
    )
    unresolved = tuple(row for row in five_piece if row.unresolved_objectives)
    complete_positive = tuple(
        row for row in reviewed_positive if row.mechanic_complete_for_h1_screen
    )
    authoritative_selected = tuple(
        row for row in five_piece if row.selected_by_authoritative_search
    )
    authoritative_omitted_complete_positive = tuple(
        row
        for row in complete_positive
        if not row.selected_by_authoritative_search
    )
    bounded_selected = tuple(
        row for row in five_piece if row.selected_by_bounded_comparison
    )
    bounded_omitted_complete_positive = tuple(
        row
        for row in complete_positive
        if not row.selected_by_bounded_comparison
    )

    print("EXTREME E2 ACTUAL HEAL ORDINARY GEAR DENOMINATOR")
    print(f"database={Path(args.database)}")
    print("authoritative_per_objective_candidate_cap=None")
    print(f"comparison_per_objective_candidate_cap={comparison_cap}")
    print(f"canonical_set_count={len(rows)}")
    print(f"five_piece_capable_set_count={len(five_piece)}")
    print(f"shared_numeric_reviewed_positive_set_count={len(shared_numeric_positive)}")
    print(f"specialist_only_reviewed_positive_set_count={len(specialist_only_positive)}")
    print(f"reviewed_positive_h1_set_count={len(reviewed_positive)}")
    print(f"mechanic_complete_reviewed_positive_set_count={len(complete_positive)}")
    print(f"h1_screen_unresolved_set_count={len(unresolved)}")
    print(f"authoritative_search_selected_set_count={len(authoritative_selected)}")
    print(
        "authoritative_search_omitted_mechanic_complete_reviewed_positive_count="
        f"{len(authoritative_omitted_complete_positive)}"
    )
    print(f"bounded_comparison_selected_set_count={len(bounded_selected)}")
    print(
        "bounded_comparison_omitted_mechanic_complete_reviewed_positive_count="
        f"{len(bounded_omitted_complete_positive)}"
    )

    if specialist_only_positive:
        print("H1 SPECIALIST-ONLY POSITIVE SETS")
        for row in specialist_only_positive:
            print(
                f"  {row.set_name}: objectives={','.join(row.reviewed_positive_objectives)}"
            )

    if authoritative_omitted_complete_positive:
        print("AUTHORITATIVE OMISSIONS — PROOF FAILURE")
        for row in authoritative_omitted_complete_positive:
            print(
                f"  {row.set_name}: objectives={','.join(row.reviewed_positive_objectives)}"
            )

    if unresolved:
        print("UNRESOLVED H1 SCREEN SETS")
        for row in unresolved[:50]:
            print(f"  {row.set_name}: objectives={','.join(row.unresolved_objectives)}")
        if len(unresolved) > 50:
            print(f"  ... {len(unresolved) - 50} additional unresolved sets")

    authoritative_reviewed_denominator_complete = not authoritative_omitted_complete_positive
    print(
        "ordinary_gear_authoritative_reviewed_denominator_complete="
        f"{authoritative_reviewed_denominator_complete}"
    )
    print(
        "ordinary_gear_full_mechanic_denominator_complete="
        f"{authoritative_reviewed_denominator_complete and not unresolved}"
    )
    print("global_gear_family_denominator_complete=False")
    print(
        "GLOBAL_GEAR_FAMILY_REASON=ordinary five-piece proof is only one family; "
        "monster sets, mythics, arena weapons, and runtime proc families require their own denominators"
    )
    print(
        "NEXT_STEP="
        + (
            "close unresolved ordinary-set mechanics while preserving exhaustive authoritative admission"
            if unresolved
            else "ordinary five-piece family is closed; continue with monster/mythic/arena/proc denominators"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
